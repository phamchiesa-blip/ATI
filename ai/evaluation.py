"""
ai/evaluation.py
-----------------
Evaluation module: measures Precision@K, Recall@K, F1@K for the recommender.

Workflow:
1. Create simulated users with clear tastes (likes genre X, dislikes genre Y)
2. Generate fake interaction history (like/dislike some movies)
3. Run both proposed system and baseline, get Top-K
4. Measure Precision@K, Recall@K, F1@K — compare 2 approaches
5. Test failure case: new user with onboarding only, no like/dislike yet
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def precision_at_k(recommended: list, relevant: set, k: int) -> float:
    """Fraction of Top-K movies the user would actually like."""
    topk = [r["movie_id"] for r in recommended[:k]]
    hits = sum(1 for mid in topk if mid in relevant)
    return hits / k if k > 0 else 0.0


def recall_at_k(recommended: list, relevant: set, k: int) -> float:
    """Fraction of liked movies that appear in Top-K."""
    topk = [r["movie_id"] for r in recommended[:k]]
    hits = sum(1 for mid in topk if mid in relevant)
    return hits / len(relevant) if relevant else 0.0


def f1_at_k(recommended: list, relevant: set, k: int) -> float:
    p = precision_at_k(recommended, relevant, k)
    r = recall_at_k(recommended, relevant, k)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# ---------------------------------------------------------------------------
# Simulated User
# ---------------------------------------------------------------------------

@dataclass
class SimulatedUser:
    user_id: str
    preferred_genres: list      # ['Action', 'Sci-Fi']
    disliked_genres: list       # ['Horror', 'Romance']
    n_likes: int = 10           # liked movies in training set
    n_dislikes: int = 5


def create_simulated_users() -> list:
    """Create a diverse set of fake users for evaluation.
    Each user has clear tastes so accuracy is easy to measure.
    """
    return [
        SimulatedUser("eval_action_fan",
                      preferred_genres=["Action", "Adventure"],
                      disliked_genres=["Romance", "Musical"]),
        SimulatedUser("eval_drama_fan",
                      preferred_genres=["Drama", "Biography"],
                      disliked_genres=["Horror", "Thriller"]),
        SimulatedUser("eval_scifi_fan",
                      preferred_genres=["Science Fiction", "Fantasy"],
                      disliked_genres=["Comedy", "Family"]),
        SimulatedUser("eval_comedy_fan",
                      preferred_genres=["Comedy", "Animation"],
                      disliked_genres=["War", "Crime"]),
    ]


def _movies_by_genre(metadata_map: dict, genres: list, n: int, exclude: set = None) -> list:
    """Get n movies whose genre overlaps the given list (for training set)."""
    genre_set = set(genres)
    result = []
    for mid, meta in metadata_map.items():
        if exclude and mid in exclude:
            continue
        if genre_set & set(meta.get("genres", [])):
            result.append(mid)
        if len(result) >= n * 5:   # collect extra for shuffling
            break
    np.random.shuffle(result)
    return result[:n]


# ---------------------------------------------------------------------------
# Main Evaluation Runner
# ---------------------------------------------------------------------------

def run_evaluation(
    all_movie_ids: np.ndarray,
    all_vectors: np.ndarray,
    metadata_map: dict,
    proposed_system: Callable,    # fn(liked_vecs, disliked_vecs, exclude) -> list of dict
    baseline_system: Callable,    # fn(liked_vecs, exclude) -> list of dict
    k: int = 10,
    seed: int = 42,
) -> dict:
    """Run full evaluation.

    Parameters
    ----------
    proposed_system : callable
        Signature: (liked_vectors, disliked_vectors, exclude_ids) -> list[dict]
    baseline_system : callable
        Signature: (liked_vectors, exclude_ids) -> list[dict]
    k : int
        K in Precision@K, Recall@K, F1@K

    Returns
    -------
    dict with keys: 'proposed', 'baseline', 'per_user'
    """
    np.random.seed(seed)
    simulated_users = create_simulated_users()

    results = {
        "proposed": {"precision": [], "recall": [], "f1": []},
        "baseline": {"precision": [], "recall": [], "f1": []},
        "per_user": {},
    }

    id_to_idx = {int(mid): i for i, mid in enumerate(all_movie_ids)}

    for user in simulated_users:
        # --- Build training set (liked/disliked movies) ---
        liked_ids = _movies_by_genre(metadata_map, user.preferred_genres, user.n_likes)
        disliked_ids = _movies_by_genre(
            metadata_map, user.disliked_genres, user.n_dislikes,
            exclude=set(liked_ids),
        )

        liked_vecs = [all_vectors[id_to_idx[mid]]
                      for mid in liked_ids if mid in id_to_idx]
        disliked_vecs = [all_vectors[id_to_idx[mid]]
                         for mid in disliked_ids if mid in id_to_idx]

        # --- Ground truth: unused movies of the same preferred genre ---
        trained_set = set(liked_ids + disliked_ids)
        ground_truth_ids = _movies_by_genre(
            metadata_map, user.preferred_genres, n=50, exclude=trained_set
        )
        relevant = set(ground_truth_ids)

        exclude_ids = list(trained_set)

        # --- Run proposed system ---
        proposed_recs = proposed_system(liked_vecs, disliked_vecs, exclude_ids)
        p_p = precision_at_k(proposed_recs, relevant, k)
        r_p = recall_at_k(proposed_recs, relevant, k)
        f_p = f1_at_k(proposed_recs, relevant, k)

        # --- Run baseline system ---
        baseline_recs = baseline_system(liked_vecs, exclude_ids)
        p_b = precision_at_k(baseline_recs, relevant, k)
        r_b = recall_at_k(baseline_recs, relevant, k)
        f_b = f1_at_k(baseline_recs, relevant, k)

        results["proposed"]["precision"].append(p_p)
        results["proposed"]["recall"].append(r_p)
        results["proposed"]["f1"].append(f_p)
        results["baseline"]["precision"].append(p_b)
        results["baseline"]["recall"].append(r_b)
        results["baseline"]["f1"].append(f_b)

        results["per_user"][user.user_id] = {
            "proposed": {"precision@k": p_p, "recall@k": r_p, "f1@k": f_p},
            "baseline": {"precision@k": p_b, "recall@k": r_b, "f1@k": f_b},
        }

    # Average across users
    for sys in ("proposed", "baseline"):
        for metric in ("precision", "recall", "f1"):
            vals = results[sys][metric]
            results[sys][f"avg_{metric}"] = float(np.mean(vals)) if vals else 0.0

    return results


def run_cold_start_test(
    all_movie_ids: np.ndarray,
    all_vectors: np.ndarray,
    metadata_map: dict,
    proposed_system: Callable,
    selected_genres: list,        # genres user picked at onboarding
    genre_labels: list,
    total_dims: int,
    k: int = 10,
) -> dict:
    """Failure case: new user with onboarding only, no like/dislike yet.
    Checks whether Ranking returns sensible results.

    Sensible = at least X% of Top-K movies belong to the chosen genres.
    """
    from ai.user_profile import make_genre_profile_vector, build_initial_profile_from_genres
    from ai.similarity import top_k_similar
    from ai.ranking import rank_candidates

    genre_vec = make_genre_profile_vector(selected_genres, genre_labels, total_dims)
    profile = build_initial_profile_from_genres(genre_vec)

    candidates = top_k_similar(profile, all_movie_ids, all_vectors, k=k * 3)
    recs = rank_candidates(candidates, metadata_map, top_n=k)

    # Measure: how many Top-K movies belong to chosen genres
    genre_set = set(selected_genres)
    hits = 0
    for rec in recs[:k]:
        meta = metadata_map.get(rec["movie_id"], {})
        if genre_set & set(meta.get("genres", [])):
            hits += 1

    genre_match_rate = hits / k if k > 0 else 0.0

    print(f"\n[Cold-Start Test] Genres: {selected_genres}")
    print(f"  Top-{k} recommendations genre match rate: {genre_match_rate:.0%}")
    for rec in recs[:k]:
        meta = metadata_map.get(rec["movie_id"], {})
        print(f"  - {meta.get('title', '?')} | genres: {meta.get('genres', [])} | score: {rec['score']:.3f}")

    return {"genre_match_rate": genre_match_rate, "recommendations": recs}


def print_evaluation_report(results: dict, k: int):
    """Print results table to console."""
    print(f"\n{'='*60}")
    print(f"  EVALUATION REPORT — Precision/Recall/F1 @{k}")
    print(f"{'='*60}")
    print(f"{'Metric':<20} {'Proposed':>12} {'Baseline':>12} {'Delta':>10}")
    print(f"{'-'*60}")
    for metric in ("precision", "recall", "f1"):
        p = results["proposed"][f"avg_{metric}"]
        b = results["baseline"][f"avg_{metric}"]
        delta = p - b
        sign = "+" if delta >= 0 else ""
        print(f"  {metric.capitalize()+'@K':<18} {p:>12.4f} {b:>12.4f} {sign+f'{delta:.4f}':>10}")
    print(f"{'='*60}\n")
