"""
sqlite_watchlist_repo.py
------------------------
Trien khai WatchlistRepositoryProtocol su dung SQLite (accounts.db).
"""

from __future__ import annotations

import sqlite3
from typing import Any
from server.config import ACCOUNTS_DB


class SqliteWatchlistRepository:
    """Repository quan ly danh sach xem sau trong SQLite."""

    def __init__(self, db_path: str = ACCOUNTS_DB) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_watchlist(self, user_id: str) -> list[WatchlistItemEntity]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT movie_id, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,),
            ).fetchall()
            return [WatchlistItemEntity.from_dict(dict(r)) for r in rows]

    def add_to_watchlist(self, user_id: str, movie_id: int, added_at: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist VALUES (?, ?, ?)",
                (user_id, movie_id, added_at),
            )
            conn.commit()

    def remove_from_watchlist(self, user_id: str, movie_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM watchlist WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
            conn.commit()

