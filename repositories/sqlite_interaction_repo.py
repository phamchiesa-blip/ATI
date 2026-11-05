"""
sqlite_interaction_repo.py
--------------------------
Trien khai InteractionRepositoryProtocol su dung SQLite (user_interaction_history).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
for _p in (_ROOT, _DATA_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from domain import InteractionEntity
from feature_store import DEFAULT_DB_PATH, check_db_exists, get_user_interactions, log_interaction


class SqliteInteractionRepository:
    """Repository quan ly luu tru tuong tac Like / Dislike trong SQLite."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        check_db_exists(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def log_interaction(self, user_id: str, movie_id: int, action: str) -> None:
        if action not in ("like", "dislike"):
            raise ValueError(f"action phai la 'like' hoac 'dislike', nhan duoc: {action!r}")
        log_interaction(user_id, movie_id, action, db_path=self.db_path)

    def get_interactions(self, user_id: str) -> list[InteractionEntity]:
        raw = get_user_interactions(user_id, db_path=self.db_path)
        return [InteractionEntity.from_dict(r) for r in raw]

    def delete_interactions(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM user_interaction_history WHERE user_id = ?", (user_id,))
            conn.commit()
