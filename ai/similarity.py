"""
similarity.py
--------------
Cosine similarity utilities for comparing movie feature vectors and
matching a user profile against all movies in the catalogue.
"""

import numpy as np


def cosine_similarity_matrix(query_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between one query vector and every row in a matrix.

    Parameters
    ----------
    query_vector : np.ndarray, shape (n_features,)
    matrix : np.ndarray, shape (n_movies, n_features)

    Returns
    -------
    similarities : np.ndarray, shape (n_movies,)
        Cosine similarity score in [-1, 1] for each movie (higher = more similar).
    """
    query_norm = np.linalg.norm(query_vector)
    if query_norm == 0:
        return np.zeros(matrix.shape[0], dtype=np.float32)

    matrix_norms = np.linalg.norm(matrix, axis=1)
    # Avoid division by zero for zero-norm rows
    matrix_norms = np.where(matrix_norms == 0, 1e-10, matrix_norms)

    similarities = (matrix @ query_vector) / (matrix_norms * query_norm)
    return similarities.astype(np.float32)


def top_k_similar(
    query_vector: np.ndarray,
    movie_ids: np.ndarray,
    matrix: np.ndarray,
    k: int = 20,
    exclude_ids: list = None,
) -> list:
    """Return the top-k most similar movies to a query vector.

    Parameters
    ----------
    query_vector : np.ndarray
        The reference vector (a movie vector or a user profile vector).
    movie_ids : np.ndarray
        Ordered array of movie IDs matching the rows of `matrix`.
    matrix : np.ndarray
        Full feature matrix (all movies).
    k : int
        Number of results to return.
    exclude_ids : list, optional
        Movie IDs to exclude from results (e.g. already-watched movies).

    Returns
    -------
    results : list of dict
        Each dict has keys: 'movie_id', 'score'.
        Sorted descending by score.
    """
    similarities = cosine_similarity_matrix(query_vector, matrix)

    exclude_set = set(exclude_ids or [])
    results = [
        {"movie_id": int(mid), "score": float(score)}
        for mid, score in zip(movie_ids, similarities)
        if int(mid) not in exclude_set
    ]

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]
