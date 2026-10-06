"""
recommendation_service.py
--------------------------
Business logic layer for generating recommendations.
Loads the feature matrix once at startup (or lazily), then calls
similarity + ranking. User profile is loaded via profile_service
(persisted in DB) instead of rebuilt from history on every request.
"""

import numpy as np

from backend.database.database import (
    get_all_vectors,
    get_all_metadata,
    get_user_interactions,
    DEFAULT_DB_PATH,
)
from backend.services.profile_service import get_or_rebuild_profile


# ---------------------------------------------------------------------------
# Module-level cache: load the full feature matrix once per process so we
# don't hit SQLite on every recommendation request.
# ---------------------------------------------------------------------------
_cached_ids: np.ndarray = None
_cached_matrix: np.ndarray = None
_cached_metadata: dict = None


def _ensure_cache(db_path=DEFAULT_DB_PATH):
    global _cached_ids, _cached_matrix, _cached_metadata
    if _cached_ids is None:
        _cached_ids, _cached_matrix = get_all_vectors(db_path=db_path)
        _cached_metadata = get_all_metadata(db_path=db_path)


def recommend_for_user(
    user_id: str,
    top_n: int = 10,
    db_path=DEFAULT_DB_PATH,
) -> list:
    """Generate recommendations for a user from their persisted profile.

    Parameters
    ----------
    user_id : str
    top_n : int
        Number of recommendations to return.
    db_path : str
        Path to the SQLite database.

    Returns
    -------
    list of dict — each with movie_id, title, genres, score, etc.
    Falls back to popular movies on full cold-start (no onboarding, no likes).
    """
    _ensure_cache(db_path)

    profile = get_or_rebuild_profile(user_id, db_path=db_path)

    interactions = get_user_interactions(user_id, db_path=db_path)
    all_interacted = [i["movie_id"] for i in interactions]

    if profile is None:
        # Full cold-start (no onboarding and no like/dislike yet)
        from backend.services.movie_service import get_popular_movies
        return get_popular_movies(db_path=db_path, limit=top_n)

    from ai.similarity import top_k_similar
    from ai.ranking import rank_candidates

    candidates = top_k_similar(
        query_vector=profile,
        movie_ids=_cached_ids,
        matrix=_cached_matrix,
        k=50,
        exclude_ids=all_interacted,
    )

    return rank_candidates(candidates, _cached_metadata, top_n=top_n)


def invalidate_cache():
    """Call after rebuilding the database to force a fresh load."""
    global _cached_ids, _cached_matrix, _cached_metadata
    _cached_ids = _cached_matrix = _cached_metadata = None
