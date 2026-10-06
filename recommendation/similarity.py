"""
similarity.py
-------------
Tinh Cosine Similarity giua User Profile va Movie Feature Vectors,
tra ve Top-K phim phu hop nhat.

Luong:
    User Profile vector
         |
         v
    cosine_similarity(user_vector, movie_matrix)  -- vectorized
         |
         v
    Score moi phim (0.0 -> 1.0, cao = phu hop hon)
         |
         v
    get_top_k_movies()
         |
         v
    [(movie_id, score), ...]   -> ban giao cho Don (Ranking)
"""

from __future__ import annotations

import numpy as np


def cosine_similarity(user_vector: np.ndarray, movie_vector: np.ndarray) -> float:
    """Tinh cosine similarity giua user profile va 1 movie vector.

    Parameters
    ----------
    user_vector : np.ndarray, shape (n_features,)
    movie_vector : np.ndarray, shape (n_features,)

    Returns
    -------
    float
        Gia tri trong [0.0, 1.0].  Tra ve 0.0 neu mot trong hai vector la zero.
    """
    u = user_vector.astype(np.float64)
    m = movie_vector.astype(np.float64)
    norm_u = np.linalg.norm(u)
    norm_m = np.linalg.norm(m)
    if norm_u == 0.0 or norm_m == 0.0:
        return 0.0
    return float(np.dot(u, m) / (norm_u * norm_m))


def cosine_similarity_bulk(
    user_vector: np.ndarray,
    movie_matrix: np.ndarray,
) -> np.ndarray:
    """Tinh cosine similarity giua user profile va TOAN BO movie matrix (vectorized).

    Parameters
    ----------
    user_vector : np.ndarray, shape (n_features,)
    movie_matrix : np.ndarray, shape (n_movies, n_features)

    Returns
    -------
    scores : np.ndarray, shape (n_movies,)
        Cosine similarity cua user voi moi phim.
    """
    u = user_vector.astype(np.float64)
    M = movie_matrix.astype(np.float64)

    norm_u = np.linalg.norm(u)
    if norm_u == 0.0:
        return np.zeros(M.shape[0], dtype=np.float64)

    u_normalized = u / norm_u

    norms_M = np.linalg.norm(M, axis=1, keepdims=True)
    # Tranh chia cho 0 (phim co vector zero)
    norms_M = np.where(norms_M == 0.0, 1.0, norms_M)
    M_normalized = M / norms_M

    scores = M_normalized @ u_normalized  # shape (n_movies,)
    return scores


def get_top_k_movies(
    user_vector: np.ndarray,
    movie_ids: np.ndarray,
    movie_matrix: np.ndarray,
    k: int = 20,
    exclude_ids: "set[int] | None" = None,
) -> "list[tuple[int, float]]":
    """Tra ve Top-K phim phu hop nhat theo Cosine Similarity.

    Parameters
    ----------
    user_vector : np.ndarray, shape (n_features,)
        Vector profile cua user.
    movie_ids : np.ndarray, shape (n_movies,)
        Mang cac movie_id tuong ung voi tung hang cua movie_matrix.
    movie_matrix : np.ndarray, shape (n_movies, n_features)
        Ma tran feature vector cua toan bo phim.
    k : int
        So phim can tra ve (mac dinh 20).
    exclude_ids : set[int], optional
        Tap cac movie_id can loai (phim user da Like/Dislike).

    Returns
    -------
    list[tuple[int, float]]
        [(movie_id, cosine_score), ...] sap xep giam dan theo score.
        Day la dau vao cho module Ranking cua Don.
    """
    exclude = exclude_ids or set()
    scores = cosine_similarity_bulk(user_vector, movie_matrix)

    # Tao mask cho cac phim khong bi loai
    mask = np.array([int(mid) not in exclude for mid in movie_ids], dtype=bool)

    filtered_ids = movie_ids[mask]
    filtered_scores = scores[mask]

    # Sort giam dan
    sorted_indices = np.argsort(filtered_scores)[::-1]

    top_k = sorted_indices[:k]
    result = [
        (int(filtered_ids[i]), float(filtered_scores[i]))
        for i in top_k
    ]
    return result
