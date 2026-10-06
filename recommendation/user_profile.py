"""
user_profile.py
---------------
Quan ly User Profile duoi dang vector dac trung, khoi tao tu onboarding
(genre/phim yeu thich) va cap nhat moi khi user Like/Dislike.

Cong thuc cap nhat:
    Like:    Profile = Profile + alpha * MovieVector   (alpha = 1.0)
    Dislike: Profile = Profile - beta  * MovieVector   (beta  = 0.5)
"""

from __future__ import annotations

import numpy as np

# Hyperparameters
ALPHA: float = 1.0   # learning rate cho Like
BETA:  float = 0.5   # learning rate cho Dislike


class UserProfile:
    """Luu tru va cap nhat vector so thich cua mot user.

    Parameters
    ----------
    user_id : str
        Dinh danh duy nhat cua user.
    vector : np.ndarray, optional
        Vector khoi dau (float32).  None -> zero-vector khi nhan tin hieu dau.
    alpha : float
        Learning rate cho Like (mac dinh 1.0).
    beta : float
        Learning rate cho Dislike (mac dinh 0.5).
    """

    def __init__(
        self,
        user_id: str,
        vector: "np.ndarray | None" = None,
        alpha: float = ALPHA,
        beta: float = BETA,
    ) -> None:
        self.user_id = user_id
        self.alpha = alpha
        self.beta = beta
        self._vector: "np.ndarray | None" = (
            vector.astype(np.float32).copy() if vector is not None else None
        )

    # ── Onboarding ──────────────────────────────────────────────────────────

    def seed_from_movies(self, movie_vectors: "list[np.ndarray]") -> None:
        """Tao Initial User Profile tu danh sach phim yeu thich (onboarding).

        Profile ban dau = trung binh cong cua cac movie vector duoc chon.

        Parameters
        ----------
        movie_vectors : list[np.ndarray]
            Danh sach vector cua cac phim user chon trong onboarding.
        """
        if not movie_vectors:
            return
        stacked = np.vstack([v.astype(np.float32) for v in movie_vectors])
        self._vector = stacked.mean(axis=0)

    def _ensure_initialized(self, reference_vector: np.ndarray) -> None:
        """Neu profile chua co vector, khoi tao bang zero vector cung chieu."""
        if self._vector is None:
            self._vector = np.zeros(reference_vector.shape, dtype=np.float32)

    # ── Cap nhat Profile ────────────────────────────────────────────────────

    def apply_like(self, movie_vector: np.ndarray) -> None:
        """Cap nhat profile theo Like.

        Profile = Profile + alpha * MovieVector
        """
        mv = movie_vector.astype(np.float32)
        self._ensure_initialized(mv)
        self._vector = self._vector + self.alpha * mv

    def apply_dislike(self, movie_vector: np.ndarray) -> None:
        """Cap nhat profile theo Dislike.

        Profile = Profile - beta * MovieVector
        """
        mv = movie_vector.astype(np.float32)
        self._ensure_initialized(mv)
        self._vector = self._vector - self.beta * mv

    # ── Truy cap vector ─────────────────────────────────────────────────────

    @property
    def vector(self) -> "np.ndarray | None":
        """Tra ve vector profile hien tai (hoac None neu chua khoi tao)."""
        return self._vector

    def is_initialized(self) -> bool:
        """True neu profile da co it nhat 1 tin hieu."""
        return self._vector is not None

    def __repr__(self) -> str:
        shape = self._vector.shape if self._vector is not None else "uninitialized"
        return f"UserProfile(user_id={self.user_id!r}, shape={shape})"


class UserProfileRegistry:
    """Luu tru nhieu UserProfile trong memory (dung cho demo / testing).

    Trong production, caller tu quan ly persist/load tu DB.
    """

    def __init__(self) -> None:
        self._profiles: "dict[str, UserProfile]" = {}

    def get_or_create(
        self,
        user_id: str,
        alpha: float = ALPHA,
        beta: float = BETA,
    ) -> UserProfile:
        """Lay profile hien co hoac tao moi neu chua co."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id, alpha=alpha, beta=beta)
        return self._profiles[user_id]

    def get(self, user_id: str) -> "UserProfile | None":
        return self._profiles.get(user_id)

    def all_user_ids(self) -> "list[str]":
        return list(self._profiles.keys())
