"""
ai/neural_network.py
---------------------
Tier 2 Neural Network: SGDClassifier (logistic regression with SGD)
from scikit-learn, learning online from Like/Dislike history.

Does NOT replace Tier 1 (cosine similarity + ranking).
Only re-scores Tier-1 candidates for extra fine-tuning.

Usage:
    1. After enough interaction data (at least 5-10 like/dislike)
    2. Train model with fit_from_interactions() / partial_fit()
    3. Use rerank_with_nn() to re-score Tier-1 candidates
"""

import os
import pickle

import numpy as np
from sklearn.linear_model import SGDClassifier


class OnlineNeuralRanker:
    """Logistic Regression online learner using SGDClassifier.
    partial_fit() allows learning from small batches (each like/dislike).
    """

    MODEL_PATH = "nn_ranker.pkl"

    def __init__(self, n_features: int):
        self.n_features = n_features
        self.model = SGDClassifier(
            loss="log_loss",        # logistic regression
            learning_rate="optimal",
            random_state=42,
            max_iter=1,             # partial_fit is called many times
            warm_start=True,
        )
        self._fitted = False

    def partial_fit(self, X: np.ndarray, y: np.ndarray):
        """Online update: call on each new Like/Dislike batch.
        X: (n_samples, n_features) — feature vectors
        y: (n_samples,) — 1 = like, 0 = dislike
        """
        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y)
        classes = np.array([0, 1])
        self.model.partial_fit(X, y, classes=classes)
        self._fitted = True

    def fit_from_interactions(self, liked_vectors: list, disliked_vectors: list):
        """Convenience: build X/y from liked/disliked vector lists and partial_fit."""
        X_parts, y_parts = [], []
        if liked_vectors:
            X_parts.append(np.vstack(liked_vectors).astype(np.float32))
            y_parts.append(np.ones(len(liked_vectors), dtype=int))
        if disliked_vectors:
            X_parts.append(np.vstack(disliked_vectors).astype(np.float32))
            y_parts.append(np.zeros(len(disliked_vectors), dtype=int))
        if not X_parts:
            return
        self.partial_fit(np.vstack(X_parts), np.concatenate(y_parts))

    def predict_scores(self, X: np.ndarray) -> np.ndarray:
        """Return P('like') for each candidate. Shape: (n_samples,)."""
        X = np.asarray(X, dtype=np.float32)
        if not self._fitted:
            return np.zeros(X.shape[0], dtype=np.float32)
        proba = self.model.predict_proba(X)[:, 1]  # P(like)
        return proba.astype(np.float32)

    def save(self, path: str = MODEL_PATH):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str = MODEL_PATH) -> "OnlineNeuralRanker":
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)


def rerank_with_nn(
    candidates: list,
    all_vectors: np.ndarray,
    all_movie_ids: np.ndarray,
    ranker: OnlineNeuralRanker,
    blend_alpha: float = 0.3,  # weight of NN score vs Tier-1 score
) -> list:
    """Blend Tier-1 score with NN score:
        final_score = (1 - alpha) * tier1_score + alpha * nn_score

    Parameters
    ----------
    candidates : list of dict from rank_candidates() — each has 'score' and 'movie_id'
    blend_alpha : 0 = ignore NN, 1 = only NN
    """
    if ranker is None or not ranker._fitted or not candidates:
        return candidates

    mid_to_idx = {int(mid): i for i, mid in enumerate(all_movie_ids)}
    vecs = np.vstack([
        all_vectors[mid_to_idx[c["movie_id"]]]
        for c in candidates
        if c["movie_id"] in mid_to_idx
    ]).astype(np.float32)

    nn_scores = ranker.predict_scores(vecs)

    for i, c in enumerate(candidates):
        tier1 = c["score"]
        nn = float(nn_scores[i]) if i < len(nn_scores) else 0.0
        c["score"] = (1 - blend_alpha) * tier1 + blend_alpha * nn

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates
