"""
feature_store.py
-----------------
Step 3: persist the processed data (from data_pipeline.py +
feature_engineering.py) into a small SQLite database, and expose a simple
API for the rest of the team to use -- nobody else needs to know how the
feature vector was built internally.

Tables (matching the "Data Storage" box in the architecture diagram):
    movies                  -> Movie Dataset + Movie Rating (metadata)
    movie_feature_vectors   -> Movie Feature Vectors (one row per movie)
    user_interaction_history -> placeholder table for Son's Like/Dislike events

Public functions other teammates should use:
    get_movie_vector(movie_id)      -> np.ndarray
    get_all_vectors()               -> (movie_ids, matrix)
    get_movie_metadata(movie_id)    -> dict
    log_interaction(user_id, movie_id, action)  -> None   (for Son)
    get_user_interactions(user_id)  -> list[dict]         (for Son)
"""

import json
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

import numpy as np

DEFAULT_DB_PATH = str(Path(__file__).resolve().parent / "movies.db")


def check_db_exists(db_path: str = DEFAULT_DB_PATH) -> None:
    """Kiểm tra sự tồn tại của cơ sở dữ liệu movies.db.

    Nếu file không tồn tại, báo lỗi rõ ràng bằng tiếng Việt và hướng dẫn cách tạo,
    tuyệt đối không tự tạo database rỗng.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Cơ sở dữ liệu movies.db không tồn tại tại '{db_path}'.\n"
            "Vui lòng tạo cơ sở dữ liệu trước bằng cách chạy lệnh:\n"
            "  python data_module/src/build_dataset.py --movies path/to/tmdb_5000_movies.csv --credits path/to/tmdb_5000_credits.csv --db data_module/src/movies.db"
        )


def _connect(db_path=DEFAULT_DB_PATH, check_exists=True):
    if check_exists:
        check_db_exists(db_path)
    return sqlite3.connect(db_path)


def create_schema(db_path=DEFAULT_DB_PATH):
    conn = _connect(db_path, check_exists=False)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS movies (
            movie_id      INTEGER PRIMARY KEY,
            title         TEXT NOT NULL,
            overview      TEXT,
            overview_vi   TEXT,      -- Vietnamese translated overview (optional/cached)
            tagline       TEXT,
            genres        TEXT,      -- JSON list of strings
            keywords      TEXT,      -- JSON list of strings (all TMDB keywords)
            director      TEXT,
            cast          TEXT,      -- JSON list of strings (top-billed)
            cast_details  TEXT,      -- JSON list of dicts [{name, character, voice}] (top 20)
            crew_details  TEXT,      -- JSON dict {writers: [...], composers: [...]}
            runtime       INTEGER,
            budget        INTEGER,
            revenue       INTEGER,
            companies     TEXT,      -- JSON list of strings
            countries     TEXT,      -- JSON list of strings
            languages     TEXT,      -- JSON list of strings
            homepage      TEXT,
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
        """
    )
    # Ensure backward-compatible migration if `movies` table already existed with fewer columns
    existing_cols = {r[1] for r in cur.execute("PRAGMA table_info(movies)").fetchall()}
    migrations = [
        ("overview_vi", "TEXT"),
        ("tagline", "TEXT"),
        ("keywords", "TEXT"),
        ("cast_details", "TEXT"),
        ("crew_details", "TEXT"),
        ("runtime", "INTEGER"),
        ("budget", "INTEGER"),
        ("revenue", "INTEGER"),
        ("companies", "TEXT"),
        ("countries", "TEXT"),
        ("languages", "TEXT"),
        ("homepage", "TEXT"),
    ]
    for col_name, col_type in migrations:
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE movies ADD COLUMN {col_name} {col_type}")
    conn.commit()
    conn.close()


def save_dataset(df, movie_ids, vectors, db_path=DEFAULT_DB_PATH, overview_vi_map=None):
    """Write the cleaned movie table + feature vectors into the database.
    Safe to re-run: it replaces any existing rows for the same movie_id."""
    create_schema(db_path)
    conn = _connect(db_path)
    cur = conn.cursor()

    # Preserve existing overview_vi translations already stored in movies.db if overview_vi_map is not passed
    existing_vi = {}
    try:
        for mid, txt in cur.execute("SELECT movie_id, overview_vi FROM movies WHERE overview_vi IS NOT NULL"):
            if txt:
                existing_vi[int(mid)] = txt
    except Exception:
        pass
    if overview_vi_map:
        existing_vi.update(overview_vi_map)

    movie_rows = [
        (
            int(row.movie_id),
            row.title,
            row.overview,
            existing_vi.get(int(row.movie_id)),
            getattr(row, "tagline", None) or None,
            json.dumps(row.genres_list, ensure_ascii=False),
            json.dumps(getattr(row, "keywords_list", []), ensure_ascii=False),
            row.director,
            json.dumps(row.cast_list, ensure_ascii=False),
            json.dumps(getattr(row, "cast_details_list", []), ensure_ascii=False),
            json.dumps(getattr(row, "crew_details_dict", {"writers": [], "composers": []}), ensure_ascii=False),
            None if pd_isnull(getattr(row, "runtime", None)) else int(float(row.runtime)),
            int(getattr(row, "budget", 0) or 0),
            int(getattr(row, "revenue", 0) or 0),
            json.dumps(getattr(row, "companies_list", []), ensure_ascii=False),
            json.dumps(getattr(row, "countries_list", []), ensure_ascii=False),
            json.dumps(getattr(row, "languages_list", []), ensure_ascii=False),
            getattr(row, "homepage", None) or None,
            float(row.vote_average),
            int(row.vote_count),
            float(row.popularity),
            None if pd_isnull(row.release_date) else str(row.release_date.date()),
        )
        for row in df.itertuples(index=False)
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO movies
           (movie_id, title, overview, overview_vi, tagline, genres, keywords,
            director, cast, cast_details, crew_details, runtime, budget, revenue,
            companies, countries, languages, homepage,
            vote_average, vote_count, popularity, release_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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


def pd_isnull(value):
    # tiny local helper so this module doesn't need to import pandas
    # just for one null check
    return value is None or value != value


# ---------------------------------------------------------------------
# Public API for teammates (Son, Vo, Don)
# ---------------------------------------------------------------------

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
    """Return every movie's vector at once, for bulk similarity
    computation. Much faster than calling get_movie_vector() in a loop.

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
    """Return a dict with the human-readable info about one movie
    (title, genres, director, cast, rating, popularity, release_date, plus extended metadata) --
    useful for the UI (Vo) and for displaying recommendations."""
    conn = _connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM movies WHERE movie_id = ?", (movie_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    result["genres"] = json.loads(result["genres"] or "[]")
    result["cast"] = json.loads(result["cast"] or "[]")
    for json_col, default_val in (
        ("keywords", "[]"),
        ("cast_details", "[]"),
        ("crew_details", "{}"),
        ("companies", "[]"),
        ("countries", "[]"),
        ("languages", "[]"),
    ):
        if json_col in result:
            try:
                result[json_col] = json.loads(result[json_col] or default_val)
            except Exception:
                result[json_col] = json.loads(default_val)
    return result


def log_interaction(user_id, movie_id, action, db_path=DEFAULT_DB_PATH):
    """Record a Like/Dislike event. `action` must be 'like' or 'dislike'.
    This is the write side of the User Interaction History box; Son's
    Profile Builder should call this every time a user clicks Like/Dislike."""
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
    """Return every Like/Dislike event for one user, oldest first --
    what Son's Profile Builder needs to (re)build a User Profile."""
    conn = _connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT movie_id, action, created_at FROM user_interaction_history
           WHERE user_id = ? ORDER BY created_at ASC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
