"""Backend-facing service functions for the Frontend team.

These functions define JSON-friendly inputs/outputs without choosing a web
framework. A FastAPI/Flask route can call them directly. Data is read from the
Part I SQLite store; Like/Dislike and profile seeding use Part II public APIs;
recommendations use Part III ranking.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
_RECOMMENDATION = os.path.join(_ROOT, "recommendation")
for _path in (_DATA_SRC, _RECOMMENDATION):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from feature_store import get_movie_metadata
from recommender import (
    dislike as core_dislike,
    like as core_like,
    seed_profile_from_onboarding,
)

from .integration import get_ranked_recommendations


def _decode_movie(row):
    item = dict(row)
    item["genres"] = json.loads(item.get("genres") or "[]")
    item["cast"] = json.loads(item.get("cast") or "[]")
    return item


def list_movies(
    *,
    db_path: str,
    page: int = 1,
    page_size: int = 20,
    genre: str | None = None,
    search: str | None = None,
) -> dict:
    """Browse movies with pagination and optional exact genre/title filters."""
    if page < 1 or page_size < 1 or page_size > 100:
        raise ValueError("page must be >= 1 and page_size must be between 1 and 100")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM movies"
    params = []
    if search:
        query += " WHERE title LIKE ?"
        params.append(f"%{search}%")
    query += " ORDER BY title COLLATE NOCASE"
    records = [_decode_movie(row) for row in conn.execute(query, params).fetchall()]
    conn.close()

    if genre:
        wanted = genre.casefold()
        records = [row for row in records if wanted in [g.casefold() for g in row["genres"]]]
    total = len(records)
    start = (page - 1) * page_size
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": records[start:start + page_size],
    }


def onboard_user(
    user_id: str,
    *,
    db_path: str,
    selected_genres: list[str] | None = None,
    favorite_movie_ids: list[int] | None = None,
) -> dict:
    """Seed Part II's initial profile from favorite movies or chosen genres.

    If favorite movie IDs are provided, use those as the stronger signal.
    Otherwise, seed from the vectors of all stored movies matching the chosen
    genre(s). The Part II profile builder then averages those movie vectors.
    """
    genres = [genre.strip() for genre in (selected_genres or []) if genre.strip()]
    movie_ids = list(dict.fromkeys(int(mid) for mid in (favorite_movie_ids or [])))
    source = "favorite_movies"
    if not movie_ids and genres:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT movie_id, genres FROM movies").fetchall()
        conn.close()
        wanted = {genre.casefold() for genre in genres}
        for movie_id, genres_json in rows:
            stored_genres = json.loads(genres_json or "[]")
            if wanted.intersection(genre.casefold() for genre in stored_genres):
                movie_ids.append(int(movie_id))
        source = "selected_genres"

    if not movie_ids:
        raise ValueError("Choose at least one genre or favorite movie to start a profile")
    valid_ids = [mid for mid in movie_ids if get_movie_metadata(mid, db_path=db_path) is not None]
    if not valid_ids:
        raise ValueError("None of the selected movies exist in the movie database")

    seed_profile_from_onboarding(user_id, valid_ids, db_path=db_path)
    return {
        "ok": True,
        "user_id": user_id,
        "profile_source": source,
        "seed_movie_count": len(valid_ids),
        "selected_genres": genres,
    }


def record_interaction(
    user_id: str,
    movie_id: int,
    action: str,
    *,
    db_path: str,
) -> dict:
    """Pass Like/Dislike to Part II, which updates profile and stores history."""
    if action not in ("like", "dislike"):
        raise ValueError("action must be 'like' or 'dislike'")
    if get_movie_metadata(int(movie_id), db_path=db_path) is None:
        raise ValueError(f"movie_id={movie_id} does not exist")
    handler = core_like if action == "like" else core_dislike
    handler(user_id, int(movie_id), db_path=db_path)
    return {"ok": True, "user_id": user_id, "movie_id": int(movie_id), "action": action}


def recommendations(
    user_id: str,
    *,
    db_path: str,
    limit: int = 10,
    candidate_k: int = 100,
) -> dict:
    """Return a JSON-friendly ranked list for the View Recommendations screen."""
    if limit < 1 or candidate_k < limit:
        raise ValueError("Require limit >= 1 and candidate_k >= limit")
    items = get_ranked_recommendations(
        user_id,
        candidate_k=candidate_k,
        top_n=limit,
        db_path=db_path,
    )
    return {
        "user_id": user_id,
        "count": len(items),
        "items": items,
    }
