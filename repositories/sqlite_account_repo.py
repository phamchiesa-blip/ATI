"""
sqlite_account_repo.py
----------------------
Trien khai AccountRepositoryProtocol su dung SQLite (accounts.db).
"""

from __future__ import annotations

import sqlite3
from typing import Any, Optional
from server.config import ACCOUNTS_DB


class SqliteAccountRepository:
    """Repository quan ly tai khoan, phien session va onboarding trong SQLite."""

    def __init__(self, db_path: str = ACCOUNTS_DB) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_by_email(self, email: str) -> Optional[UserAccountEntity]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE email = ?", (email,)).fetchone()
            return UserAccountEntity.from_dict(dict(row)) if row else None

    def get_by_id(self, user_id: str) -> Optional[UserAccountEntity]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE id = ?", (user_id,)).fetchone()
            return UserAccountEntity.from_dict(dict(row)) if row else None

    def create_guest_account(
        self, user_id: str, email: str, name: str, salt: bytes, password_hash: bytes, created_at: float
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO accounts (id, email, name, salt, password_hash, created_at, is_guest) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (user_id, email, name, salt, password_hash, created_at),
            )
            conn.commit()

    def create_user_account(
        self, user_id: str, email: str, name: str, salt: bytes, password_hash: bytes, created_at: float
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO accounts (id, email, name, salt, password_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, email, name, salt, password_hash, created_at),
            )
            conn.commit()

    def upgrade_guest_account(
        self, user_id: str, email: str, name: str, salt: bytes, password_hash: bytes
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE accounts SET email = ?, name = ?, salt = ?, password_hash = ?, is_guest = 0 WHERE id = ?",
                (email, name, salt, password_hash, user_id),
            )
            conn.commit()

    def create_session(self, token_hash: str, user_id: str, expires_at: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?)",
                (token_hash, user_id, expires_at),
            )
            conn.commit()

    def get_account_by_session(self, token_hash: str, current_time: float) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT a.* FROM sessions s JOIN accounts a ON a.id = s.user_id
                   WHERE s.token_hash = ? AND s.expires_at > ?""",
                (token_hash, current_time),
            ).fetchone()
            return dict(row) if row else None

    def delete_session(self, token_hash: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            conn.commit()

    def delete_user_sessions(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.commit()

    def get_onboarding(self, user_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM onboarding WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def save_onboarding(self, user_id: str, genres_json: str, favorites_json: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO onboarding VALUES (?, ?, ?)",
                (user_id, genres_json, favorites_json),
            )
            conn.execute("UPDATE accounts SET onboarded = 1 WHERE id = ?", (user_id,))
            conn.commit()

    def reset_onboarding(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM onboarding WHERE user_id = ?", (user_id,))
            conn.execute("UPDATE accounts SET onboarded = 0 WHERE id = ?", (user_id,))
            conn.commit()

