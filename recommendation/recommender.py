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
    like(user_id, movie_id, db_path)
    dislike(user_id, movie_id, db_path)
    recommend(user_id, k, db_path)  -> [(movie_id, score), ...]
"""

from __future__ import annotations

import sys
import os

# Cho phep import feature_store tu thu muc data_module/src
_DATA_MODULE_SRC = os.path.join(
    os.path.dirname(__file__), "..", "data_module", "src"
)
sys.path.insert(0, os.path.abspath(_DATA_MODULE_SRC))

import numpy as np
from feature_store import get_movie_vector, get_all_vectors

from user_profile import UserProfile, UserProfileRegistry, ALPHA, BETA
from interaction import save_interaction, get_interactions
from similarity import get_top_k_movies

# ─── Singleton registry (in-memory) ─────────────────────────────────────────
_registry = UserProfileRegistry()


def _get_profile(user_id: str, db_path: str) -> UserProfile:
    """Lay hoac phuc dung profile cua user.

    Neu profile chua trong memory, thu build lai tu interaction history.
    """
    profile = _registry.get(user_id)
    if profile is not None:
        return profile

    # Tao moi va replay lich su (cold start sau khi restart)
    profile = _registry.get_or_create(user_id)
    history = get_interactions(user_id, db_path=db_path)
    for record in history:
        vec = get_movie_vector(record["movie_id"], db_path=db_path)
        if vec is None:
            continue
        if record["action"] == "like":
            profile.apply_like(vec)
        else:
            profile.apply_dislike(vec)
    return profile


# ─── Public API ──────────────────────────────────────────────────────────────

def like(user_id: str, movie_id: int, db_path: str = "movies.db") -> None:
    """Xu ly su kien user bam Like tren mot phim.

    Luong:
        movie_id
           |
           v
        get_movie_vector(movie_id)
           |
           v
        Update User Profile  (Profile += alpha * MovieVector)
           |
           v
        Luu Interaction History

    Parameters
    ----------
    user_id : str
    movie_id : int
    db_path : str
        Duong dan den movies.db (mac dinh 'movies.db').

    Raises
    ------
    ValueError
        Neu movie_id khong ton tai trong DB.
    """
    vec = get_movie_vector(movie_id, db_path=db_path)
    if vec is None:
        raise ValueError(f"movie_id={movie_id} khong ton tai trong DB.")

    profile = _get_profile(user_id, db_path)
    profile.apply_like(vec)
    save_interaction(user_id, movie_id, "like", db_path=db_path)


def dislike(user_id: str, movie_id: int, db_path: str = "movies.db") -> None:
    """Xu ly su kien user bam Dislike tren mot phim.

    Luong:
        movie_id
           |
           v
        get_movie_vector(movie_id)
           |
           v
        Update User Profile  (Profile -= beta * MovieVector)
           |
           v
        Luu Interaction History

    Parameters
    ----------
    user_id : str
    movie_id : int
    db_path : str

    Raises
    ------
    ValueError
        Neu movie_id khong ton tai trong DB.
    """
    vec = get_movie_vector(movie_id, db_path=db_path)
    if vec is None:
        raise ValueError(f"movie_id={movie_id} khong ton tai trong DB.")

    profile = _get_profile(user_id, db_path)
    profile.apply_dislike(vec)
    save_interaction(user_id, movie_id, "dislike", db_path=db_path)


def seed_profile_from_onboarding(
    user_id: str,
    seed_movie_ids: "list[int]",
    db_path: str = "movies.db",
) -> None:
    """Khoi tao User Profile tu danh sach phim yeu thich trong onboarding.

    Goi ham nay khi user moi dang ky va chon genre / phim yeu thich.
    Profile = trung binh cac vector phim duoc chon.

    Parameters
    ----------
    user_id : str
    seed_movie_ids : list[int]
        Danh sach movie_id user chon trong buoc onboarding.
    db_path : str
    """
    vectors = []
    for mid in seed_movie_ids:
        vec = get_movie_vector(mid, db_path=db_path)
        if vec is not None:
            vectors.append(vec)
    if not vectors:
        return
    profile = _registry.get_or_create(user_id)
    profile.seed_from_movies(vectors)


def recommend(
    user_id: str,
    k: int = 20,
    db_path: str = "movies.db",
) -> "list[tuple[int, float]]":
    """Tra ve Top-K phim phu hop nhat cho user.

    Luong:
        User Profile
             |
             v
        So sanh voi toan bo Movie Feature Vectors (Cosine Similarity)
             |
             v
        Sort giam dan
             |
             v
        Loai phim da Like / Dislike
             |
             v
        Lay Top-K

    Parameters
    ----------
    user_id : str
    k : int
        So phim muon lay (mac dinh 20).
    db_path : str

    Returns
    -------
    list[tuple[int, float]]
        [(movie_id, cosine_score), ...] sap xep giam dan.
        Day la dau vao cho module Ranking cua Don.

    Raises
    ------
    RuntimeError
        Neu user chua co profile (chua onboarding va chua co bat ky
        Like/Dislike nao).
    """
    profile = _get_profile(user_id, db_path)
    if not profile.is_initialized():
        raise RuntimeError(
            f"User '{user_id}' chua co profile. "
            "Hay goi seed_profile_from_onboarding() hoac like()/dislike() truoc."
        )

    # Lay toan bo phim
    movie_ids, movie_matrix = get_all_vectors(db_path=db_path)

    # Tap phim can loai (da tuong tac)
    history = get_interactions(user_id, db_path=db_path)
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
