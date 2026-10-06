"""
auth.py
--------
Authentication API routes: register, login, logout.
"""

from backend.services.auth_service import register_user, login_user


def register(username: str, email: str, password: str, db_path: str) -> dict:
    """POST /api/auth/register"""
    return register_user(username, email, password, db_path=db_path)


def login(email: str, password: str, db_path: str) -> dict:
    """POST /api/auth/login"""
    return login_user(email, password, db_path=db_path)
