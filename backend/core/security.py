"""
backend/core/security.py
------------------------
Ma hoa mat khau, kiem tra do manh mat khau, token hashing va tien ich xu ly chuoi.
"""

import hashlib
import re
import unicodedata

SESSION_SECONDS = 30 * 24 * 3600
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
COMMON_PASSWORDS = {
    "12345678", "123456789", "1234567890", "11111111", "00000000", "123123123",
    "password", "password1", "password123", "passw0rd", "qwerty123", "qwertyuiop",
    "abc12345", "abcd1234", "iloveyou", "admin123", "letmein123", "welcome1",
    "matkhau123", "12345678a", "1q2w3e4r", "dragon123", "monkey123", "football1",
}
LOCK_AFTER = 5
LOCK_SECONDS = 5 * 60


def password_problems(password: str, email: str = "") -> list[str]:
    """Quy tac mat khau toi thieu (khop voi passwordRules.js tren giao dien)."""
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


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def fold_text(s: str) -> str:
    """Bo dau + chu thuong de tim kiem khong dau ('amelie' -> 'Amélie')."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(ch)
    )

