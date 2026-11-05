import ast
import glob
import json
import os
import random
import re
import threading
import time
import unicodedata
from collections import Counter
from typing import Optional
from urllib.parse import quote_plus

import numpy as np
from fastapi import HTTPException

import tmdb_client
from domain import MovieCardDTO
from feature_store import get_all_vectors, get_movie_metadata, get_movie_vector
from server.config import DB, ROOT
from server.database import acc_conn, db_conn
from similarity import cosine_similarity_bulk

_POSTERS: dict = {}
_POSTERS_AT = 0.0

_LOCK = threading.RLock()
_EXTRA: Optional[dict] = None
_KW_ALL: dict = {}
_CAST20: dict = {}
_INDEX: Optional[dict] = None
_TITLES: Optional[list] = None
_ALL_VECTORS: Optional[tuple] = None


def poster_url(movie_id: int, size: str = "w342") -> Optional[str]:
    """Poster tu bang tmdb_cache. Lam moi cache moi 60 giay."""
    global _POSTERS, _POSTERS_AT
    if time.time() - _POSTERS_AT > 60:
        with acc_conn() as c:
            _POSTERS = {
                r["movie_id"]: r["poster_path"]
                for r in c.execute("SELECT movie_id, poster_path FROM tmdb_cache WHERE poster_path IS NOT NULL")
            }
        _POSTERS_AT = time.time()
    p = _POSTERS.get(movie_id)
    return f"https://image.tmdb.org/t/p/{size}{p}" if p else None


def fold(s: str) -> str:
    """Bo dau + chu thuong de tim kiem 'amelie' ra 'Amélie'."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(ch))


def card(meta: dict) -> MovieCardDTO:
    """Rut gon metadata thanh du lieu card phim cho frontend."""
    date = meta.get("release_date") or ""
    return MovieCardDTO(
        movie_id=meta["movie_id"],
        title=meta["title"],
        overview=meta.get("overview") or "",
        genres=meta.get("genres", []),
        director=meta.get("director"),
        cast=meta.get("cast", []),
        vote_average=meta.get("vote_average"),
        popularity=meta.get("popularity"),
        release_year=int(date[:4]) if date[:4].isdigit() else None,
        poster_url=poster_url(meta["movie_id"]),
    )


def find_csv(kind: str) -> Optional[str]:
    """Tim duong dan file CSV tmdb_5000_movies hoac credits."""
    env = os.environ.get(f"TMDB_{kind.upper()}_CSV")
    if env and os.path.exists(env):
        return env
    for d in (ROOT, os.path.join(ROOT, "data"), os.path.join(ROOT, "data_module"),
              os.path.join(ROOT, "data_module", "data"), os.path.join(ROOT, "data_module", "src")):
        hits = sorted(glob.glob(os.path.join(d, f"tmdb_5000_{kind}*.csv")))
        if hits:
            return hits[0]
    return None


def parse_list(value) -> list:
    if not isinstance(value, str):
        return []
    try:
        out = json.loads(value)
    except ValueError:
        try:
            out = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
    return [d for d in out if isinstance(d, dict)]


def names(value, limit=None) -> list[str]:
    out = [d["name"] for d in parse_list(value) if d.get("name")]
    return out[:limit] if limit else out


def clean_val(x):
    return None if x is None or x != x or x == "" else x


def load_extra() -> dict:
    """Doc CSV 1 lan, luu trong bo nho (runtime, dien vien chi tiet, doanh thu...)."""
    global _EXTRA
    with _LOCK:
        if _EXTRA is None:
            _EXTRA = _build_extra()
        return _EXTRA


def _build_extra() -> dict:
    extra: dict = {}
    movies_csv, credits_csv = find_csv("movies"), find_csv("credits")
    if not movies_csv:
        return extra
    import pandas as pd

    for r in pd.read_csv(movies_csv).to_dict("records"):
        runtime = clean_val(r.get("runtime"))
        budget = clean_val(r.get("budget"))
        revenue = clean_val(r.get("revenue"))
        _KW_ALL[int(r["id"])] = names(r.get("keywords"))
        extra[int(r["id"])] = {
            "tagline": clean_val(r.get("tagline")),
            "runtime": int(runtime) if runtime else None,
            "budget": int(budget) if budget else None,
            "revenue": int(revenue) if revenue else None,
            "companies": names(r.get("production_companies"), 4),
            "countries": names(r.get("production_countries")),
            "languages": names(r.get("spoken_languages")),
            "keywords": names(r.get("keywords"), 10),
            "homepage": clean_val(r.get("homepage")),
            "vote_count": int(r["vote_count"]) if clean_val(r.get("vote_count")) is not None else None,
            "cast_members": [],
            "voice_cast": [],
            "crew": {"writers": [], "composers": []},
        }

    if credits_csv:
        for r in pd.read_csv(credits_csv).to_dict("records"):
            entry = extra.get(int(r["movie_id"]))
            if entry is None:
                continue
            cast_list = sorted(parse_list(r.get("cast")), key=lambda d: d.get("order", 999))[:20]
            people = []
            for d in cast_list:
                raw = d.get("character") or ""
                people.append({
                    "name": d.get("name"),
                    "character": re.sub(r"\s*\(.*?\)", "", raw).strip(),
                    "voice": "(voice" in raw.lower(),
                })
            _CAST20[int(r["movie_id"])] = [(p["name"], p["voice"]) for p in people if p["name"]]
            entry["cast_members"] = [p for p in people if not p["voice"]][:12]
            entry["voice_cast"] = [p for p in people if p["voice"]][:12]
            crew = parse_list(r.get("crew"))
            entry["crew"] = {
                "writers": list(dict.fromkeys(
                    d["name"] for d in crew if d.get("job") in ("Screenplay", "Writer", "Story", "Novel")
                ))[:3],
                "composers": list(dict.fromkeys(
                    d["name"] for d in crew if d.get("job") == "Original Music Composer"
                ))[:2],
            }
    return extra


def get_index() -> dict:
    """Chi muc tim kiem theo dao dien / dien vien / voice / keyword."""
    global _INDEX
    with _LOCK:
        if _INDEX is None:
            _INDEX = _build_index()
        return _INDEX


def _build_index() -> dict:
    load_extra()
    idx = {k: {} for k in ("director", "actor", "voice", "keyword")}

    def add(kind, name, mid):
        e = idx[kind].setdefault(fold(name), {"name": name, "ids": set()})
        e["ids"].add(mid)

    with db_conn() as c:
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


def get_titles() -> list:
    """Danh sach [(movie_id, title, folded_title, year)] xep theo do pho bien giam dan."""
    global _TITLES
    with _LOCK:
        if _TITLES is None:
            with db_conn() as c:
                rows = c.execute("SELECT movie_id, title, release_date FROM movies ORDER BY popularity DESC").fetchall()
            _TITLES = [
                (
                    r["movie_id"],
                    r["title"],
                    fold(r["title"]),
                    int(r["release_date"][:4]) if (r["release_date"] or "")[:4].isdigit() else None,
                )
                for r in rows
            ]
        return _TITLES


def get_genres_distribution() -> list[dict]:
    with db_conn() as c:
        rows = c.execute("SELECT genres FROM movies").fetchall()
    counter = Counter()
    for r in rows:
        counter.update(json.loads(r["genres"] or "[]"))
    return [{"name": g, "count": n} for g, n in counter.most_common()]


def get_showcase(n: int = 12) -> dict:
    with db_conn() as c:
        ids = [
            r["movie_id"]
            for r in c.execute(
                "SELECT movie_id FROM movies WHERE vote_count >= 1000 AND vote_average >= 7 "
                "ORDER BY popularity DESC LIMIT 200"
            )
        ]
    pick = random.sample(ids, min(max(n, 3), len(ids)))
    return {"items": [card(get_movie_metadata(i, db_path=DB)) for i in pick]}


def suggest_entities(q: str, limit: int = 4) -> dict:
    key = fold(q.strip())
    out = {"movies": [], "director": [], "actor": [], "voice": [], "keyword": []}
    if len(key) < 2:
        return out
    out["movies"] = [
        {"movie_id": mid, "title": title, "release_year": year}
        for mid, title, folded_t, year in get_titles()
        if key in folded_t
    ][:5]
    idx = get_index()
    for kind in ("director", "actor", "voice", "keyword"):
        hits = [(k, e["name"], len(e["ids"])) for k, e in idx[kind].items() if key in k]
        hits.sort(key=lambda h: (not h[0].startswith(key), -h[2]))
        out[kind] = [{"name": n, "count": c} for _, n, c in hits[:limit]]
    return out


def query_movies(
    query: Optional[str] = None,
    genres: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_rating: Optional[float] = None,
    director: Optional[str] = None,
    actor: Optional[str] = None,
    voice: Optional[str] = None,
    keyword: Optional[str] = None,
    sort: str = "popularity",
    page: int = 1,
    page_size: int = 24,
) -> dict:
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
        qkey = fold(query.strip())
        allowed = {mid for mid, _t, folded_t, _y in get_titles() if qkey in folded_t}
        if sort == "popularity":
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
        where.append("vote_count >= 200")

    for kind, value in (("director", director), ("actor", actor), ("voice", voice), ("keyword", keyword)):
        if value:
            ids = get_index()[kind].get(fold(value), {}).get("ids", set())
            allowed = ids if allowed is None else allowed & ids

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    if allowed is not None and not allowed:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    with db_conn() as c:
        ids = [
            r["movie_id"]
            for r in c.execute(
                f"SELECT movie_id FROM movies WHERE {' AND '.join(where)} ORDER BY {order}",
                params + order_params,
            )
        ]
    if allowed is not None:
        ids = [i for i in ids if i in allowed]
    start = (page - 1) * page_size
    items = [card(get_movie_metadata(i, db_path=DB)) for i in ids[start : start + page_size]]
    return {"total": len(ids), "page": page, "page_size": page_size, "items": items}


def get_movie_detail(movie_id: int) -> dict:
    meta = get_movie_metadata(movie_id, db_path=DB)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy phim")
    c = card(meta)
    detail = {**c, "vote_count": meta.get("vote_count"), **load_extra().get(movie_id, {})}
    year = c["release_year"] or ""
    detail["trailer_url"] = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(f"{c['title']} {year} official trailer")
    )
    same = []
    if c["director"]:
        with db_conn() as conn_db:
            ids = [
                r["movie_id"]
                for r in conn_db.execute(
                    "SELECT movie_id FROM movies WHERE director = ? AND movie_id != ? "
                    "ORDER BY popularity DESC LIMIT 6",
                    (c["director"], movie_id),
                )
            ]
        same = [card(get_movie_metadata(i, db_path=DB)) for i in ids]
    detail["same_director"] = same
    detail["poster_url"] = poster_url(movie_id, "w500") or c["poster_url"]
    return detail


def get_movie_trailer(movie_id: int) -> dict:
    meta = get_movie_metadata(movie_id, db_path=DB)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy phim")
    year = (meta.get("release_date") or "")[:4]
    search_url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(f"{meta['title']} {year} official trailer")
    )
    with acc_conn() as c:
        row = c.execute("SELECT * FROM tmdb_cache WHERE movie_id = ?", (movie_id,)).fetchone()
    if row is None and tmdb_client.api_key():
        try:
            d = tmdb_client.fetch(movie_id)
        except Exception:
            return {"key": None, "reason": "unavailable", "search_url": search_url}
        with acc_conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO tmdb_cache VALUES (?, ?, ?, ?, ?)",
                (movie_id, d["poster_path"], d["trailer_key"], d["trailer_name"], time.time()),
            )
        row = d
    if row is None:
        return {"key": None, "reason": "no_key", "search_url": search_url}
    key = row["trailer_key"]
    return {
        "key": key,
        "name": row["trailer_name"],
        "reason": None if key else "not_found",
        "search_url": search_url,
    }


def get_similar_movies(movie_id: int, k: int = 8) -> dict:
    global _ALL_VECTORS
    vec = get_movie_vector(movie_id, db_path=DB)
    if vec is None:
        raise HTTPException(404, "Không tìm thấy phim")
    if _ALL_VECTORS is None:
        _ALL_VECTORS = get_all_vectors(db_path=DB)
    ids, matrix = _ALL_VECTORS
    scores = cosine_similarity_bulk(vec, matrix)
    out = []
    for i in np.argsort(scores)[::-1]:
        mid = int(ids[i])
        if mid == movie_id:
            continue
        c = card(get_movie_metadata(mid, db_path=DB))
        c["similarity"] = round(max(0.0, float(scores[i])) * 100)
        out.append(c)
        if len(out) >= min(max(k, 1), 24):
            break
    return {"items": out}

