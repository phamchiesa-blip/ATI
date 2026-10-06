"""
profile_service.py
-------------------
Manages User Profile vectors: init (onboarding), update (like/dislike),
persist to DB and reload when needed.

DB schema (in database.py):
    user_profiles (user_id TEXT PK, profile BLOB, dims INTEGER, updated_at TEXT)
"""

import numpy as np

from backend.database.database import (
    get_movie_vector,
    get_user_interactions,
    save_user_profile,
    load_user_profile,
    DEFAULT_DB_PATH,
)
from ai.user_profile import (
    build_user_profile,
    update_user_profile,
    build_initial_profile_from_genres,
    make_genre_profile_vector,
)


def initialize_profile_from_onboarding(
    user_id: str,
    selected_genres: list,       # from Vo's Onboarding screen
    genre_labels: list,          # from feature_info, saved at DB build time
    total_dims: int,
    db_path=DEFAULT_DB_PATH,
) -> np.ndarray:
    """Called when a new user completes onboarding.
    Creates initial profile from selected genres and saves to DB.
    """
    genre_vec = make_genre_profile_vector(selected_genres, genre_labels, total_dims)
    profile = build_initial_profile_from_genres(genre_vec)
    save_user_profile(user_id, profile, db_path=db_path)
    return profile


def process_feedback_and_update(
    user_id: str,
    movie_id: int,
    action: str,    # 'like' or 'dislike'
    db_path=DEFAULT_DB_PATH,
) -> np.ndarray:
    """Called when user presses Like/Dislike.
    Loads current profile -> updates -> saves back.
    """
    current_profile = load_user_profile(user_id, db_path=db_path)
    movie_vec = get_movie_vector(movie_id, db_path=db_path)
    if movie_vec is None:
        return current_profile

    updated = update_user_profile(current_profile, movie_vec, action)
    if updated is not None:
        save_user_profile(user_id, updated, db_path=db_path)
    return updated


def get_or_rebuild_profile(user_id: str, db_path=DEFAULT_DB_PATH) -> np.ndarray:
    """Load profile from DB. If missing -> rebuild from interaction history.
    Safe fallback when DB was reset.
    """
    profile = load_user_profile(user_id, db_path=db_path)
    if profile is not None:
        return profile

    # Rebuild from history
    interactions = get_user_interactions(user_id, db_path=db_path)
    liked_vecs = [get_movie_vector(i["movie_id"], db_path) for i in interactions if i["action"] == "like"]
    disliked_vecs = [get_movie_vector(i["movie_id"], db_path) for i in interactions if i["action"] == "dislike"]
    liked_vecs = [v for v in liked_vecs if v is not None]
    disliked_vecs = [v for v in disliked_vecs if v is not None]

    return build_user_profile(liked_vecs, disliked_vecs)
