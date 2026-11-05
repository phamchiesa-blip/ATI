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

# Xay san chi muc o luong nen de yeu cau dau tien khong phai cho
threading.Thread(target=lambda: (get_search_index(), get_titles_index()), daemon=True).start()
