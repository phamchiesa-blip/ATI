"""
ranking.py
-----------
Re-ranks a candidate list of movies by blending cosine-similarity scores
with rating (vote_average), popularity and recency signals, then applies
diversity filtering to avoid recommending 10 movies from the same genre.

Formula (report section 3.7):
    score = w_sim * sim_n + w_rating * rating_n + w_pop * pop_n + w_rec * year_n
"""

import numpy as np


def _normalize(arr: np.ndarray) -> np.ndarray:
    """Min-max normalize an array to [0, 1]. Returns zeros if all values equal."""
    lo, hi = arr.min(), arr.max()
    if hi == lo:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def rank_candidates(
    candidates: list,
    metadata_map: dict,
    similarity_weight: float = 0.50,
    rating_weight: float = 0.20,
    popularity_weight: float = 0.20,
    recency_weight: float = 0.10,
    diversity_max_per_genre: int = 3,
    top_n: int = 10,
) -> list:
    """Re-rank a list of candidate movies using a weighted scoring formula.

    Parameters
    ----------
    candidates : list of dict
        Output of similarity.top_k_similar():  [{'movie_id': int, 'score': float}, ...]
    metadata_map : dict
        {movie_id: metadata_dict} — from backend.database.get_movie_metadata().
        Each metadata_dict must contain 'vote_average', 'popularity',
        'release_date' (YYYY-MM-DD string or None), and 'genres' (list[str]).
    similarity_weight : float
        Weight for cosine-similarity score.
    rating_weight : float
        Weight for normalized vote_average signal.
    popularity_weight : float
        Weight for normalized popularity signal.
    recency_weight : float
        Weight for normalized release-year signal.
    diversity_max_per_genre : int
        Maximum movies from the same primary genre in the final list.
    top_n : int
        Number of movies to return after re-ranking and diversity filtering.

    Returns
    -------
    ranked : list of dict
        Each dict: {'movie_id', 'score', 'sim_score', 'title', 'genres', ...}
        Sorted descending by final blended score.
    """
    if not candidates:
        return []

    ids = np.array([c["movie_id"] for c in candidates])
    sim_scores = np.array([c["score"] for c in candidates], dtype=np.float32)

    pop_scores = np.array(
        [metadata_map.get(mid, {}).get("popularity", 0.0) or 0.0 for mid in ids],
        dtype=np.float32,
    )

    rating_scores = np.array(
        [metadata_map.get(mid, {}).get("vote_average", 0.0) or 0.0 for mid in ids],
        dtype=np.float32,
    )

    def _year(mid):
        rd = metadata_map.get(mid, {}).get("release_date") or ""
        try:
            return int(rd[:4])
        except (ValueError, TypeError):
            return 0

    year_scores = np.array([_year(mid) for mid in ids], dtype=np.float32)

    sim_n = _normalize(sim_scores)
    pop_n = _normalize(pop_scores)
    rating_n = _normalize(rating_scores)
    year_n = _normalize(year_scores)

    blended = (
        similarity_weight * sim_n
        + rating_weight * rating_n
        + popularity_weight * pop_n
        + recency_weight * year_n
    )

    order = np.argsort(-blended)

    # Diversity filter: limit how many movies per primary genre
    genre_counts: dict = {}
    ranked = []
    for idx in order:
        mid = int(ids[idx])
        meta = metadata_map.get(mid, {})
        genres = meta.get("genres") or []
        primary_genre = genres[0] if genres else "Unknown"

        if genre_counts.get(primary_genre, 0) >= diversity_max_per_genre:
            continue

        genre_counts[primary_genre] = genre_counts.get(primary_genre, 0) + 1
        ranked.append({
            "movie_id": mid,
            "score": float(blended[idx]),
            "sim_score": float(sim_scores[idx]),
            "title": meta.get("title", ""),
            "genres": genres,
            "vote_average": meta.get("vote_average"),
            "popularity": meta.get("popularity"),
            "release_date": meta.get("release_date"),
        })

        if len(ranked) >= top_n:
            break

    return ranked
