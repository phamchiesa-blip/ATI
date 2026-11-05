"""
sqlite_movie_repo.py
--------------------
Trien khai MovieRepositoryProtocol su dung SQLite (movies.db).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from typing import Any, Optional, Set
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
for _p in (_ROOT, _DATA_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from domain import MovieEntity, PagedMoviesDTO
from feature_store import (
    DEFAULT_DB_PATH,
    check_db_exists,
    get_all_vectors as _get_all_vectors,
    get_movie_metadata as _get_movie_metadata,
    get_movie_vector as _get_movie_vector,
)


class SqliteMovieRepository:
    """Repository truy xuat phim va feature vector tu co so du lieu SQLite."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        check_db_exists(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_vector(self, movie_id: int) -> Optional[np.ndarray]:
        return _get_movie_vector(movie_id, db_path=self.db_path)

    def get_all_vectors(self) -> tuple[np.ndarray, np.ndarray]:
        return _get_all_vectors(db_path=self.db_path)

    def get_metadata(self, movie_id: int) -> Optional[MovieEntity]:
        raw = _get_movie_metadata(movie_id, db_path=self.db_path)
        return MovieEntity.from_dict(raw) if raw is not None else None

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

        with self._connect() as conn:
            query = """
                SELECT * FROM movies
                WHERE vote_count >= ? AND vote_average >= ?
                ORDER BY popularity DESC
            """
            rows = conn.execute(query, (min_vote_count, min_vote_average)).fetchall()

        results = []
        for r in rows:
            mid = int(r["movie_id"])
            if mid in exclude:
                continue
            item = dict(r)
            item["genres"] = json.loads(item.get("genres") or "[]")
            item["cast"] = json.loads(item.get("cast") or "[]")
            if hated:
                movie_genres = {g.casefold() for g in item.get("genres", [])}
                if movie_genres.intersection(hated):
                    continue
            results.append(MovieEntity.from_dict(item))
            if len(results) >= limit:
                break
        return results

    def list_movies(
        self,
        page: int = 1,
        page_size: int = 20,
        genre: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        if page < 1 or page_size < 1 or page_size > 100:
            raise ValueError("page must be >= 1 and page_size must be between 1 and 100")

        query = "SELECT * FROM movies"
        conditions: list[str] = []
        params: list[Any] = []

        if genre:
            conditions.append("genres LIKE ?")
            params.append(f'%"{genre}"%')
        if search:
            conditions.append("title LIKE ?")
            params.append(f"%{search}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with self._connect() as conn:
            count_query = f"SELECT COUNT(*) FROM ({query})"
            total = conn.execute(count_query, params).fetchone()[0]

            query += " ORDER BY popularity DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])
            rows = conn.execute(query, params).fetchall()

        items = []
        for r in rows:
            item = dict(r)
            item["genres"] = json.loads(item.get("genres") or "[]")
            item["cast"] = json.loads(item.get("cast") or "[]")
            items.append(item)

        return PagedMoviesDTO(total=total, page=page, page_size=page_size, items=[MovieEntity.from_dict(m) for m in items])

    def get_all_movie_rows(self) -> list[dict[str, Any]]:
        """Lay toan bo metadata phim sap xep theo movie_id."""
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT movie_id, title, overview, genres, director, "cast", '
                'vote_average, vote_count, popularity, release_date '
                'FROM movies ORDER BY movie_id'
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                raw_g = item.get("genres")
                item["genres"] = raw_g if isinstance(raw_g, list) else json.loads(raw_g or "[]")
                raw_c = item.get("cast")
                item["cast"] = raw_c if isinstance(raw_c, list) else json.loads(raw_c or "[]")
                out.append(MovieEntity.from_dict(item))
            return out

    def get_keywords_mapping(self) -> dict[int, list[str]]:
        """Lay ban do movie_id -> danh sach tu khoa TMDB tu file CSV neu co."""
        env = os.environ.get("TMDB_MOVIES_CSV")
        candidates = [
            env,
            os.path.join(_ROOT, "tmdb_5000_movies.csv"),
            os.path.join(_ROOT, "data", "tmdb_5000_movies.csv"),
            os.path.join(_ROOT, "data_module", "data", "tmdb_5000_movies.csv"),
            os.path.join(_ROOT, "data_module", "src", "tmdb_5000_movies.csv"),
        ]
        csv_path = next((p for p in candidates if p and os.path.exists(p)), None)
        if not csv_path:
            return {}

        mapping: dict[int, list[str]] = {}
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            for mid_val, kw_val in zip(df["id"], df.get("keywords", [])):
                if not isinstance(kw_val, str):
                    continue
                try:
                    items = json.loads(kw_val)
                    names = [it["name"].strip() for it in items if it.get("name")]
                    if names:
                        mapping[int(mid_val)] = names
                except Exception:
                    pass
        except Exception:
            pass
        return mapping

    def get_onboarding_candidates(self) -> list[dict[str, Any]]:
        """Lay danh sach phim sap xep theo do pho bien va luot vote phuc vu onboarding."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT movie_id, title, overview, genres, director, "cast",
                      vote_average, vote_count, popularity, release_date FROM movies
                   WHERE genres IS NOT NULL AND genres != '[]'
                   ORDER BY popularity DESC, vote_count DESC, movie_id ASC"""
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                raw_g = item.get("genres")
                item["genres"] = raw_g if isinstance(raw_g, list) else json.loads(raw_g or "[]")
                out.append(MovieEntity.from_dict(item))
            return out
