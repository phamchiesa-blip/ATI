"""
backend/core/config.py
----------------------
Cau hinh duong dan, bien moi truong va hang so he thong.
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (ROOT, os.path.join(ROOT, "data_module", "src"), os.path.join(ROOT, "recommendation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def load_env_file(env_path: str = os.path.join(ROOT, ".env")) -> None:
    """Tu dong nap cac bien moi truong tu file .env o thu muc goc (khong ghi de bien da co san
    va bo qua cac gia tri placeholder mau nhu 'your_gemini_api_key_here')."""
    placeholders = {"your_gemini_api_key_here", "your_tmdb_api_key_here", "your_openai_api_key_here"}
    if os.path.exists(env_path):
        try:
            with open(env_path, encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[7:].strip()
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and val and val not in placeholders and not os.environ.get(key):
                        os.environ[key] = val
        except Exception:
            pass
    # Fallback TMDB API key mac dinh cua du an neu may moi pull code ve chua tao file .env
    if not os.environ.get("TMDB_API_KEY"):
        os.environ["TMDB_API_KEY"] = "fcf8e04d0d4d12b9eac083efb9134563"


load_env_file()

DB = os.environ.get("MOVIES_DB", os.path.join(ROOT, "data_module", "src", "movies.db"))
ACCOUNTS_DB = os.environ.get("ACCOUNTS_DB", os.path.join(ROOT, "accounts.db"))
EVAL_DIR = os.environ.get("EVAL_RESULTS_DIR", os.path.join(ROOT, "ranking_eval", "results"))
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

