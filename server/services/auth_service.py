import hashlib
import hmac
import secrets
import sqlite3
import time
from typing import Optional

from fastapi import HTTPException

from repositories.protocols import AccountRepositoryProtocol
from repositories.sqlite_account_repo import SqliteAccountRepository
from server.config import (
    COMMON_PASSWORDS,
    EMAIL_RE,
    LOCK_AFTER,
    LOCK_SECONDS,
    SESSION_SECONDS,
)

_fails: dict[str, list] = {}  # email -> [so lan sai, thoi diem het khoa]
_default_repo: AccountRepositoryProtocol = SqliteAccountRepository()


def get_account_repo() -> AccountRepositoryProtocol:
    return _default_repo


def set_account_repo(repo: AccountRepositoryProtocol) -> None:
    global _default_repo
    _default_repo = repo


def password_problems(password: str, email: str = "") -> list[str]:
    """Quy tac mat khau toi thieu (giong ben giao dien: passwordRules.js)."""
    out = []
    if len(password) < 8:
        out.append("Mật khẩu cần ít nhất 8 ký tự")
    if len(password) > 128:
        out.append("Mật khẩu tối đa 128 ký tự")
    if not (any(ch.isalpha() for ch in password) and any(ch.isdigit() for ch in password)):
        out.append("Mật khẩu cần có cả chữ cái và chữ số")
    if password.lower() in COMMON_PASSWORDS or len(set(password)) < 4:
        out.append("Mật khẩu quá phổ biến hoặc quá đơn giản")
    local = email.split("@")[0].lower()
    if len(local) >= 3 and local in password.lower():
        out.append("Mật khẩu không được chứa phần đầu của email")
    return out


def check_lock(email: str) -> None:
    """Kiem tra xem email co bi tam khoa do dang nhap sai qua nhieu lan khong."""
    f = _fails.get(email)
    if f and f[1] > time.time():
        minutes = int((f[1] - time.time()) // 60) + 1
        raise HTTPException(429, f"Đăng nhập sai quá nhiều lần. Hãy thử lại sau {minutes} phút")


def record_fail(email: str) -> None:
    """Ghi nhan mot lan dang nhap sai."""
    f = _fails.setdefault(email, [0, 0.0])
    f[0] += 1
    if f[0] >= LOCK_AFTER:
        f[0], f[1] = 0, time.time() + LOCK_SECONDS


def hash_password(password: str, salt: bytes) -> bytes:
    """Hash mat khau bang thuat toan scrypt."""
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def token_hash(token: str) -> str:
    """Hash session token bang SHA-256 de luu vao DB."""
    return hashlib.sha256(token.encode()).hexdigest()


def public_user(row) -> dict:
    """Chuyen row DB thanh dict thong tin nguoi dung an toan de tra ve frontend."""
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "onboarded": bool(row["onboarded"]),
        "guest": bool(row["is_guest"]),
    }


def new_session(user_id: str, repo: Optional[AccountRepositoryProtocol] = None) -> dict:
    """Tao session moi va tra ve token cung thong tin user."""
    r = repo or _default_repo
    token = secrets.token_urlsafe(32)
    t_hash = token_hash(token)
    r.create_session(t_hash, user_id, time.time() + SESSION_SECONDS)
    row = r.get_by_id(user_id)
    return {"token": token, "user": public_user(row)}


def row_from_token(authorization: Optional[str], repo: Optional[AccountRepositoryProtocol] = None):
    """Lay account record tu authorization header."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        return None
    r = repo or _default_repo
    return r.get_account_by_session(token_hash(token), time.time())


def create_guest_session(repo: Optional[AccountRepositoryProtocol] = None) -> dict:
    """Tao tai khoan va session cho khach."""
    r = repo or _default_repo
    user_id = "g" + secrets.token_hex(6)
    r.create_guest_account(
        user_id=user_id,
        email=f"{user_id}@guest.invalid",
        name="Khách",
        salt=secrets.token_bytes(16),
        password_hash=secrets.token_bytes(32),
        created_at=time.time(),
    )
    return new_session(user_id, repo=r)


def register_account(
    email: str,
    password: str,
    name: str,
    accept_terms: bool,
    authorization: Optional[str],
    repo: Optional[AccountRepositoryProtocol] = None,
) -> dict:
    """Dang ky tai khoan moi hoac nang cap tu tai khoan khach."""
    clean_email = email.strip().lower()
    clean_name = " ".join(name.split())
    if len(clean_email) > 254 or not EMAIL_RE.match(clean_email):
        raise HTTPException(400, "Email không hợp lệ")
    if not 2 <= len(clean_name) <= 30 or any(ord(ch) < 32 for ch in clean_name):
        raise HTTPException(400, "Tên hiển thị cần từ 2 đến 30 ký tự")
    problems = password_problems(password, clean_email)
    if problems:
        raise HTTPException(400, "; ".join(problems))
    if not accept_terms:
        raise HTTPException(400, "Bạn cần đồng ý với điều khoản sử dụng")

    r = repo or _default_repo
    salt = secrets.token_bytes(16)
    pw_hash = hash_password(password, salt)
    current = row_from_token(authorization, repo=r)

    try:
        if current is not None and current["is_guest"]:
            user_id = current["id"]
            r.upgrade_guest_account(user_id, clean_email, clean_name, salt, pw_hash)
            r.delete_user_sessions(user_id)
        else:
            user_id = "u" + secrets.token_hex(6)
            r.create_user_account(user_id, clean_email, clean_name, salt, pw_hash, time.time())
    except (sqlite3.IntegrityError, Exception) as exc:
        if "UNIQUE" in str(exc) or isinstance(exc, sqlite3.IntegrityError):
            raise HTTPException(409, "Email này đã được đăng ký")
        raise

    return new_session(user_id, repo=r)


def login_account(email: str, password: str, repo: Optional[AccountRepositoryProtocol] = None) -> dict:
    """Xac thuc dang nhap va tao session moi."""
    clean_email = email.strip().lower()
    check_lock(clean_email)
    r = repo or _default_repo
    row = r.get_by_email(clean_email)
    if row is not None and row["is_guest"]:
        row = None
    salt = row["salt"] if row else b"\0" * 16
    ok = hmac.compare_digest(
        hash_password(password[:1024], salt), row["password_hash"] if row else b"\0" * 32
    )
    if row is None or not ok:
        record_fail(clean_email)
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    _fails.pop(clean_email, None)
    return new_session(row["id"], repo=r)


def logout_account(authorization: Optional[str], repo: Optional[AccountRepositoryProtocol] = None) -> dict:
    """Huy session dang ton tai."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token:
        r = repo or _default_repo
        r.delete_session(token_hash(token))
    return {"ok": True}
