"""
auth_service.py
----------------
Authentication service: user registration, login, and token management.
Stub implementation — integrate with your JWT library of choice.
"""

import hashlib
import uuid
from datetime import datetime, timezone

from backend.database.database import _connect, DEFAULT_DB_PATH


def _hash_password(password: str) -> str:
    """Simple SHA-256 hash. In production use bcrypt or argon2."""
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, email: str, password: str, db_path=DEFAULT_DB_PATH) -> dict:
    """Register a new user. Returns the created user dict or raises ValueError on conflict."""
    conn = _connect(db_path)
    # Ensure users table exists
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
               user_id   TEXT PRIMARY KEY,
               username  TEXT NOT NULL,
               email     TEXT NOT NULL UNIQUE,
               password  TEXT NOT NULL,
               is_active INTEGER DEFAULT 1,
               created_at TEXT
           )"""
    )
    conn.commit()

    existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Email '{email}' is already registered.")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO users (user_id, username, email, password, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, email, _hash_password(password), now),
    )
    conn.commit()
    conn.close()
    return {"user_id": user_id, "username": username, "email": email, "created_at": now}


def login_user(email: str, password: str, db_path=DEFAULT_DB_PATH) -> dict:
    """Validate credentials and return user info. Raises ValueError on failure."""
    conn = _connect(db_path)
    conn.row_factory = __import__("sqlite3").Row
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row is None or row["password"] != _hash_password(password):
        raise ValueError("Invalid email or password.")
    return dict(row)


def get_user_by_id(user_id: str, db_path=DEFAULT_DB_PATH) -> dict:
    conn = _connect(db_path)
    conn.row_factory = __import__("sqlite3").Row
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
