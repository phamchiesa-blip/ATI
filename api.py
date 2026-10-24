"""
api.py  (v2)
------------
Lop API giua giao dien React va backend cua nhom. Dat o THU MUC GOC cua repo,
cung cap voi data_module/, recommendation/ va ranking_eval/.

Chay:
    pip install -r requirements-api.txt
    uvicorn api:app --reload --port 8000
Tai lieu API tu dong: http://localhost:8000/docs

Bien moi truong (khong bat buoc):
    MOVIES_DB        duong dan movies.db        (mac dinh data_module/src/movies.db)
    CORS_ORIGINS     them nguon duoc phep goi API, cach nhau bang dau phay (mac dinh: moi cong localhost)
    TMDB_API_KEY     khoa TMDB de lay poster/trailer
    ACCOUNTS_DB      file luu tai khoan          (mac dinh ./accounts.db, tu tao)
    TMDB_MOVIES_CSV  duong dan tmdb_5000_movies.csv   } dung cho trang chi tiet phim
    TMDB_CREDITS_CSV duong dan tmdb_5000_credits*.csv } (runtime, dien vien, ...)
Neu khong dat, API tu tim cac file tmdb_5000_*.csv trong thu muc goc, data/,
data_module/, data_module/data/, data_module/src/.
"""

import ast
import glob
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import sqlite3
import sys
import threading
import time
import unicodedata
from collections import Counter
from contextlib import contextmanager
from typing import List, Optional
from urllib.parse import quote_plus

import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Cho phep import code cua nhom (cac module dung import phang) ────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
for _p in (ROOT, os.path.join(ROOT, "data_module", "src"), os.path.join(ROOT, "recommendation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DB = os.environ.get("MOVIES_DB", os.path.join(ROOT, "data_module", "src", "movies.db"))
ACCOUNTS_DB = os.environ.get("ACCOUNTS_DB", os.path.join(ROOT, "accounts.db"))

import recommender as _rec                                          # noqa: E402
from recommender import like, dislike                               # noqa: E402
from feature_store import (                                         # noqa: E402
    get_all_vectors, get_movie_metadata, get_movie_vector, get_user_interactions,
)
import tmdb_client                                                   # noqa: E402
from similarity import cosine_similarity_bulk                       # noqa: E402
from ranking_eval.frontend_service import (                        # noqa: E402
    onboard_user, recommendations as ranked_recommendations, get_popular_movies,
)

app = FastAPI(title="Movie Recommendation API")
# Cho phep giao dien chay o bat ky cong localhost nao (Vite doi cong neu 5173 ban).
# Muon cho may khac trong mang LAN truy cap: dat CORS_ORIGINS="http://192.168.1.10:5173,..."
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# Co so du lieu
# ═══════════════════════════════════════════════════════════════════════════

@contextmanager
def _conn(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _db():
    return _conn(DB)


def _acc():
    return _conn(ACCOUNTS_DB)


def _init_accounts():
    with _acc() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,            -- chinh la user_id dung o backend cua nhom
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                onboarded INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tmdb_cache (
                movie_id INTEGER PRIMARY KEY, poster_path TEXT, trailer_key TEXT,
                trailer_name TEXT, fetched_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS onboarding (
                user_id TEXT PRIMARY KEY,
                genres TEXT NOT NULL,           -- JSON list
                favorites TEXT NOT NULL         -- JSON list movie_id
            );
            """
        )
        # accounts.db cu (truoc khi co che do khach) chua co cot is_guest
        cols = [r["name"] for r in c.execute("PRAGMA table_info(accounts)")]
        if "is_guest" not in cols:
            c.execute("ALTER TABLE accounts ADD COLUMN is_guest INTEGER NOT NULL DEFAULT 0")


_init_accounts()


# ═══════════════════════════════════════════════════════════════════════════
# Tai khoan
# ═══════════════════════════════════════════════════════════════════════════

SESSION_SECONDS = 30 * 24 * 3600
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
COMMON_PASSWORDS = {
    "12345678", "123456789", "1234567890", "11111111", "00000000", "123123123",
    "password", "password1", "password123", "passw0rd", "qwerty123", "qwertyuiop",
    "abc12345", "abcd1234", "iloveyou", "admin123", "letmein123", "welcome1",
    "matkhau123", "12345678a", "1q2w3e4r", "dragon123", "monkey123", "football1",
}
LOCK_AFTER, LOCK_SECONDS = 5, 5 * 60     # sai 5 lan -> khoa email do 5 phut
_fails: "dict[str, list]" = {}            # email -> [so lan sai, thoi diem het khoa]


def password_problems(password: str, email: str = "") -> "list[str]":
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


def _check_lock(email: str) -> None:
    f = _fails.get(email)
    if f and f[1] > time.time():
        minutes = int((f[1] - time.time()) // 60) + 1
        raise HTTPException(429, f"Đăng nhập sai quá nhiều lần. Hãy thử lại sau {minutes} phút")


def _record_fail(email: str) -> None:
    f = _fails.setdefault(email, [0, 0.0])
    f[0] += 1
    if f[0] >= LOCK_AFTER:
        f[0], f[1] = 0, time.time() + LOCK_SECONDS


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _public(row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "onboarded": bool(row["onboarded"]), "guest": bool(row["is_guest"])}


def _new_session(user_id: str) -> dict:
    token = secrets.token_urlsafe(32)
    with _acc() as c:
        c.execute("INSERT INTO sessions VALUES (?, ?, ?)",
                  (_token_hash(token), user_id, time.time() + SESSION_SECONDS))
        row = c.execute("SELECT * FROM accounts WHERE id = ?", (user_id,)).fetchone()
    return {"token": token, "user": _public(row)}


def _row_from_token(authorization: Optional[str]):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        return None
    with _acc() as c:
        return c.execute(
            """SELECT a.* FROM sessions s JOIN accounts a ON a.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > ?""",
            (_token_hash(token), time.time()),
        ).fetchone()


def current_user(authorization: Optional[str] = Header(None)) -> dict:
    row = _row_from_token(authorization)
    if row is None:
        raise HTTPException(401, "not_authenticated")
    return _public(row)


class RegisterBody(BaseModel):
    email: str
    password: str
    name: str = ""
    accept_terms: bool = False


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/api/auth/guest")
def guest():
    """Tao phien khach: dung duoc moi tinh nang, du lieu gan voi phien nay.
    Neu sau do dang ky, tai khoan khach duoc nang cap (giu nguyen ho so + lich su)."""
    user_id = "g" + secrets.token_hex(6)
    with _acc() as c:
        c.execute(
            "INSERT INTO accounts (id, email, name, salt, password_hash, created_at, is_guest) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (user_id, f"{user_id}@guest.invalid", "Khách",
             secrets.token_bytes(16), secrets.token_bytes(32), time.time()),
        )
    return _new_session(user_id)


@app.post("/api/auth/register")
def register(body: RegisterBody, authorization: Optional[str] = Header(None)):
    email = body.email.strip().lower()
    name = " ".join(body.name.split())
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise HTTPException(400, "Email không hợp lệ")
    if not 2 <= len(name) <= 30 or any(ord(ch) < 32 for ch in name):
        raise HTTPException(400, "Tên hiển thị cần từ 2 đến 30 ký tự")
    problems = password_problems(body.password, email)
    if problems:
        raise HTTPException(400, "; ".join(problems))
    if not body.accept_terms:
        raise HTTPException(400, "Bạn cần đồng ý với điều khoản sử dụng")

    salt = secrets.token_bytes(16)
    pw_hash = _hash_password(body.password, salt)
    current = _row_from_token(authorization)
    try:
        with _acc() as c:
            if current is not None and current["is_guest"]:
                user_id = current["id"]
                c.execute(
                    "UPDATE accounts SET email = ?, name = ?, salt = ?, password_hash = ?, "
                    "is_guest = 0 WHERE id = ?", (email, name, salt, pw_hash, user_id))
                c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))  # token cu het hieu luc
            else:
                user_id = "u" + secrets.token_hex(6)
                c.execute(
                    "INSERT INTO accounts (id, email, name, salt, password_hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (user_id, email, name, salt, pw_hash, time.time()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Email này đã được đăng ký")
    return _new_session(user_id)


@app.post("/api/auth/login")
def login(body: LoginBody):
    email = body.email.strip().lower()
    _check_lock(email)
    with _acc() as c:
        row = c.execute("SELECT * FROM accounts WHERE email = ?", (email,)).fetchone()
    if row is not None and row["is_guest"]:
        row = None
    # So sanh hang so thoi gian de khong lo email nao ton tai
    salt = row["salt"] if row else b"\0" * 16
    ok = hmac.compare_digest(
        _hash_password(body.password[:1024], salt), row["password_hash"] if row else b"\0" * 32
    )
    if row is None or not ok:
        _record_fail(email)
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    _fails.pop(email, None)
    return _new_session(row["id"])


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return user


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token:
        with _acc() as c:
            c.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Tien ich phim
# ═══════════════════════════════════════════════════════════════════════════

_POSTERS: "dict" = {}
_POSTERS_AT = 0.0


def _poster_url(movie_id: int, size: str = "w342") -> "Optional[str]":
    """Poster tu bang tmdb_cache (do fetch_tmdb_posters.py dien). Lam moi moi 60 giay."""
    global _POSTERS, _POSTERS_AT
    if time.time() - _POSTERS_AT > 60:
        with _acc() as c:
            _POSTERS = {r["movie_id"]: r["poster_path"] for r in c.execute(
                "SELECT movie_id, poster_path FROM tmdb_cache WHERE poster_path IS NOT NULL")}
        _POSTERS_AT = time.time()
    p = _POSTERS.get(movie_id)
    return f"https://image.tmdb.org/t/p/{size}{p}" if p else None


def _fold(s: str) -> str:
    """Bo dau + chu thuong de tim kiem 'amelie' ra 'Amélie'."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(ch))


def _card(meta: dict) -> dict:
    """Rut gon metadata thanh du lieu hien thi tren card phim."""
    date = meta.get("release_date") or ""
    return {
        "movie_id": meta["movie_id"],
        "title": meta["title"],
        "overview": meta.get("overview") or "",
        "genres": meta.get("genres", []),
        "director": meta.get("director"),
        "cast": meta.get("cast", []),
        "vote_average": meta.get("vote_average"),
        "popularity": meta.get("popularity"),
        "release_year": int(date[:4]) if date[:4].isdigit() else None,
        "poster_url": _poster_url(meta["movie_id"]),
    }


def _rated_ids(user_id: str) -> "set[int]":
    return {h["movie_id"] for h in get_user_interactions(user_id, db_path=DB)}


# ═══════════════════════════════════════════════════════════════════════════
# Phim: danh sach / chi tiet / tuong tu
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/genres")
def list_genres():
    with _db() as c:
        rows = c.execute("SELECT genres FROM movies").fetchall()
    counter = Counter()
    for r in rows:
        counter.update(json.loads(r["genres"] or "[]"))
    return [{"name": g, "count": n} for g, n in counter.most_common()]


@app.get("/api/showcase")
def showcase(n: int = 12):
    """Phim ngau nhien (trong nhom noi tieng, diem cao) cho trang dang nhap."""
    with _db() as c:
        ids = [r["movie_id"] for r in c.execute(
            "SELECT movie_id FROM movies WHERE vote_count >= 1000 AND vote_average >= 7 "
            "ORDER BY popularity DESC LIMIT 200")]
    pick = random.sample(ids, min(max(n, 3), len(ids)))
    return {"items": [_card(get_movie_metadata(i, db_path=DB)) for i in pick]}


def _get_index() -> dict:
    global _INDEX
    with _LOCK:
        if _INDEX is None:
            _INDEX = _build_index()
        return _INDEX


def _build_index() -> dict:
    """Chi muc ten -> tap movie_id cho loc theo dao dien / dien vien / long tieng / tu khoa.
    Dien vien lay tu DB (5 nguoi dau) va tu CSV (20 nguoi dau) neu co."""
    _load_extra()
    idx = {k: {} for k in ("director", "actor", "voice", "keyword")}

    def add(kind, name, mid):
        e = idx[kind].setdefault(_fold(name), {"name": name, "ids": set()})
        e["ids"].add(mid)

    with _db() as c:
        rows = c.execute('SELECT movie_id, director, "cast" FROM movies').fetchall()
    for r in rows:
        if r["director"]:
            add("director", r["director"], r["movie_id"])
        for n in json.loads(r["cast"] or "[]"):
            add("actor", n, r["movie_id"])
    for mid, people in _CAST20.items():
        for name, is_voice in people:
            add("voice" if is_voice else "actor", name, mid)
            if is_voice:
                add("actor", name, mid)
    for mid, kws in _KW_ALL.items():
        for k in kws:
            add("keyword", k, mid)
    return idx


_TITLES: "Optional[list]" = None


def _titles() -> list:
    """[(movie_id, title, title_da_bo_dau, nam)] xep theo do pho bien giam dan."""
    global _TITLES
    with _LOCK:
        if _TITLES is None:
            with _db() as c:
                rows = c.execute("SELECT movie_id, title, release_date FROM movies "
                                 "ORDER BY popularity DESC").fetchall()
            _TITLES = [(r["movie_id"], r["title"], _fold(r["title"]),
                        int(r["release_date"][:4]) if (r["release_date"] or "")[:4].isdigit() else None)
                       for r in rows]
        return _TITLES


@app.get("/api/suggest")
def suggest(q: str, limit: int = 4):
    key = _fold(q.strip())
    out = {"movies": [], "director": [], "actor": [], "voice": [], "keyword": []}
    if len(key) < 2:
        return out
    out["movies"] = [{"movie_id": mid, "title": title, "release_year": year}
                     for mid, title, folded, year in _titles() if key in folded][:5]
    idx = _get_index()
    for kind in ("director", "actor", "voice", "keyword"):
        hits = [(k, e["name"], len(e["ids"])) for k, e in idx[kind].items() if key in k]
        hits.sort(key=lambda h: (not h[0].startswith(key), -h[2]))
        out[kind] = [{"name": n, "count": c} for _, n, c in hits[:limit]]
    return out


@app.get("/api/movies")
def list_movies(
    query: Optional[str] = None,
    genres: Optional[str] = None,          # "Action,Comedy" -> phim co CA HAI the loai
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_rating: Optional[float] = None,
    director: Optional[str] = None,
    actor: Optional[str] = None,
    voice: Optional[str] = None,
    keyword: Optional[str] = None,
    sort: str = "popularity",              # popularity | rating | newest | oldest | title
    page: int = 1,
    page_size: int = 24,
):
    order = {
        "popularity": "popularity DESC",
        "rating": "vote_average DESC",
        "newest": "release_date DESC",
        "oldest": "release_date ASC",
        "title": "title COLLATE NOCASE ASC",
    }.get(sort, "popularity DESC")

    where, params, order_params = ["1=1"], [], []
    allowed = None
    if query:
        qkey = _fold(query.strip())
        allowed = {mid for mid, _t, folded, _y in _titles() if qkey in folded}
        if sort == "popularity":           # ten bat dau bang tu khoa len truoc
            order = "CASE WHEN title LIKE ? THEN 0 ELSE 1 END, popularity DESC"
            order_params = [f"{query}%"]
    for g in [x.strip() for x in (genres or "").split(",") if x.strip()]:
        where.append("genres LIKE ?")
        params.append(f'%"{g}"%')
    if year_from:
        where.append("release_date >= ?")
        params.append(f"{year_from}-01-01")
    if year_to:
        where.append("release_date <= ?")
        params.append(f"{year_to}-12-31")
    if sort in ("newest", "oldest"):
        where.append("release_date IS NOT NULL")
    if min_rating:
        where.append("vote_average >= ? AND vote_count >= 50")
        params.append(min_rating)
    if sort == "rating":
        where.append("vote_count >= 200")   # tranh phim it luot vote co diem ao

    for kind, value in (("director", director), ("actor", actor), ("voice", voice), ("keyword", keyword)):
        if value:
            ids = _get_index()[kind].get(_fold(value), {}).get("ids", set())
            allowed = ids if allowed is None else allowed & ids
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    if allowed is not None and not allowed:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    with _db() as c:
        ids = [r["movie_id"] for r in c.execute(
            f"SELECT movie_id FROM movies WHERE {' AND '.join(where)} ORDER BY {order}",
            params + order_params)]
    if allowed is not None:
        ids = [i for i in ids if i in allowed]
    start = (page - 1) * page_size
    items = [_card(get_movie_metadata(i, db_path=DB)) for i in ids[start:start + page_size]]
    return {"total": len(ids), "page": page, "page_size": page_size, "items": items}


# --- Thong tin mo rong (runtime, dien vien, ...) doc tu 2 file CSV goc ------

_EXTRA: "Optional[dict]" = None
_KW_ALL: dict = {}      # movie_id -> toan bo tu khoa
_CAST20: dict = {}      # movie_id -> [(ten, la_long_tieng)]
_INDEX: "Optional[dict]" = None


def _find_csv(kind: str) -> "Optional[str]":
    env = os.environ.get(f"TMDB_{kind.upper()}_CSV")
    if env and os.path.exists(env):
        return env
    for d in (ROOT, os.path.join(ROOT, "data"), os.path.join(ROOT, "data_module"),
              os.path.join(ROOT, "data_module", "data"), os.path.join(ROOT, "data_module", "src")):
        hits = sorted(glob.glob(os.path.join(d, f"tmdb_5000_{kind}*.csv")))
        if hits:
            return hits[0]
    return None


def _parse_list(value) -> list:
    if not isinstance(value, str):
        return []
    try:
        out = json.loads(value)               # nhanh hon literal_eval ~10 lan
    except ValueError:
        try:
            out = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
    return [d for d in out if isinstance(d, dict)]


def _names(value, limit=None) -> "list[str]":
    out = [d["name"] for d in _parse_list(value) if d.get("name")]
    return out[:limit] if limit else out


def _clean(x):
    return None if x is None or x != x or x == "" else x


_LOCK = threading.RLock()


def _load_extra() -> dict:
    """Doc CSV 1 lan, giu trong bo nho. Thieu file CSV thi trang chi tiet chi bot thong tin."""
    global _EXTRA
    with _LOCK:
        if _EXTRA is None:
            _EXTRA = _build_extra()
        return _EXTRA


def _build_extra() -> dict:
    extra: dict = {}
    movies_csv, credits_csv = _find_csv("movies"), _find_csv("credits")
    if not movies_csv:
        return extra
    import pandas as pd

    for r in pd.read_csv(movies_csv).to_dict("records"):
        runtime, budget, revenue = _clean(r.get("runtime")), _clean(r.get("budget")), _clean(r.get("revenue"))
        _KW_ALL[int(r["id"])] = _names(r.get("keywords"))
        extra[int(r["id"])] = {
            "tagline": _clean(r.get("tagline")),
            "runtime": int(runtime) if runtime else None,
            "budget": int(budget) if budget else None,
            "revenue": int(revenue) if revenue else None,
            "companies": _names(r.get("production_companies"), 4),
            "countries": _names(r.get("production_countries")),
            "languages": _names(r.get("spoken_languages")),
            "keywords": _names(r.get("keywords"), 10),
            "homepage": _clean(r.get("homepage")),
            "vote_count": int(r["vote_count"]) if _clean(r.get("vote_count")) is not None else None,
            "cast_members": [], "voice_cast": [],
            "crew": {"writers": [], "composers": []},
        }

    if credits_csv:
        for r in pd.read_csv(credits_csv).to_dict("records"):
            entry = extra.get(int(r["movie_id"]))
            if entry is None:
                continue
            cast = sorted(_parse_list(r.get("cast")), key=lambda d: d.get("order", 999))[:20]
            people = []
            for d in cast:
                raw = d.get("character") or ""
                people.append({
                    "name": d.get("name"),
                    "character": re.sub(r"\s*\(.*?\)", "", raw).strip(),
                    "voice": "(voice" in raw.lower(),
                })
            _CAST20[int(r["movie_id"])] = [(p["name"], p["voice"]) for p in people if p["name"]]
            entry["cast_members"] = [p for p in people if not p["voice"]][:12]
            entry["voice_cast"] = [p for p in people if p["voice"]][:12]
            crew = _parse_list(r.get("crew"))
            entry["crew"] = {
                "writers": list(dict.fromkeys(
                    d["name"] for d in crew if d.get("job") in ("Screenplay", "Writer", "Story", "Novel")
                ))[:3],
                "composers": list(dict.fromkeys(
                    d["name"] for d in crew if d.get("job") == "Original Music Composer"
                ))[:2],
            }
    return extra


@app.get("/api/movies/{movie_id}")
def get_movie(movie_id: int):
    meta = get_movie_metadata(movie_id, db_path=DB)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy phim")
    card = _card(meta)
    detail = {**card, "vote_count": meta.get("vote_count"), **_load_extra().get(movie_id, {})}
    year = card["release_year"] or ""
    detail["trailer_url"] = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(f"{card['title']} {year} official trailer")
    )
    same = []
    if card["director"]:
        with _db() as c:
            ids = [r["movie_id"] for r in c.execute(
                "SELECT movie_id FROM movies WHERE director = ? AND movie_id != ? "
                "ORDER BY popularity DESC LIMIT 6", (card["director"], movie_id))]
        same = [_card(get_movie_metadata(i, db_path=DB)) for i in ids]
    detail["same_director"] = same
    detail["poster_url"] = _poster_url(movie_id, "w500") or card["poster_url"]
    return detail


@app.get("/api/movies/{movie_id}/trailer")
def trailer(movie_id: int):
    """Khoa video YouTube cua trailer (tu bang tmdb_cache, hoac goi TMDB neu co key)."""
    meta = get_movie_metadata(movie_id, db_path=DB)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy phim")
    year = (meta.get("release_date") or "")[:4]
    search_url = ("https://www.youtube.com/results?search_query="
                  + quote_plus(f"{meta['title']} {year} official trailer"))
    with _acc() as c:
        row = c.execute("SELECT * FROM tmdb_cache WHERE movie_id = ?", (movie_id,)).fetchone()
    if row is None and tmdb_client.api_key():
        try:
            d = tmdb_client.fetch(movie_id)
        except Exception:
            return {"key": None, "reason": "unavailable", "search_url": search_url}
        with _acc() as c:
            c.execute("INSERT OR REPLACE INTO tmdb_cache VALUES (?, ?, ?, ?, ?)",
                      (movie_id, d["poster_path"], d["trailer_key"], d["trailer_name"], time.time()))
        row = d
    if row is None:
        return {"key": None, "reason": "no_key", "search_url": search_url}
    key = row["trailer_key"]
    return {"key": key, "name": row["trailer_name"], "reason": None if key else "not_found",
            "search_url": search_url}


_ALL: "Optional[tuple]" = None


@app.get("/api/movies/{movie_id}/similar")
def similar_movies(movie_id: int, k: int = 8):
    """Phim co noi dung gan nhat (cosine giua vector phim nay va toan bo phim khac)."""
    global _ALL
    vec = get_movie_vector(movie_id, db_path=DB)
    if vec is None:
        raise HTTPException(404, "Không tìm thấy phim")
    if _ALL is None:
        _ALL = get_all_vectors(db_path=DB)
    ids, matrix = _ALL
    scores = cosine_similarity_bulk(vec, matrix)
    out = []
    for i in np.argsort(scores)[::-1]:
        mid = int(ids[i])
        if mid == movie_id:
            continue
        card = _card(get_movie_metadata(mid, db_path=DB))
        card["similarity"] = round(max(0.0, float(scores[i])) * 100)
        out.append(card)
        if len(out) >= min(max(k, 1), 24):
            break
    return {"items": out}


# ═══════════════════════════════════════════════════════════════════════════
# Ho so nguoi dung: onboarding, Like/Dislike, goi y
# ═══════════════════════════════════════════════════════════════════════════

# Phim yeu thich chon luc onboarding (khong goi y lai chinh chung). Luu trong bo nho.
_seeds: "dict[str, set[int]]" = {}


def _selection(user_id: str) -> "Optional[dict]":
    with _acc() as c:
        row = c.execute("SELECT * FROM onboarding WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    return {"genres": json.loads(row["genres"]), "favorites": json.loads(row["favorites"])}


def _replay_history(user_id: str) -> None:
    prof = _rec._registry.get(user_id)
    if prof is None:
        return
    for ev in get_user_interactions(user_id, db_path=DB):
        vec = get_movie_vector(ev["movie_id"], db_path=DB)
        if vec is not None:
            (prof.apply_like if ev["action"] == "like" else prof.apply_dislike)(vec)


def _ensure_profile(user_id: str) -> None:
    """Backend cua nhom giu profile trong bo nho: tat server la mat phan onboarding.
    Ham nay dung lai profile tu lua chon da luu + lich su Like/Dislike (dung thu tu)."""
    prof = _rec._registry.get(user_id)
    if prof is not None and prof.is_initialized():
        return
    sel = _selection(user_id)
    if sel is None:
        return      # chua chon the loai: de recommender tu dung lai tu lich su
    onboard_user(user_id, db_path=DB, selected_genres=sel["genres"],
                 favorite_movie_ids=sel["favorites"])
    _replay_history(user_id)
    _seeds[user_id] = set(sel["favorites"])


def _popular(user_id: str, k: int) -> dict:
    """Chua co gu: hien phim pho bien, diem tot (de nguoi dung thay danh sach ngay)."""
    rated = _rated_ids(user_id)
    popular = get_popular_movies(db_path=DB, limit=k, exclude_ids=rated)
    items = []
    for meta in popular:
        card = _card(meta)
        card.update(match_percent=None, reasons=[], neural_used=False, cold_start=True)
        items.append(card)
    return {"items": items[:k], "personalized": False, "cold_start": True}


class OnboardingBody(BaseModel):
    genres: List[str] = []
    favorite_movie_ids: List[int] = []


@app.post("/api/onboarding")
def onboarding(body: OnboardingBody, user: dict = Depends(current_user)):
    uid = user["id"]
    _rec._registry._profiles.pop(uid, None)      # onboarding lai thi thay profile cu
    try:
        res = onboard_user(uid, db_path=DB, selected_genres=body.genres,
                           favorite_movie_ids=body.favorite_movie_ids)
    except ValueError as e:
        raise HTTPException(400, str(e))
    favorites = body.favorite_movie_ids if res["profile_source"] == "favorite_movies" else []
    with _acc() as c:
        c.execute("INSERT OR REPLACE INTO onboarding VALUES (?, ?, ?)",
                  (uid, json.dumps(body.genres), json.dumps(favorites)))
        c.execute("UPDATE accounts SET onboarded = 1 WHERE id = ?", (uid,))
    _replay_history(uid)          # doi the loai khong lam mat nhung phim da Thich/Khong thich
    _seeds[uid] = set(favorites)
    return {"ok": True, "seed_count": res["seed_movie_count"]}


@app.get("/api/onboarding")
def get_onboarding(user: dict = Depends(current_user)):
    sel = _selection(user["id"]) or {"genres": [], "favorites": []}
    return sel


class FeedbackBody(BaseModel):
    movie_id: int
    action: str    # "like" | "dislike"


@app.post("/api/feedback")
def feedback(body: FeedbackBody, user: dict = Depends(current_user)):
    uid = user["id"]
    if body.action not in ("like", "dislike"):
        raise HTTPException(400, "action phai la 'like' hoac 'dislike'")
    # Backend chi ghi them, khong hoan tac duoc -> chan danh gia lap lai mot phim.
    if body.movie_id in _rated_ids(uid):
        raise HTTPException(409, "already_rated")
    _ensure_profile(uid)
    try:
        (like if body.action == "like" else dislike)(uid, body.movie_id, db_path=DB)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


@app.get("/api/recommendations")
def recommendations(k: int = 12, mode: str = "proposed", user: dict = Depends(current_user)):
    """mode=proposed: Ranking + Neural Network cua Don. mode=baseline: chi sap theo cosine
    (cach don gian de so sanh, muc 3.9 bao cao)."""
    uid = user["id"]
    _ensure_profile(uid)
    seeds = _seeds.get(uid, set())
    want = k + len(seeds)
    mode = "baseline" if mode == "baseline" else "proposed"
    try:
        if mode == "baseline":
            rows_all = [{"movie_id": m, "cosine": sc, "final_score": sc}
                        for m, sc in _rec.recommend(uid, k=want, db_path=DB)]
        else:
            rows_all = ranked_recommendations(
                uid, db_path=DB, limit=want, candidate_k=max(100, want + 20))["items"]
    except RuntimeError:
        return _popular(uid, k)                       # chua co gu: hien phim pho bien
    except ValueError as e:
        raise HTTPException(400, str(e))
    rows = [r for r in rows_all if r["movie_id"] not in seeds][:k]

    # Ly do goi y: genre trung voi the loai da chon / phim da thich
    sel = _selection(uid) or {"genres": [], "favorites": []}
    has_onboarding = bool(sel.get("genres") or sel.get("favorites"))
    user_history = get_user_interactions(uid, db_path=DB)
    likes = [h["movie_id"] for h in user_history if h["action"] == "like"]
    is_cold_start = (len(likes) == 0) and not has_onboarding

    liked_genres = Counter(sel["genres"])
    liked = list(seeds) + likes
    for mid in liked:
        m = get_movie_metadata(mid, db_path=DB)
        if m:
            liked_genres.update(m["genres"])

    items = []
    for r in rows:
        card = _card(get_movie_metadata(r["movie_id"], db_path=DB))
        card["score"] = round(r["final_score"], 4)
        card["match_percent"] = round(max(0.0, min(1.0, r["final_score"])) * 100)
        card["cosine"] = round(r["cosine"], 4)
        card["neural_used"] = bool(r.get("neural_used"))
        card["reasons"] = [g for g, _ in liked_genres.most_common() if g in card["genres"]][:3]
        # Diem thanh phan (0-1, chuan hoa trong danh sach ung vien) cua module Ranking
        card["breakdown"] = None if "rating_score" not in r else {
            "cosine": round(r["cosine_score"], 3),
            "rating": round(r["rating_score"], 3),
            "popularity": round(r["popularity_score"], 3),
            "newness": round(r["newness_score"], 3),
            "neural": round(r["nn_like_probability"], 3) if r.get("neural_used") else None,
        }
        card["cold_start"] = is_cold_start
        items.append(card)
    return {
        "items": items,
        "personalized": not is_cold_start,
        "cold_start": is_cold_start,
        "mode": mode,
    }


@app.get("/api/history")
def history(user: dict = Depends(current_user)):
    out = []
    for h in get_user_interactions(user["id"], db_path=DB):
        meta = get_movie_metadata(h["movie_id"], db_path=DB)
        if meta:
            out.append({**_card(meta), "action": h["action"], "created_at": h["created_at"]})
    return {"items": out}


@app.delete("/api/me/profile")
def reset_profile(user: dict = Depends(current_user)):
    """Xoa profile + lich su Like/Dislike de lam lai tu dau (khong xoa tai khoan)."""
    uid = user["id"]
    _rec._registry._profiles.pop(uid, None)
    _seeds.pop(uid, None)
    with _db() as c:
        c.execute("DELETE FROM user_interaction_history WHERE user_id = ?", (uid,))
    with _acc() as c:
        c.execute("DELETE FROM onboarding WHERE user_id = ?", (uid,))
        c.execute("UPDATE accounts SET onboarded = 0 WHERE id = ?", (uid,))
    return {"ok": True}


# Xay san chi muc o luong nen de yeu cau dau tien khong phai cho ~vai giay
threading.Thread(target=lambda: (_get_index(), _titles()), daemon=True).start()