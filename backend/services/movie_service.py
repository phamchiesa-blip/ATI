"""
movie_service.py
-----------------
Business logic layer for movie operations: search, browse, and metadata lookup.
Sits between the API routes and the database layer.
"""

from backend.database.database import get_movie_metadata, get_all_metadata, DEFAULT_DB_PATH


def get_movie(movie_id: int, db_path=DEFAULT_DB_PATH) -> dict:
    """Fetch a single movie's metadata by ID. Returns None if not found."""
    return get_movie_metadata(movie_id, db_path=db_path)


def search_movies(query: str, db_path=DEFAULT_DB_PATH, limit: int = 20) -> list:
    """Simple title/overview full-text search using SQLite LIKE.

    Parameters
    ----------
    query : str
        Search term to match against title and overview.
    limit : int
        Maximum number of results to return.

    Returns
    -------
    list of dict (movie metadata)
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    pattern = f"%{query}%"
    rows = conn.execute(
        """SELECT * FROM movies
           WHERE title LIKE ? OR overview LIKE ?
           LIMIT ?""",
        (pattern, pattern, limit),
    ).fetchall()
    conn.close()

    import json
    results = []
    for row in rows:
        d = dict(row)
        d["genres"] = json.loads(d["genres"] or "[]")
        d["cast"] = json.loads(d["cast"] or "[]")
        results.append(d)
    return results


def get_popular_movies(db_path=DEFAULT_DB_PATH, limit: int = 20) -> list:
    """Return the most popular movies by vote_count * vote_average (Wilson score proxy)."""
    import sqlite3, json

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT * FROM movies
           ORDER BY (vote_count * vote_average) DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        d = dict(row)
        d["genres"] = json.loads(d["genres"] or "[]")
        d["cast"] = json.loads(d["cast"] or "[]")
        results.append(d)
    return results
