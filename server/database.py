import csv
import os
import sqlite3
from contextlib import contextmanager

from server.config import ACCOUNTS_DB, DB, ROOT


@contextmanager
def conn(path: str):
    """Context manager mo ket noi SQLite va commit tu dong."""
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def db_conn():
    """Ket noi toi movies.db."""
    return conn(DB)


def acc_conn():
    """Ket noi toi accounts.db."""
    return conn(ACCOUNTS_DB)


def init_accounts_db() -> None:
    """Khoi tao cac bang quan ly tai khoan, phien, cache poster/trailer, watchlist va onboarding."""
    with acc_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                onboarded INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tmdb_cache (
                movie_id INTEGER PRIMARY KEY, poster_path TEXT, trailer_key TEXT,
                trailer_name TEXT, fetched_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                user_id TEXT NOT NULL, movie_id INTEGER NOT NULL, added_at REAL NOT NULL,
                PRIMARY KEY (user_id, movie_id)
            );
            CREATE TABLE IF NOT EXISTS onboarding (
                user_id TEXT PRIMARY KEY,
                genres TEXT NOT NULL,
                favorites TEXT NOT NULL
            );
            """
        )
        cols = [r["name"] for r in c.execute("PRAGMA table_info(accounts)")]
        if "is_guest" not in cols:
            c.execute("ALTER TABLE accounts ADD COLUMN is_guest INTEGER NOT NULL DEFAULT 0")


def import_media_csv() -> int:
    """Nap poster/trailer tu data_module/tmdb_media.csv vao bang tmdb_cache."""
    path = os.environ.get("TMDB_MEDIA_CSV") or next(
        (p for p in (os.path.join(ROOT, "data_module", "tmdb_media.csv"),
                     os.path.join(ROOT, "tmdb_media.csv")) if os.path.exists(p)), None)
    if not path:
        return 0
    with open(path, newline="", encoding="utf-8") as f:
        rows = [
            (
                int(r["movie_id"]),
                r["poster_path"] or None,
                r["trailer_key"] or None,
                r["trailer_name"] or None,
                0.0,
            )
            for r in csv.DictReader(f)
        ]
    with acc_conn() as c:
        before = c.total_changes
        c.executemany("INSERT OR IGNORE INTO tmdb_cache VALUES (?, ?, ?, ?, ?)", rows)
        return c.total_changes - before

