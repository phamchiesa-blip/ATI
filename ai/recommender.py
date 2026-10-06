"""
recommender.py
---------------
High-level entry point for the AI recommendation pipeline.
Orchestrates: user profile -> similarity search -> ranking -> result.

Other modules (services/recommendation_service.py) call this instead of
calling similarity.py / ranking.py directly.
"""

import numpy as np

from ai.user_profile import build_user_profile
from ai.similarity import top_k_similar
from ai.ranking import rank_candidates


def get_recommendations(
    user_id: str,
    all_movie_ids: np.ndarray,
    all_vectors: np.ndarray,
    liked_vectors: list,
    disliked_vectors: list,
    metadata_map: dict,
    exclude_ids: list = None,
    candidate_pool: int = 50,
    top_n: int = 10,
    user_profile: np.ndarray = None,
) -> list:
    """Generate movie recommendations for a user.

    Parameters
    ----------
    user_id : str
        The user's ID (used for logging/debugging only here).
    all_movie_ids : np.ndarray
        Ordered array of all movie IDs in the feature store.
    all_vectors : np.ndarray
        Feature matrix (n_movies, n_features) from the feature store.
    liked_vectors : list of np.ndarray
        Feature vectors of movies the user has liked.
    disliked_vectors : list of np.ndarray
        Feature vectors of movies the user has disliked.
    metadata_map : dict
        {movie_id: metadata_dict} for all candidates.
    exclude_ids : list, optional
        Movie IDs already shown or watched — excluded from results.
    candidate_pool : int
        How many candidates to retrieve from cosine similarity before re-ranking.
    top_n : int
        Final number of recommendations to return.

    Returns
    -------
    recommendations : list of dict
        Each dict contains movie_id, title, genres, score, etc.
        Empty list if the user has no interaction history yet.
    """
    profile = user_profile if user_profile is not None else build_user_profile(liked_vectors, disliked_vectors)
    if profile is None:
        # Cold-start: no interactions yet — return empty (caller should fall back
        # to popular movies or genre-based defaults)
        return []

    candidates = top_k_similar(
        query_vector=profile,
        movie_ids=all_movie_ids,
        matrix=all_vectors,
        k=candidate_pool,
        exclude_ids=exclude_ids,
    )

    ranked = rank_candidates(
        candidates=candidates,
        metadata_map=metadata_map,
        top_n=top_n,
    )

    return ranked
