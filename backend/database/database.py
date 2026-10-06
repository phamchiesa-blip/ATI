"""
database.py
------------
Persist the processed data (from preprocessing.py + feature_engineering.py)
into a small SQLite database, and expose a simple API for the rest of the
team to use — nobody else needs to know how the feature vector was built.

Tables:
    movies                   -> Movie Dataset + Movie Rating (metadata)
    movie_feature_vectors    -> Movie Feature Vectors (one row per movie)
    user_interaction_history -> Like/Dislike events for User Profile building

Public functions:
    get_movie_vector(movie_id)      -> np.ndarray
    get_all_vectors()               -> (movie_ids, matrix)
    get_movie_metadata(movie_id)    -> dict
    log_interaction(user_id, movie_id, action)  -> None
    get_user_interactions(user_id)  -> list[dict]
"""

import json
import sqlite3
from datetime import datetime, timezone

import numpy as np

DEFAULT_DB_PATH = "movies.db"


def _connect(db_path=DEFAULT_DB_PATH):
    return sqlite3.connect(db_path)


def create_schema(db_path=DEFAULT_DB_PATH):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS movies (
            movie_id      INTEGER PRIMARY KEY,
            title         TEXT NOT NULL,
            overview      TEXT,
            genres        TEXT,      -- JSON list of strings
            director      TEXT,
            cast          TEXT,      -- JSON list of strings (top-billed)
            vote_average  REAL,
            vote_count    INTEGER,
            popularity    REAL,
            release_date  TEXT
        );

        CREATE TABLE IF NOT EXISTS movie_feature_vectors (
            movie_id INTEGER PRIMARY KEY,
            vector   BLOB NOT NULL,  -- float32 numpy array, serialized
            dims     INTEGER NOT NULL,
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        );

        CREATE TABLE IF NOT EXISTS user_interaction_history (
            interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        TEXT NOT NULL,
            movie_id       INTEGER NOT NULL,
            action         TEXT NOT NULL CHECK (action IN ('like', 'dislike')),
            created_at     TEXT NOT NULL,
            FOREIGN KEY (movie_id) REFERENCES movies (movie_id)
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id    TEXT PRIMARY KEY,
            profile    BLOB NOT NULL,
            dims       INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def save_dataset(df, movie_ids, vectors, db_path=DEFAULT_DB_PATH):
    """Write the cleaned movie table + feature vectors into the database.
    Safe to re-run: it replaces any existing rows for the same movie_id."""
    create_schema(db_path)
    conn = _connect(db_path)
    cur = conn.cursor()

    movie_rows = [
        (
            int(row.movie_id),
            row.title,
            row.overview,
            json.dumps(row.genres_list, ensure_ascii=False),
            row.director,
            json.dumps(row.cast_list, ensure_ascii=False),
            float(row.vote_average),
            int(row.vote_count),
            float(row.popularity),
            None if _pd_isnull(row.release_date) else str(row.release_date.date()),
        )
        for row in df.itertuples(index=False)
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO movies
           (movie_id, title, overview, genres, director, cast,
            vote_average, vote_count, popularity, release_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        movie_rows,
    )

    vector_rows = [
        (int(mid), vec.astype(np.float32).tobytes(), int(vec.shape[0]))
        for mid, vec in zip(movie_ids, vectors)
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO movie_feature_vectors (movie_id, vector, dims)
           VALUES (?, ?, ?)""",
        vector_rows,
    )

    conn.commit()
    conn.close()


def _pd_isnull(value):
    """Tiny helper so this module doesn't need to import pandas just for one null check."""
    return value is None or value != value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_movie_vector(movie_id, db_path=DEFAULT_DB_PATH):
    """Return the feature vector (np.ndarray) for one movie, or None if
    the movie_id isn't in the store."""
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT vector, dims FROM movie_feature_vectors WHERE movie_id = ?",
        (movie_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    blob, dims = row
    return np.frombuffer(blob, dtype=np.float32).reshape(dims)


def get_all_vectors(db_path=DEFAULT_DB_PATH):
    """Return every movie's vector at once, for bulk similarity computation.
    Much faster than calling get_movie_vector() in a loop.

    Returns
    -------
    movie_ids : np.ndarray, shape (n_movies,)
    matrix    : np.ndarray, shape (n_movies, n_features)
    """
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT movie_id, vector, dims FROM movie_feature_vectors ORDER BY movie_id"
    ).fetchall()
    conn.close()
    movie_ids = np.array([r[0] for r in rows])
    matrix = np.vstack([np.frombuffer(r[1], dtype=np.float32).reshape(r[2]) for r in rows])
    return movie_ids, matrix


def get_movie_metadata(movie_id, db_path=DEFAULT_DB_PATH):
    """Return a dict with human-readable info about one movie
    (title, genres, director, cast, rating, popularity, release_date)."""
    conn = _connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM movies WHERE movie_id = ?", (movie_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    result["genres"] = json.loads(result["genres"] or "[]")
    result["cast"] = json.loads(result["cast"] or "[]")
    return result


def get_all_metadata(db_path=DEFAULT_DB_PATH):
    """Return metadata for all movies as a dict {movie_id: metadata_dict}."""
    conn = _connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM movies").fetchall()
    conn.close()
    result = {}
    for row in rows:
        d = dict(row)
        d["genres"] = json.loads(d["genres"] or "[]")
        d["cast"] = json.loads(d["cast"] or "[]")
        result[d["movie_id"]] = d
    return result


def log_interaction(user_id, movie_id, action, db_path=DEFAULT_DB_PATH):
    """Record a Like/Dislike event. `action` must be 'like' or 'dislike'."""
    if action not in ("like", "dislike"):
        raise ValueError("action must be 'like' or 'dislike'")
    conn = _connect(db_path)
    conn.execute(
        """INSERT INTO user_interaction_history (user_id, movie_id, action, created_at)
           VALUES (?, ?, ?, ?)""",
        (user_id, movie_id, action, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_user_interactions(user_id, db_path=DEFAULT_DB_PATH):
    """Return every Like/Dislike event for one user, oldest first."""
    conn = _connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT movie_id, action, created_at FROM user_interaction_history
           WHERE user_id = ? ORDER BY created_at ASC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_user_profile(user_id: str, profile: np.ndarray, db_path=DEFAULT_DB_PATH):
    """Save (or update) user profile vector into DB."""
    if profile is None:
        return
    conn = _connect(db_path)
    conn.execute(
        """INSERT OR REPLACE INTO user_profiles (user_id, profile, dims, updated_at)
           VALUES (?, ?, ?, ?)""",
        (user_id, np.asarray(profile, dtype=np.float32).tobytes(),
         int(np.asarray(profile).shape[0]), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def load_user_profile(user_id: str, db_path=DEFAULT_DB_PATH) -> np.ndarray | None:
    """Load user profile vector from DB. Returns None if not present."""
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT profile, dims FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    blob, dims = row
    return np.frombuffer(blob, dtype=np.float32).reshape(dims)
