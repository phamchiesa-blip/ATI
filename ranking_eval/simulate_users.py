"""ranking_eval/simulate_users.py
---------------------------------
Simulated user personas and interaction generation for ranking evaluation.

Safety guarantee:
    All user interactions and profile updates MUST run against a temporary copy
    of movies.db. This module does not write to the production database.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set, Tuple

# Ensure paths to data_module/src and recommendation are available
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
_RECOMMENDATION = os.path.join(_ROOT, "recommendation")
for _p in (_ROOT, _DATA_SRC, _RECOMMENDATION):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd
import recommender as _rec
from feature_store import DEFAULT_DB_PATH, check_db_exists, get_movie_metadata
from ranking_eval.evaluation import precision_recall_f1_at_k
from ranking_eval.frontend_service import (
    DEFAULT_ONBOARDING_TOP_N,
    get_popular_movies,
    onboard_user,
    record_interaction,
)
from ranking_eval.integration import (
    _apply_neural_reranking,
    baseline_rank,
    get_cosine_recommendations,
    rank_candidates,
)


@dataclass
class Persona:
    id: str
    name: str
    genres: list[str]
    is_external: bool
    external_desc: str
    description: str
    condition: Callable[[dict, dict], bool]
    relevant_pool: list[int] = field(default_factory=list)


def _load_raw_csv_metadata(csv_path: str) -> dict[int, dict]:
    """Load raw CSV to retrieve external features not present in movies.db/feature vectors."""
    if not os.path.exists(csv_path):
        return {}
    df = pd.read_csv(csv_path)
    csv_map = {}
    for _, row in df.iterrows():
        try:
            mid = int(row["id"])
            csv_map[mid] = {
                "original_language": str(row.get("original_language", "") or "").strip(),
                "keywords": str(row.get("keywords", "") or "").strip(),
            }
        except (ValueError, TypeError):
            continue
    return csv_map


def _has_keyword(raw_keywords: str, target: str) -> bool:
    """Check if target keyword is inside the JSON string of TMDB keywords."""
    if not raw_keywords:
        return False
    try:
        kw_list = json.loads(raw_keywords)
        target_lower = target.casefold()
        return any(k.get("name", "").casefold() == target_lower for k in kw_list if isinstance(k, dict))
    except Exception:
        return False


def create_personas_definitions() -> list[Persona]:
    """Define the 8 realistic personas.
    
    Personas P1 - P6 are defined on standard metadata (genres, dates, votes).
    Personas P7 - P8 are defined on external attributes NOT present in the
    movie feature vectors (original_language and raw keywords).
    """
    return [
        Persona(
            id="P1",
            name="Modern Sci-Fi Explorer",
            genres=["Science Fiction"],
            is_external=False,
            external_desc="Standard feature vector genres & release date",
            description="Fans of 21st century science fiction blockbusters with strong viewership",
            condition=lambda m, ex: (
                "Science Fiction" in m["genres"]
                and m["release_year"] >= 2000
                and m["vote_count"] >= 800
            ),
        ),
        Persona(
            id="P2",
            name="Modern Horror Fan",
            genres=["Horror"],
            is_external=False,
            external_desc="Standard feature vector genres & release date",
            description="Fans of contemporary horror cinema released since 2006",
            condition=lambda m, ex: (
                "Horror" in m["genres"]
                and m["release_year"] >= 2006
            ),
        ),
        Persona(
            id="P3",
            name="Classic Crime & Noir",
            genres=["Crime"],
            is_external=False,
            external_desc="Standard feature vector genres, rating, and 20th century release",
            description="Fans of classic, well-reviewed 20th century crime and noir films",
            condition=lambda m, ex: (
                "Crime" in m["genres"]
                and 1900 <= m["release_year"] < 2000
                and m["vote_average"] >= 6.5
            ),
        ),
        Persona(
            id="P4",
            name="Family Animation Lover",
            genres=["Animation", "Family"],
            is_external=False,
            external_desc="Standard multi-genre combination and popularity",
            description="Fans of animated family films with active viewer engagement",
            condition=lambda m, ex: (
                "Animation" in m["genres"]
                and "Family" in m["genres"]
                and m["vote_count"] >= 300
            ),
        ),
        Persona(
            id="P5",
            name="Millennial Rom-Com",
            genres=["Romance", "Comedy"],
            is_external=False,
            external_desc="Standard multi-genre combination and era",
            description="Fans of romantic comedies released between 2000 and 2012",
            condition=lambda m, ex: (
                "Romance" in m["genres"]
                and "Comedy" in m["genres"]
                and 2000 <= m["release_year"] <= 2012
                and m["vote_count"] >= 150
            ),
        ),
        Persona(
            id="P6",
            name="Action Thriller Buff",
            genres=["Action", "Thriller"],
            is_external=False,
            external_desc="Standard multi-genre combination and high rating",
            description="Fans of fast-paced, critically acclaimed action-thriller films",
            condition=lambda m, ex: (
                "Action" in m["genres"]
                and "Thriller" in m["genres"]
                and m["vote_average"] >= 6.6
                and m["vote_count"] >= 400
            ),
        ),
        Persona(
            id="P7",
            name="World / Non-English Cinema",
            genres=["Drama"],
            is_external=True,
            external_desc="original_language != 'en' in raw CSV (NOT in movie feature vector)",
            description="Fans of foreign/international non-English cinema across global cultures",
            condition=lambda m, ex: (
                ex.get("original_language", "en") != "en"
            ),
        ),
        Persona(
            id="P8",
            name="Literary Adaptation Buff",
            genres=["Drama", "Thriller"],
            is_external=True,
            external_desc="Keyword 'based on novel' in raw CSV (NOT in movie feature vector)",
            description="Fans of movies adapted from novels and literary works with solid audience",
            condition=lambda m, ex: (
                _has_keyword(ex.get("keywords", ""), "based on novel")
                and m["vote_count"] >= 250
            ),
        ),
    ]


def load_personas(db_path: str, csv_path: str) -> list[Persona]:
    """Load the catalog and compute relevant movie pools for all 8 personas."""
    check_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM movies").fetchall()
    conn.close()

    csv_meta = _load_raw_csv_metadata(csv_path)
    personas = create_personas_definitions()

    parsed_movies = []
    for r in rows:
        mid = int(r["movie_id"])
        date_str = r["release_date"] or ""
        yr = int(date_str[:4]) if date_str[:4].isdigit() else 0
        parsed_movies.append({
            "movie_id": mid,
            "title": r["title"] or "",
            "genres": json.loads(r["genres"] or "[]"),
            "director": r["director"] or "",
            "vote_average": float(r["vote_average"] or 0.0),
            "vote_count": int(r["vote_count"] or 0),
            "popularity": float(r["popularity"] or 0.0),
            "release_year": yr,
        })

    for p in personas:
        pool = []
        for m in parsed_movies:
            mid = m["movie_id"]
            ex = csv_meta.get(mid, {})
            if p.condition(m, ex):
                pool.append(mid)
        p.relevant_pool = pool

    return personas


_SEED_CACHE: dict[tuple, list[int]] = {}
_METADATA_CACHE: dict[int, dict | None] = {}


def _get_cached_metadata(mid: int, db_path: str) -> dict | None:
    if mid not in _METADATA_CACHE:
        _METADATA_CACHE[mid] = get_movie_metadata(mid, db_path=db_path)
    return _METADATA_CACHE[mid]


def get_onboarding_seed_movies(
    genres: list[str],
    db_path: str,
    top_n_per_genre: int = DEFAULT_ONBOARDING_TOP_N,
) -> list[int]:
    """Compute the exact seed movie IDs chosen by onboard_user."""
    cache_key = (tuple(sorted(genres)), top_n_per_genre)
    if cache_key in _SEED_CACHE:
        return list(_SEED_CACHE[cache_key])

    check_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT movie_id, genres FROM movies
           WHERE genres IS NOT NULL AND genres != '[]'
           ORDER BY popularity DESC, vote_count DESC, movie_id ASC"""
    ).fetchall()
    conn.close()

    merged_ids = []
    for genre in genres:
        wanted = genre.casefold()
        genre_found = 0
        for row in rows:
            stored_genres = [g.casefold() for g in json.loads(row["genres"] or "[]")]
            if wanted in stored_genres:
                merged_ids.append(int(row["movie_id"]))
                genre_found += 1
                if genre_found >= top_n_per_genre:
                    break

    res = list(dict.fromkeys(merged_ids))
    _SEED_CACHE[cache_key] = res
    return list(res)


def evaluate_top_k_for_ranker(
    ranked_ids: list[int],
    test_relevant_ids: set[int],
    k: int = 10,
    k_deep: int = 50,
) -> dict[str, float]:
    """Calculate Precision@K, Recall@K, F1@K, Recall@k_deep (Recall@50), and Hit Rate@K."""
    top_k = ranked_ids[:k]
    base_metrics = precision_recall_f1_at_k(top_k, test_relevant_ids, k=k)

    top_deep = ranked_ids[:k_deep]
    rel_count = len(test_relevant_ids)
    hits_deep = sum(1 for mid in top_deep if mid in test_relevant_ids)
    recall_at_50 = hits_deep / rel_count if rel_count > 0 else 0.0
    hit_rate = 1.0 if base_metrics["precision"] > 0.0 else 0.0

    return {
        "precision": round(base_metrics["precision"], 4),
        "recall": round(base_metrics["recall"], 4),
        "f1": round(base_metrics["f1"], 4),
        "recall_at_50": round(recall_at_50, 4),
        "hit_rate": round(hit_rate, 4),
    }


def prepare_simulated_user(
    *,
    persona: Persona,
    scenario: str,
    m_likes: int,
    noise_ratio: float,
    dislike_count: int,
    seed: int,
    user_id: str,
    db_path: str,
    all_catalog_ids: list[int],
    onboarding_scale: float = 1.0,
    k_deep: int = 50,
    preserve_numeric_dislikes: bool = False,
) -> dict[str, Any]:
    """Setup user, onboard, record interactions, and retrieve candidate pool.

    Interaction generation rules:
    - If m_likes == 0: no likes are recorded; dislike_count still controls
      how many dislikes are sampled after onboarding.
    - If m_likes > 0: generates m_likes (with noise_ratio from outside the persona pool)
      and dislike_count dislikes sampled from eligible non-pool movies.
      (In run_benchmark: dislike_count is 2 for m in {1, 3}, and 3 for m in {5, 10}).
    """
    rng = random.Random(seed)

    onboard_user(user_id, db_path=db_path, selected_genres=persona.genres)
    seed_movie_ids = get_onboarding_seed_movies(persona.genres, db_path=db_path)

    if onboarding_scale != 1.0:
        prof = _rec._registry.get(user_id)
        if prof is not None and prof._vector is not None:
            prof._vector = prof._vector * float(onboarding_scale)

    liked_ids: list[int] = []
    disliked_ids: list[int] = []

    pool_set = set(persona.relevant_pool)
    seed_set = set(seed_movie_ids)
    catalog_set = set(all_catalog_ids)

    if m_likes > 0:
        noise_count = int(round(m_likes * noise_ratio))
        clean_count = max(1, m_likes - noise_count)

        eligible_clean = sorted(list(pool_set - seed_set))
        eligible_non_pool = sorted(list(catalog_set - pool_set - seed_set))

        clean_likes = rng.sample(eligible_clean, clean_count) if len(eligible_clean) >= clean_count else eligible_clean
        noise_likes = rng.sample(eligible_non_pool, noise_count) if len(eligible_non_pool) >= noise_count else eligible_non_pool[:noise_count]

        for mid in clean_likes + noise_likes:
            record_interaction(user_id, mid, "like", db_path=db_path)
            liked_ids.append(mid)

        dislike_pool = sorted(list(set(eligible_non_pool) - set(noise_likes)))
        actual_dislike_count = min(dislike_count, len(dislike_pool))
        dislikes = rng.sample(dislike_pool, actual_dislike_count)

    else:
        eligible_non_pool = sorted(list(catalog_set - pool_set - seed_set))
        actual_dislike_count = min(dislike_count, len(eligible_non_pool))
        dislikes = rng.sample(eligible_non_pool, actual_dislike_count)

    for mid in dislikes:
        record_interaction(
            user_id,
            mid,
            "dislike",
            db_path=db_path,
            preserve_numeric_dislikes=preserve_numeric_dislikes,
        )
        disliked_ids.append(mid)

    interacted_ids = seed_set | set(liked_ids) | set(disliked_ids)
    test_relevant_ids = pool_set - seed_set - set(liked_ids)

    avail_random = sorted(list(catalog_set - interacted_ids))
    sample_size = min(k_deep, len(avail_random))
    random_recs = rng.sample(avail_random, sample_size) if sample_size > 0 else []

    popular_cards = get_popular_movies(db_path=db_path, limit=k_deep, exclude_ids=interacted_ids)
    popular_recs = [int(row["movie_id"]) for row in popular_cards]

    want_k = max(100, k_deep + len(interacted_ids) + 20)
    try:
        cosine_raw = get_cosine_recommendations(user_id, k=want_k, db_path=db_path)
    except RuntimeError:
        cosine_raw = [(int(c["movie_id"]), 0.0) for c in popular_cards]

    candidates = []
    for mid, score in cosine_raw:
        mid_int = int(mid)
        if mid_int in interacted_ids:
            continue
        meta = _get_cached_metadata(mid_int, db_path=db_path)
        if meta is None:
            continue
        candidates.append({
            "movie_id": mid_int,
            "cosine": float(score),
            "vote_average": meta["vote_average"],
            "popularity": meta["popularity"],
            "release_date": meta["release_date"],
        })
        if len(candidates) >= 100:
            break

    baseline_rows = baseline_rank(candidates)[:k_deep]
    baseline_recs = [row["movie_id"] for row in baseline_rows]

    return {
        "user_id": user_id,
        "persona": persona,
        "scenario": scenario,
        "m_likes": m_likes,
        "seed": seed,
        "interacted_ids": interacted_ids,
        "test_relevant_ids": test_relevant_ids,
        "random_recs": random_recs,
        "popular_recs": popular_recs,
        "candidates": candidates,
        "baseline_recs": baseline_recs,
    }


def simulate_single_user(
    *,
    persona: Persona,
    scenario: str,
    m_likes: int,
    noise_ratio: float,
    dislike_count: int,
    seed: int,
    user_id: str,
    db_path: str,
    all_catalog_ids: list[int],
    k: int = 10,
    k_deep: int = 50,
    onboarding_scale: float = 1.0,
    ranking_weights: Any = None,
    neural_weight: float = 0.20,
    preserve_numeric_dislikes: bool = False,
) -> dict[str, Any]:
    """Run one complete user simulation across all 6 rankers:
    (0a) Random, (0b) Popular, (1) Baseline Cosine, (2) Tier 1 Ranking,
    (3a) Tier 2 Old (Prob mode), (3b) Tier 2 New (Logit MinMax mode).

    Dislike count convention:
    - m = 0: 0 dislikes (onboarding only)
    - m in {1, 3}: 2 dislikes
    - m in {5, 10}: 3 dislikes
    """
    prep = prepare_simulated_user(
        persona=persona,
        scenario=scenario,
        m_likes=m_likes,
        noise_ratio=noise_ratio,
        dislike_count=dislike_count,
        seed=seed,
        user_id=user_id,
        db_path=db_path,
        all_catalog_ids=all_catalog_ids,
        onboarding_scale=onboarding_scale,
        k_deep=k_deep,
        preserve_numeric_dislikes=preserve_numeric_dislikes,
    )

    candidates = prep["candidates"]
    test_relevant_ids = prep["test_relevant_ids"]

    # Tier 1
    if ranking_weights is not None:
        tier1_rows = rank_candidates(candidates, weights=ranking_weights)[:k_deep]
    else:
        tier1_rows = rank_candidates(candidates)[:k_deep]
    tier1_recs = [row["movie_id"] for row in tier1_rows]

    # Tier 2 Old (mode='prob', legacy unscaled)
    tier2_old_rows = _apply_neural_reranking(
        user_id, tier1_rows, db_path=db_path, neural_weight=neural_weight, score_mode="prob"
    )[:k_deep]
    tier2_old_recs = [row["movie_id"] for row in tier2_old_rows]
    neural_used = bool(tier2_old_rows[0].get("neural_used", False)) if tier2_old_rows else False

    # Tier 2 New (mode='logit_minmax', standardized features)
    tier2_new_rows = _apply_neural_reranking(
        user_id, tier1_rows, db_path=db_path, neural_weight=neural_weight, score_mode="logit_minmax"
    )[:k_deep]
    tier2_new_recs = [row["movie_id"] for row in tier2_new_rows]

    metrics = {
        "0a_Random": evaluate_top_k_for_ranker(prep["random_recs"], test_relevant_ids, k=k, k_deep=k_deep),
        "0b_Popular": evaluate_top_k_for_ranker(prep["popular_recs"], test_relevant_ids, k=k, k_deep=k_deep),
        "1_Baseline": evaluate_top_k_for_ranker(prep["baseline_recs"], test_relevant_ids, k=k, k_deep=k_deep),
        "2_Tier1": evaluate_top_k_for_ranker(tier1_recs, test_relevant_ids, k=k, k_deep=k_deep),
        "3_Tier2_Old": evaluate_top_k_for_ranker(tier2_old_recs, test_relevant_ids, k=k, k_deep=k_deep),
        "3_Tier2_New": evaluate_top_k_for_ranker(tier2_new_recs, test_relevant_ids, k=k, k_deep=k_deep),
    }

    _rec._registry._profiles.pop(user_id, None)

    return {
        "user_id": user_id,
        "persona_id": persona.id,
        "persona_name": persona.name,
        "is_external": persona.is_external,
        "pool_size": len(persona.relevant_pool),
        "test_relevant_size": len(test_relevant_ids),
        "scenario": scenario,
        "m_likes": m_likes,
        "seed": seed,
        "neural_used": neural_used,
        "metrics": metrics,
        "tier1_top10": tier1_rows[:k],
    }
