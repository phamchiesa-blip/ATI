"""
in_memory_repo.py
-----------------
Cac ban cai dat In-Memory phuc vu Unit Testing va Mocking theo Clean Architecture,
hoan toan khong can file SQLite hay IO o cung.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Set
import numpy as np


class InMemoryMovieRepository:
    """Repository phim luu hoan toan trong RAM cho unit tests."""

    def __init__(
        self,
        movies_meta: Optional[dict[int, dict[str, Any]]] = None,
        movie_vectors: Optional[dict[int, np.ndarray]] = None,
    ) -> None:
        self.movies = movies_meta or {}
        self.vectors = movie_vectors or {}

    def add_movie(self, movie_id: int, meta: dict[str, Any], vector: Optional[np.ndarray] = None) -> None:
        self.movies[movie_id] = meta
        if vector is not None:
            self.vectors[movie_id] = vector

    def get_vector(self, movie_id: int) -> Optional[np.ndarray]:
        return self.vectors.get(movie_id)

    def get_all_vectors(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.vectors:
            return np.array([], dtype=int), np.empty((0, 0), dtype=np.float32)
        mids = sorted(self.vectors.keys())
        matrix = np.vstack([self.vectors[m] for m in mids])
        return np.array(mids, dtype=int), matrix

    def get_metadata(self, movie_id: int) -> Optional[dict[str, Any]]:
        return self.movies.get(movie_id)

    def get_popular_movies(
        self,
        limit: int = 10,
        min_vote_count: int = 500,
        min_vote_average: float = 6.5,
        exclude_ids: Optional[Set[int]] = None,
        exclude_genres: Optional[Set[str]] = None,
    ) -> list[dict[str, Any]]:
        exclude = exclude_ids or set()
        hated = {g.casefold() for g in (exclude_genres or set())}
        candidates = []
        for mid, m in self.movies.items():
            if mid in exclude:
                continue
            if (m.get("vote_count") or 0) < min_vote_count:
                continue
            if (m.get("vote_average") or 0.0) < min_vote_average:
                continue
            genres = {g.casefold() for g in m.get("genres", [])}
            if hated and genres.intersection(hated):
                continue
            candidates.append(m)
        candidates.sort(key=lambda x: x.get("popularity", 0.0), reverse=True)
        return candidates[:limit]

    def list_movies(
        self,
        page: int = 1,
        page_size: int = 20,
        genre: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        items = list(self.movies.values())
        if genre:
            items = [m for m in items if genre in m.get("genres", [])]
        if search:
            s_low = search.lower()
            items = [m for m in items if s_low in m.get("title", "").lower()]
        total = len(items)
        start = (page - 1) * page_size
        return {"total": total, "page": page, "page_size": page_size, "items": items[start : start + page_size]}

    def get_all_movie_rows(self) -> list[dict[str, Any]]:
        import json
        mids = sorted(self.movies.keys())
        return [
            {
                "movie_id": m,
                "title": self.movies[m].get("title", ""),
                "overview": self.movies[m].get("overview", ""),
                "genres": json.dumps(self.movies[m].get("genres", [])),
                "director": self.movies[m].get("director", ""),
                "cast": json.dumps(self.movies[m].get("cast", [])),
                "vote_average": self.movies[m].get("vote_average", 0.0),
                "vote_count": self.movies[m].get("vote_count", 0),
                "popularity": self.movies[m].get("popularity", 0.0),
                "release_date": self.movies[m].get("release_date", ""),
            }
            for m in mids
        ]

    def get_keywords_mapping(self) -> dict[int, list[str]]:
        return {
            mid: m.get("keywords", [])
            for mid, m in self.movies.items()
            if m.get("keywords")
        }

    def get_onboarding_candidates(self) -> list[dict[str, Any]]:
        import json
        mids = sorted(
            self.movies.keys(),
            key=lambda m: (
                -self.movies[m].get("popularity", 0.0),
                -self.movies[m].get("vote_count", 0),
                m,
            ),
        )
        return [
            {
                "movie_id": m,
                "genres": json.dumps(self.movies[m].get("genres", [])),
            }
            for m in mids
            if self.movies[m].get("genres")
        ]


class InMemoryInteractionRepository:
    """Repository tuong tac luu trong RAM cho unit tests."""

    def __init__(self) -> None:
        self._interactions: dict[str, list[dict[str, Any]]] = {}

    def log_interaction(self, user_id: str, movie_id: int, action: str) -> None:
        if action not in ("like", "dislike"):
            raise ValueError(f"action phai la 'like' hoac 'dislike', nhan duoc: {action!r}")
        user_list = self._interactions.setdefault(user_id, [])
        user_list.append({
            "movie_id": movie_id,
            "action": action,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def get_interactions(self, user_id: str) -> list[dict[str, Any]]:
        return list(self._interactions.get(user_id, []))

    def delete_interactions(self, user_id: str) -> None:
        self._interactions.pop(user_id, None)

