import os
import re
import sys

# Cho phep import code cua nhom (cac module dung import phang)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.join(ROOT, "data_module", "src"), os.path.join(ROOT, "recommendation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from feature_store import check_db_exists, DEFAULT_DB_PATH

DB = os.environ.get("MOVIES_DB", os.path.join(ROOT, "data_module", "src", "movies.db"))
ACCOUNTS_DB = os.environ.get("ACCOUNTS_DB", os.path.join(ROOT, "accounts.db"))
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
EVAL_DIR = os.environ.get("EVAL_RESULTS_DIR", os.path.join(ROOT, "ranking_eval", "results"))

# Kiem tra su ton tai cua DB movies truoc khi chay API
check_db_exists(DB)

# Hang so xac thuc & bao mat
SESSION_SECONDS = 30 * 24 * 3600
LOCK_AFTER = 5
LOCK_SECONDS = 5 * 60
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
COMMON_PASSWORDS = {
    "12345678", "123456789", "1234567890", "11111111", "00000000", "123123123",
    "password", "password1", "password123", "passw0rd", "qwerty123", "qwertyuiop",
    "abc12345", "abcd1234", "iloveyou", "admin123", "letmein123", "welcome1",
    "matkhau123", "12345678a", "1q2w3e4r", "dragon123", "monkey123", "football1",
}

# Hang so cho tinh nang "Hom nay xem gi?"
MOODS = [
    {"id": "happy", "label": "Vui vẻ, nhẹ nhàng", "genres": ["Comedy", "Animation", "Family"],
     "avoid": ["Horror", "War", "Crime"]},
    {"id": "thrill", "label": "Hồi hộp, căng thẳng", "genres": ["Thriller", "Mystery", "Crime"],
     "avoid": ["Family", "Animation"]},
    {"id": "touching", "label": "Cảm động, sâu lắng", "genres": ["Drama", "Romance"], "avoid": ["Horror"]},
    {"id": "excited", "label": "Phấn khích, mãn nhãn", "genres": ["Action", "Adventure", "Science Fiction"],
     "avoid": []},
    {"id": "scary", "label": "Rùng rợn", "genres": ["Horror"], "avoid": ["Comedy", "Family", "Animation"]},
    {"id": "dreamy", "label": "Mơ mộng, kỳ ảo", "genres": ["Fantasy", "Science Fiction", "Animation"],
     "avoid": ["Horror", "War"]},
    {"id": "romantic", "label": "Lãng mạn", "genres": ["Romance"], "avoid": ["Horror", "War"]},
    {"id": "think", "label": "Suy ngẫm", "genres": ["Drama", "History", "Documentary", "Mystery"],
     "avoid": ["Comedy", "Family"]},
]

TIMES = [
    {"id": "short", "label": "Dưới 100 phút", "max": 100},
    {"id": "medium", "label": "Khoảng 2 giờ", "max": 130},
    {"id": "any", "label": "Không giới hạn", "max": None},
]

