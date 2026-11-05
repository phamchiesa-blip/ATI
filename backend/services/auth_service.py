"""
backend/services/auth_service.py
--------------------------------
Use cases cho xac thuc & quan ly phien nguoi dung (Khach, Dang ky, Dang nhap, Dang xuat).
"""

import hmac
import secrets
import sqlite3
import time
from typing import Optional

from fastapi import Header, HTTPException

from backend.core.database import accounts_db
from backend.core.security import (
    EMAIL_RE,
    LOCK_AFTER,
    LOCK_SECONDS,
    SESSION_SECONDS,
    hash_password,
    password_problems,
    token_hash,
)

# Theo doi so lan dang nhap sai: email -> [so lan sai, thoi diem het khoa]
_fails: dict[str, list] = {}


def check_lock(email: str) -> None:
    f = _fails.get(email)
    if f and f[1] > time.time():
        minutes = int((f[1] - time.time()) // 60) + 1
        raise HTTPException(429, f"Đăng nhập sai quá nhiều lần. Hãy thử lại sau {minutes} phút")


def record_fail(email: str) -> None:
    f = _fails.setdefault(email, [0, 0.0])
    f[0] += 1
    if f[0] >= LOCK_AFTER:
        f[0], f[1] = 0, time.time() + LOCK_SECONDS


def public_user(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "onboarded": bool(row["onboarded"]),
        "guest": bool(row["is_guest"]),
    }


def create_session(user_id: str) -> dict:
    token = secrets.token_urlsafe(32)
    with accounts_db() as c:
        c.execute(
            "INSERT INTO sessions VALUES (?, ?, ?)",
            (token_hash(token), user_id, time.time() + SESSION_SECONDS),
        )
        row = c.execute("SELECT * FROM accounts WHERE id = ?", (user_id,)).fetchone()
    return {"token": token, "user": public_user(row)}


def row_from_token(authorization: Optional[str]):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        return None
    with accounts_db() as c:
        return c.execute(
            """SELECT a.* FROM sessions s JOIN accounts a ON a.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > ?""",
            (token_hash(token), time.time()),
        ).fetchone()


def current_user(authorization: Optional[str] = Header(None)) -> dict:
    row = row_from_token(authorization)
    if row is None:
        raise HTTPException(401, "not_authenticated")
    return public_user(row)


def create_guest_session() -> dict:
    user_id = "g" + secrets.token_hex(6)
    with accounts_db() as c:
        c.execute(
            "INSERT INTO accounts (id, email, name, salt, password_hash, created_at, is_guest) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (
                user_id,
                f"{user_id}@guest.invalid",
                "Khách",
                secrets.token_bytes(16),
                secrets.token_bytes(32),
                time.time(),
            ),
        )
    return create_session(user_id)


def register_account(
    email_raw: str,
    password: str,
    name_raw: str,
    accept_terms: bool,
    authorization: Optional[str] = None,
) -> dict:
    email = email_raw.strip().lower()
    name = " ".join(name_raw.split())
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise HTTPException(400, "Email không hợp lệ")
    if not 2 <= len(name) <= 30 or any(ord(ch) < 32 for ch in name):
        raise HTTPException(400, "Tên hiển thị cần từ 2 đến 30 ký tự")
    problems = password_problems(password, email)
    if problems:
        raise HTTPException(400, "; ".join(problems))
    if not accept_terms:
        raise HTTPException(400, "Bạn cần đồng ý với điều khoản sử dụng")

    salt = secrets.token_bytes(16)
    pw_hash = hash_password(password, salt)
    current = row_from_token(authorization)
    try:
        with accounts_db() as c:
            if current is not None and current["is_guest"]:
                user_id = current["id"]
                c.execute(
                    "UPDATE accounts SET email = ?, name = ?, salt = ?, password_hash = ?, "
                    "is_guest = 0 WHERE id = ?",
                    (email, name, salt, pw_hash, user_id),
                )
                c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            else:
                user_id = "u" + secrets.token_hex(6)
                c.execute(
                    "INSERT INTO accounts (id, email, name, salt, password_hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, email, name, salt, pw_hash, time.time()),
                )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Email này đã được đăng ký")
    return create_session(user_id)


def login_account(email_raw: str, password: str) -> dict:
    email = email_raw.strip().lower()
    check_lock(email)
    with accounts_db() as c:
        row = c.execute("SELECT * FROM accounts WHERE email = ?", (email,)).fetchone()
    if row is not None and row["is_guest"]:
        row = None
    salt = row["salt"] if row else b"\0" * 16
    ok = hmac.compare_digest(
        hash_password(password[:1024], salt), row["password_hash"] if row else b"\0" * 32
    )
    if row is None or not ok:
        record_fail(email)
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    _fails.pop(email, None)
    return create_session(row["id"])


def logout_session(authorization: Optional[str] = None) -> dict:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token:
        with accounts_db() as c:
            c.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
    return {"ok": True}

