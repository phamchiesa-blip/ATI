"""
ai/baseline.py
---------------
Baseline recommender — no Ranking module, no Neural Network.
Only uses average of liked vectors as profile, sorts purely by cosine similarity.

Used to compare against the proposed approach in Evaluation.
"""

import numpy as np

from ai.similarity import cosine_similarity_matrix


def baseline_recommend(
    liked_vectors: list,
    all_movie_ids: np.ndarray,
    all_vectors: np.ndarray,
    exclude_ids: list = None,
    top_n: int = 10,
) -> list:
    """Baseline: average profile -> cosine sim -> sort -> Top-N (no re-rank).

    Returns
    -------
    list of dict: [{'movie_id': int, 'score': float}, ...]
    """
    if not liked_vectors:
        return []

    # Simple average — no alpha/beta
    profile = np.mean(np.vstack(liked_vectors), axis=0).astype(np.float32)

    sims = cosine_similarity_matrix(profile, all_vectors)

    exclude_set = set(exclude_ids or [])
    results = [
        {"movie_id": int(mid), "score": float(score)}
        for mid, score in zip(all_movie_ids, sims)
        if int(mid) not in exclude_set
    ]
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
