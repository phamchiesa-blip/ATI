"""
api.py  (v2 - Clean Architecture Modular Entrypoint)
-----------------------------------------------------
Entry point FastAPI cho giao dien React va backend cua nhom.
Cac service nghiep vu, xac thuc va bo dinh tuyen duoc tach sang package `server/`.

Chay:
    uvicorn api:app --reload --port 8000
Tai lieu API tu dong: http://localhost:8000/docs
"""

import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import ACCOUNTS_DB, CORS_ORIGINS, DB
from server.database import acc_conn as _acc, db_conn as _db, import_media_csv, init_accounts_db
from server.dependencies import current_user
from server.routers import (
    auth_router,
    evaluation_router,
    movies_router,
    recommendations_router,
    tonight_router,
)
from server.services.movie_service import get_index, get_titles

# Khoi tao bang accounts va cache poster/trailer
init_accounts_db()
import_media_csv()

app = FastAPI(title="Movie Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gan cac Router vao FastAPI App
app.include_router(auth_router)
app.include_router(movies_router)
app.include_router(recommendations_router)
app.include_router(tonight_router)
app.include_router(evaluation_router)

# Xay san chi muc o luong nen de yeu cau dau tien khong phai cho ~vai giay
threading.Thread(target=lambda: (get_index(), get_titles()), daemon=True).start()
