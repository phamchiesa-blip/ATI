"""Connect Part III ranking to the actual Part I store and Part II output.

This file does not build profiles, generate cosine scores, or make fake users.
It asks Part II for Top-K, gets metadata from Part I, and reranks that list.
"""

from __future__ import annotations
from pathlib import Path

import argparse
import os
import sys
from typing import Any

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
_RECOMMENDATION = os.path.join(_ROOT, "recommendation")
for _path in (_DATA_SRC, _RECOMMENDATION):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from feature_store import DEFAULT_DB_PATH, check_db_exists, get_movie_metadata
from recommender import recommend as get_cosine_recommendations

from .evaluation import precision_recall_f1_at_k
from .online_model import (
    ONLINE_SCORE_MODE,
    OnlineLikeModel,
    get_global_movie_feature_scaler,
)
from .ranking import _minmax, baseline_rank, rank_candidates

CLEARLY_HATED_GENRE_THRESHOLD: float = 0.5


def get_ranked_recommendations(
    user_id: str,
    *,
    candidate_k: int = 100,
    top_n: int = 10,
    db_path: str = DEFAULT_DB_PATH,
    neural_weight: float = 0.20,
    score_mode: str | None = None,
) -> list[dict]:
    """Get Part II's Top-K, enrich from Part I, then return Part III Top-N.

    ``candidate_k`` is how many cosine recommendations Part II supplies.
    ``top_n`` is how many reranked recommendations to return.
    """
    from collections import Counter
    import recommender as _rec
    from feature_store import get_user_interactions
    from .frontend_service import get_popular_movies

    history = get_user_interactions(user_id, db_path=db_path)
    likes = [h for h in history if h["action"] == "like"]
    dislikes = [h for h in history if h["action"] == "dislike"]

    prof = _rec._registry.get(user_id)
    is_onboarded = getattr(prof, "is_onboarded", False) if prof else False
    if not is_onboarded:
        accounts_db = os.environ.get("ACCOUNTS_DB", str(Path(__file__).resolve().parent.parent / "accounts.db"))
        if os.path.exists(accounts_db):
            try:
                import sqlite3
                with sqlite3.connect(accounts_db) as conn:
                    row = conn.execute(
                        "SELECT 1 FROM onboarding WHERE user_id = ? AND (genres != '[]' OR favorites != '[]')",
                        (user_id,),
                    ).fetchone()
                    if row:
                        is_onboarded = True
            except Exception:
                pass

    has_positive_signal = (len(likes) > 0) or is_onboarded

    if has_positive_signal:
        try:
            cosine_results = get_cosine_recommendations(
                user_id, k=candidate_k, db_path=db_path
            )
            candidates = []
            for movie_id, cosine_score in cosine_results:
                metadata = get_movie_metadata(movie_id, db_path=db_path)
                if metadata is None:
                    continue
                candidates.append({
                    "movie_id": int(movie_id),
                    "cosine": float(cosine_score),
                    "title": metadata["title"],
                    "genres": metadata["genres"],
                    "director": metadata["director"],
                    "vote_average": metadata["vote_average"],
                    "popularity": metadata["popularity"],
                    "release_date": metadata["release_date"],
                })
            ranked = rank_candidates(candidates)
            return _apply_neural_reranking(
                user_id,
                ranked,
                db_path=db_path,
                neural_weight=neural_weight,
                score_mode=score_mode,
            )[:top_n]
        except RuntimeError:
            pass  # Fall through to popular fallback

    # Fallback for cold start (no interactions) or dislike-only users (no positive signal)
    rated_ids = {h["movie_id"] for h in history}
    hated_genres = set()
    if dislikes:
        genre_counts = Counter()
        for d in dislikes:
            meta = get_movie_metadata(d["movie_id"], db_path=db_path)
            if meta and meta.get("genres"):
                for g in meta["genres"]:
                    genre_counts[g.strip()] += 1

        total_dislikes = len(dislikes)
        hated_genres = {
            g for g, count in genre_counts.items()
            if (count / total_dislikes) >= CLEARLY_HATED_GENRE_THRESHOLD
        }

    popular = get_popular_movies(
        db_path=db_path,
        limit=top_n,
        exclude_ids=rated_ids,
        exclude_genres=hated_genres if hated_genres else None,
    )
    candidates = []
    for metadata in popular:
        candidates.append({
            "movie_id": int(metadata["movie_id"]),
            "cosine": 0.0,
            "title": metadata["title"],
            "genres": metadata["genres"],
            "director": metadata["director"],
            "vote_average": metadata["vote_average"],
            "popularity": metadata["popularity"],
            "release_date": metadata["release_date"],
        })
    ranked = rank_candidates(candidates)
    for row in ranked:
        row["final_score"] = row["ranking_score"]
        row["neural_used"] = False
    return ranked[:top_n]


def _apply_neural_reranking(
    user_id: str,
    ranked_candidates: list[dict],
    *,
    db_path: str,
    neural_weight: float,
    score_mode: str | None = None,
    scaler: Any = None,
) -> list[dict]:
    """Blend first-layer ranking with the Like model when training is viable."""
    mode = score_mode or ONLINE_SCORE_MODE
    if not 0.0 <= neural_weight <= 1.0:
        raise ValueError("neural_weight must be between 0 and 1")
    if not ranked_candidates:
        return ranked_candidates
    if neural_weight == 0:
        for row in ranked_candidates:
            row["final_score"] = row["ranking_score"]
            row["neural_used"] = False
        return ranked_candidates

    if scaler is None and mode == "logit_minmax":
        scaler = get_global_movie_feature_scaler(db_path)

    model = train_online_model_from_history(user_id, db_path, scaler=scaler, score_mode=mode)
    if model is None:
        # No examples or only one feedback class: keep Tầng 1 as the result.
        for row in ranked_candidates:
            row["final_score"] = row["ranking_score"]
            row["neural_used"] = False
        return ranked_candidates

    from feature_store import get_movie_vector

    scored = []
    if mode == "logit_minmax":
        raw_logits = []
        for candidate in ranked_candidates:
            vector = get_movie_vector(candidate["movie_id"], db_path=db_path)
            raw_logits.append(None if vector is None else float(model.decision_function(vector)))

        normalized_scores = _minmax(raw_logits, missing=0.5)

        for candidate, norm_s, raw_z in zip(ranked_candidates, normalized_scores, raw_logits):
            row = dict(candidate)
            row["nn_raw_logit"] = raw_z
            row["nn_like_score"] = norm_s
            row["nn_like_probability"] = norm_s  # for backward compatibility
            row["final_score"] = (
                (1.0 - neural_weight) * row["ranking_score"]
                + neural_weight * norm_s
            )
            row["neural_used"] = True
            scored.append(row)
    else:  # mode == "prob" (legacy)
        for candidate in ranked_candidates:
            vector = get_movie_vector(candidate["movie_id"], db_path=db_path)
            row = dict(candidate)
            if vector is None:
                row["nn_like_probability"] = 0.5
            else:
                row["nn_like_probability"] = float(model.like_probability(vector))
            row["nn_like_score"] = row["nn_like_probability"]
            row["final_score"] = (
                (1.0 - neural_weight) * row["ranking_score"]
                + neural_weight * row["nn_like_probability"]
            )
            row["neural_used"] = True
            scored.append(row)

    return sorted(scored, key=lambda row: row["final_score"], reverse=True)


def evaluate_recommendations(
    user_id: str,
    relevant_movie_ids,
    *,
    candidate_k: int = 100,
    k: int = 10,
    db_path: str = DEFAULT_DB_PATH,
    score_mode: str | None = None,
) -> dict[str, dict[str, float]]:
    """Compare cosine-only with reranking, given known relevant movie IDs.

    The relevant IDs must come from held-out user feedback or an explicitly
    defined evaluation dataset. This function does not invent ground truth.
    """
    cosine_results = get_cosine_recommendations(
        user_id, k=candidate_k, db_path=db_path
    )
    candidates = []
    for movie_id, cosine_score in cosine_results:
        metadata = get_movie_metadata(movie_id, db_path=db_path)
        if metadata is None:
            continue
        candidates.append({
            "movie_id": int(movie_id),
            "cosine": float(cosine_score),
            "vote_average": metadata["vote_average"],
            "popularity": metadata["popularity"],
            "release_date": metadata["release_date"],
        })

    relevant = set(int(movie_id) for movie_id in relevant_movie_ids)
    result = {}
    weighted = rank_candidates(candidates)
    neural = _apply_neural_reranking(
        user_id,
        weighted,
        db_path=db_path,
        neural_weight=0.20,
        score_mode=score_mode,
    )
    for name, ordered in (
        ("cosine_baseline", baseline_rank(candidates)),
        ("weighted_ranking", weighted),
        ("weighted_plus_neural", neural),
    ):
        result[name] = precision_recall_f1_at_k(
            [row["movie_id"] for row in ordered], relevant, k
        )
    return result


def train_online_model_from_history(
    user_id: str,
    db_path: str = DEFAULT_DB_PATH,
    *,
    scaler: Any = None,
    score_mode: str | None = None,
):
    """Train the optional model from real history, if both labels are present.

    Returns None until there is at least one Like and one Dislike; a classifier
    trained on only one kind of feedback would rank nearly everything alike.
    """
    from feature_store import get_movie_vector, get_user_interactions

    mode = score_mode or ONLINE_SCORE_MODE
    if scaler is None and mode == "logit_minmax":
        scaler = get_global_movie_feature_scaler(db_path)

    examples, labels = [], []
    for event in get_user_interactions(user_id, db_path=db_path):
        vector = get_movie_vector(event["movie_id"], db_path=db_path)
        if vector is not None:
            examples.append(vector)
            labels.append(1 if event["action"] == "like" else 0)
    if not examples or set(labels) != {0, 1}:
        return None
    return OnlineLikeModel(scaler=scaler).partial_fit(examples, labels)


def main():
    # Windows PowerShell may use a legacy code page that cannot print some
    # movie-title characters. Replace unsupported characters instead of
    # crashing halfway through the recommendation list.
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        description="Use Part II recommendations and rerank them with Part III."
    )
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--candidate-k", type=int, default=100)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument(
        "--neural-weight", type=float, default=0.20,
        help="How much the NN probability affects the final score (0 to 1).",
    )
    parser.add_argument(
        "--relevant-ids",
        help="Optional comma-separated held-out relevant movie IDs for evaluation.",
    )
    parser.add_argument(
        "--score-mode",
        choices=["prob", "logit_minmax"],
        default=ONLINE_SCORE_MODE,
        help="Online model scoring mode: 'prob' (legacy) or 'logit_minmax' (scaled margin).",
    )
    args = parser.parse_args()
    if not os.path.exists(args.db):
        raise SystemExit(
            f"Database not found: {args.db}\n"
            "Build it with data_module/src/build_dataset.py first."
        )

    results = get_ranked_recommendations(
        args.user_id,
        candidate_k=args.candidate_k,
        top_n=args.top_n,
        db_path=args.db,
        neural_weight=args.neural_weight,
        score_mode=args.score_mode,
    )
    print(f"Top {len(results)} phim sau reranking cho user {args.user_id}:")
    neural_active = bool(results and results[0].get("neural_used"))
    if neural_active:
        print("Tầng Neural Network: đang dùng")
    else:
        print("Tầng Neural Network: chưa dùng; cần ít nhất một Like và một Dislike trong lịch sử")
    for rank, item in enumerate(results, start=1):
        print(
            f"{rank}. {item['title']} (id={item['movie_id']}) | "
            f"cosine={item['cosine']:.3f} | ranking={item['ranking_score']:.3f} | "
            f"final={item['final_score']:.3f}"
        )

    if args.relevant_ids:
        relevant_ids = [value for value in args.relevant_ids.split(",") if value.strip()]
        print("Evaluation:", evaluate_recommendations(
            args.user_id,
            relevant_ids,
            candidate_k=args.candidate_k,
            k=args.top_n,
            db_path=args.db,
            score_mode=args.score_mode,
        ))


if __name__ == "__main__":
    main()
