"""
recommender.py
--------------
Dieu phoi toan bo luong Recommendation Core:

    User
     |
     v
    Like / Dislike
     |
     v
    User Profile (vector)
     |
     v
    Cosine Similarity (vs toan bo phim)
     |
     v
    Top-K Movies
     |
     v
    Don -> Ranking

Public API:
    like(user_id, movie_id, db_path, ...)
    dislike(user_id, movie_id, db_path, ...)
    recommend(user_id, k, db_path, ...)  -> [(movie_id, score), ...]
"""

from __future__ import annotations

import os
import sys
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_MODULE_SRC = os.path.join(_ROOT, "data_module", "src")
for _p in (_ROOT, _DATA_MODULE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
from feature_store import DEFAULT_DB_PATH
from repositories.protocols import InteractionRepositoryProtocol, MovieRepositoryProtocol
from repositories.sqlite_interaction_repo import SqliteInteractionRepository
from repositories.sqlite_movie_repo import SqliteMovieRepository
from similarity import get_top_k_movies
from user_profile import ALPHA, BETA, UserProfile, UserProfileRegistry

# ─── Singleton registry (in-memory) ─────────────────────────────────────────
_registry = UserProfileRegistry()


def _get_profile(
    user_id: str,
    db_path: str = DEFAULT_DB_PATH,
    movie_repo: Optional[MovieRepositoryProtocol] = None,
    interaction_repo: Optional[InteractionRepositoryProtocol] = None,
) -> UserProfile:
    """Lay hoac phuc dung profile cua user.

    Neu profile chua trong memory, thu build lai tu interaction history.
    """
    profile = _registry.get(user_id)
    if profile is not None:
        return profile

    profile = _registry.get_or_create(user_id)
    i_repo = interaction_repo or SqliteInteractionRepository(db_path=db_path)
    m_repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    history = i_repo.get_interactions(user_id)
    for record in history:
        vec = m_repo.get_vector(record["movie_id"])
        if vec is None:
            continue
        if record["action"] == "like":
            profile.apply_like(vec)
        else:
            profile.apply_dislike(vec)
    return profile


# ─── Public API ──────────────────────────────────────────────────────────────

def like(
    user_id: str,
    movie_id: int,
    db_path: str = DEFAULT_DB_PATH,
    *,
    movie_repo: Optional[MovieRepositoryProtocol] = None,
    interaction_repo: Optional[InteractionRepositoryProtocol] = None,
) -> None:
    """Xu ly su kien user bam Like tren mot phim."""
    m_repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    i_repo = interaction_repo or SqliteInteractionRepository(db_path=db_path)

    vec = m_repo.get_vector(movie_id)
    if vec is None:
        raise ValueError(f"movie_id={movie_id} khong ton tai trong DB.")

    profile = _get_profile(user_id, db_path=db_path, movie_repo=m_repo, interaction_repo=i_repo)
    profile.apply_like(vec)
    i_repo.log_interaction(user_id, movie_id, "like")


def dislike(
    user_id: str,
    movie_id: int,
    db_path: str = DEFAULT_DB_PATH,
    *,
    preserve_numeric: bool = False,
    movie_repo: Optional[MovieRepositoryProtocol] = None,
    interaction_repo: Optional[InteractionRepositoryProtocol] = None,
) -> None:
    """Xu ly su kien user bam Dislike tren mot phim."""
    m_repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    i_repo = interaction_repo or SqliteInteractionRepository(db_path=db_path)

    vec = m_repo.get_vector(movie_id)
    if vec is None:
        raise ValueError(f"movie_id={movie_id} khong ton tai trong DB.")

    profile = _get_profile(user_id, db_path=db_path, movie_repo=m_repo, interaction_repo=i_repo)
    profile.apply_dislike(vec, preserve_numeric=preserve_numeric)
    i_repo.log_interaction(user_id, movie_id, "dislike")


def seed_profile_from_onboarding(
    user_id: str,
    seed_movie_ids: "list[int]",
    db_path: str = DEFAULT_DB_PATH,
    *,
    movie_repo: Optional[MovieRepositoryProtocol] = None,
) -> None:
    """Khoi tao User Profile tu danh sach phim yeu thich trong onboarding."""
    m_repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    vectors = []
    for mid in seed_movie_ids:
        vec = m_repo.get_vector(mid)
        if vec is not None:
            vectors.append(vec)
    if not vectors:
        return
    profile = _registry.get_or_create(user_id)
    profile.seed_from_movies(vectors)


def recommend(
    user_id: str,
    k: int = 20,
    db_path: str = DEFAULT_DB_PATH,
    *,
    movie_repo: Optional[MovieRepositoryProtocol] = None,
    interaction_repo: Optional[InteractionRepositoryProtocol] = None,
) -> "list[tuple[int, float]]":
    """Tra ve Top-K phim phu hop nhat cho user."""
    m_repo = movie_repo or SqliteMovieRepository(db_path=db_path)
    i_repo = interaction_repo or SqliteInteractionRepository(db_path=db_path)

    profile = _get_profile(user_id, db_path=db_path, movie_repo=m_repo, interaction_repo=i_repo)
    if not profile.is_initialized():
        raise RuntimeError(
            f"User '{user_id}' chua co profile. "
            "Hay goi seed_profile_from_onboarding() hoac like()/dislike() truoc."
        )

    # Lay toan bo phim tu Repository
    movie_ids, movie_matrix = m_repo.get_all_vectors()

    # Tap phim can loai (da tuong tac)
    history = i_repo.get_interactions(user_id)
    interacted_ids = {record["movie_id"] for record in history}

    # Tinh Top-K
    top_k = get_top_k_movies(
        user_vector=profile.vector,
        movie_ids=movie_ids,
        movie_matrix=movie_matrix,
        k=k,
        exclude_ids=interacted_ids,
    )
    return top_k
