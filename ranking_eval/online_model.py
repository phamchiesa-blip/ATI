"""Optional lightweight online Like/Dislike reranker.

This is a separate second layer. It learns from rows of numeric features and
labels (1=Like, 0=Dislike); it does not alter the first-layer profile or
candidate generation. Requires scikit-learn only when this file is used.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler

ONLINE_SCORE_MODE: str = "logit_minmax"  # "prob" (legacy) | "logit_minmax" (new standardized)

_SCALER_CACHE: dict[str, StandardScaler] = {}


def get_global_movie_feature_scaler(db_path: str = "movies.db") -> StandardScaler:
    """Fit StandardScaler on the full movie feature matrix once and cache.
    
    Guarantees that scaling parameters are derived strictly from the movie catalog,
    completely independent of test user interactions or benchmark splits.
    """
    if db_path not in _SCALER_CACHE:
        from feature_store import get_all_vectors
        _, matrix = get_all_vectors(db_path)
        scaler = StandardScaler().fit(matrix)
        _SCALER_CACHE[db_path] = scaler
    return _SCALER_CACHE[db_path]


class OnlineLikeModel:
    def __init__(self, *, random_state: int = 42, scaler: StandardScaler | None = None) -> None:
        self._model = SGDClassifier(loss="log_loss", random_state=random_state)
        self._scaler = scaler
        self._ready = False

    def partial_fit(self, features, labels) -> "OnlineLikeModel":
        x = np.asarray(features, dtype=np.float64)
        y = np.asarray(labels, dtype=np.int32)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        if self._scaler is not None:
            x = self._scaler.transform(x)
        if not self._ready:
            self._model.partial_fit(x, y, classes=np.array([0, 1]))
            self._ready = True
        else:
            self._model.partial_fit(x, y)
        return self

    @property
    def is_ready(self) -> bool:
        return self._ready

    def decision_function(self, features) -> np.ndarray | float:
        if not self._ready:
            raise RuntimeError("Model is not trained yet; call partial_fit first.")
        x = np.asarray(features, dtype=np.float64)
        single = x.ndim == 1
        if single:
            x = x.reshape(1, -1)
        if self._scaler is not None:
            x = self._scaler.transform(x)
        scores = self._model.decision_function(x)
        return float(scores[0]) if single else scores

    def like_probability(self, features) -> np.ndarray | float:
        if not self._ready:
            raise RuntimeError("Model is not trained yet; call partial_fit first.")
        x = np.asarray(features, dtype=np.float64)
        single = x.ndim == 1
        if single:
            x = x.reshape(1, -1)
        if self._scaler is not None:
            x = self._scaler.transform(x)
        probabilities = self._model.predict_proba(x)[:, 1]
        return float(probabilities[0]) if single else probabilities

    def rerank(self, candidates, feature_key: str = "model_features"):
        """Sort candidate dicts by learned Like probability, preserving fields."""
        result = []
        for candidate in candidates:
            row = dict(candidate)
            row["like_probability"] = self.like_probability(row[feature_key])
            result.append(row)
        return sorted(result, key=lambda row: row["like_probability"], reverse=True)
