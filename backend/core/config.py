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

DB = os.environ.get("MOVIES_DB", os.path.join(ROOT, "data_module", "src", "movies.db"))
ACCOUNTS_DB = os.environ.get("ACCOUNTS_DB", os.path.join(ROOT, "accounts.db"))
EVAL_DIR = os.environ.get("EVAL_RESULTS_DIR", os.path.join(ROOT, "ranking_eval", "results"))
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

