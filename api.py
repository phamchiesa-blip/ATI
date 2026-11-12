"""
api.py  (Clean Architecture Entrypoint)
---------------------------------------
Diem khoi chay FastAPI cua he thong goi y phim.
Toan bo kien truc duoc chia tach ro rang trong package `backend/`:
  - backend/core/          : Cau hinh, ket noi SQLite, bao mat & tien ich.
  - backend/schemas/       : Pydantic Request/Response DTOs.
  - backend/repositories/  : Truy cap DB, CSV metadata, TMDB cache & chi muc tim kiem.
  - backend/services/      : Tang Use Cases / Business Logic.
  - backend/routers/       : Tang Presentation / HTTP Controllers.

Chay:
    uvicorn api:app --reload --port 8000
Tai lieu API tu dong: http://localhost:8000/docs
"""

import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import ACCOUNTS_DB, CORS_ORIGINS, DB, ROOT  # noqa: F401
from backend.core.database import (
    import_media_csv,
    import_overview_vi_csv,
    init_accounts_db,
)
from backend.core.security import EMAIL_RE, password_problems  # noqa: F401
from backend.repositories.movie_repository import get_search_index, get_titles_index
from backend.routers import (
    auth_router,
    evaluation_router,
    movie_router,
    recommendation_router,
)
from feature_store import check_db_exists

# Kiem tra movies.db ton tai va khoi tao accounts.db + du lieu cache ban dau
check_db_exists(DB)
init_accounts_db()
import_media_csv()
import_overview_vi_csv()

app = FastAPI(title="Movie Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dang ky cac router theo tung mien nghiep vu (Clean Architecture Presentation Layer)
app.include_router(auth_router.router)
app.include_router(movie_router.router)
app.include_router(recommendation_router.router)
app.include_router(evaluation_router.router)


def _startup_background_tasks() -> None:
    """Xay san chi muc tim kiem va TU DONG dong bo phim moi (2017-2026) tu TMDB API
    neu phat hien movies.db tren may nay van la ban cu (chua co phim sau nam 2017)."""
    try:
        get_search_index()
        get_titles_index()
    except Exception:
        pass

    try:
        import sqlite3
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        new_movies_cnt = cur.execute(
            "SELECT COUNT(*) FROM movies WHERE release_date >= '2018-01-01'"
        ).fetchone()[0]
        conn.close()

        if new_movies_cnt < 30:
            print(
                f"[Startup Sync] Phát hiện movies.db chỉ có {new_movies_cnt} phim từ 2018+. "
                "Đang tự động tải & đồng bộ phim mới (2017–2026) từ TMDB API..."
            )
            from sync_tmdb import sync_movies_from_tmdb
            from backend.repositories.movie_repository import _check_db_reload
            from chatbot import get_feature_space

            res = sync_movies_from_tmdb(
                db_path=DB,
                accounts_db_path=ACCOUNTS_DB,
                mode="years",
                start_year=2017,
                end_year=2026,
                per_year=10,
            )
            _check_db_reload()
            get_search_index()
            get_titles_index()
            get_feature_space(DB)
            print(
                f"[Startup Sync] Hoàn tất! Đã thêm {res.get('inserted', 0)} phim mới "
                f"(Tổng: {res.get('total_movies')} phim trong movies.db)."
            )
    except Exception as exc:
        print(f"[Startup Sync] Bỏ qua đồng bộ tự động: {exc}")


# Chay o luong nen ngay khi khoi dong Backend
threading.Thread(target=_startup_background_tasks, daemon=True).start()
