"""
backend/repositories/movie_repository.py
----------------------------------------
Tang truy cap du lieu phim:
  - Cache poster TMDB & ban dich tom tat tieng Viet (overview_vi)
  - Doc thong tin mo rong tu CSV goc (runtime, budget, revenue, cast, crew, keywords)
  - Chi muc tim kiem & goi y tu dong (titles, director, actor, voice, keyword)
  - Chuyen doi metadata sang MovieCard DTO
"""

import ast
import glob
import json
import os
import re
import threading
import time
from typing import Optional

from backend.core.config import DB, ROOT
from backend.core.database import accounts_db, movies_db
from backend.core.security import fold_text
from feature_store import get_all_vectors, get_movie_metadata

_LOCK = threading.RLock()

_POSTERS: dict = {}
_POSTERS_AT = 0.0

_OVERVIEW_VI: dict = {}
_OVERVIEW_VI_AT = 0.0

_EXTRA: Optional[dict] = None
_KW_ALL: dict = {}      # movie_id -> toan bo tu khoa
_CAST20: dict = {}      # movie_id -> [(ten, la_long_tieng)]
_INDEX: Optional[dict] = None
_TITLES: Optional[list] = None
_ALL_VECTORS: Optional[tuple] = None


def get_poster_url(movie_id: int, size: str = "w342") -> Optional[str]:
    """Poster tu bang tmdb_cache. Lam moi moi 60 giay."""
    global _POSTERS, _POSTERS_AT
    if time.time() - _POSTERS_AT > 60:
        with accounts_db() as c:
            _POSTERS = {
                r["movie_id"]: r["poster_path"]
                for r in c.execute(
                    "SELECT movie_id, poster_path FROM tmdb_cache WHERE poster_path IS NOT NULL"
                )
            }
        _POSTERS_AT = time.time()
    p = _POSTERS.get(movie_id)
    return f"https://image.tmdb.org/t/p/{size}{p}" if p else None


def get_cached_overview_vi(movie_id: int) -> Optional[str]:
    """Tom tat tieng Viet da dich san (bang overview_vi). Lam moi moi 60 giay."""
    global _OVERVIEW_VI, _OVERVIEW_VI_AT
    if time.time() - _OVERVIEW_VI_AT > 60:
        with accounts_db() as c:
            _OVERVIEW_VI = {
                r["movie_id"]: r["text"]
                for r in c.execute("SELECT movie_id, text FROM overview_vi WHERE text IS NOT NULL")
            }
        _OVERVIEW_VI_AT = time.time()
    return _OVERVIEW_VI.get(movie_id)


def cache_overview_vi(movie_id: int, text: str, source: str) -> None:
    with accounts_db() as c:
        c.execute(
            "INSERT OR REPLACE INTO overview_vi VALUES (?, ?, ?, ?)",
            (movie_id, text, source, time.time()),
        )
    _OVERVIEW_VI[movie_id] = text


def to_movie_card(meta: dict) -> dict:
    """Rut gon metadata thanh du lieu hien thi tren card phim."""
    date = meta.get("release_date") or ""
    return {
        "movie_id": meta["movie_id"],
        "title": meta["title"],
        "overview": meta.get("overview") or "",
        "overview_vi": get_cached_overview_vi(meta["movie_id"]),
        "genres": meta.get("genres", []),
        "director": meta.get("director"),
        "cast": meta.get("cast", []),
        "vote_average": meta.get("vote_average"),
        "popularity": meta.get("popularity"),
        "release_year": int(date[:4]) if date[:4].isdigit() else None,
        "poster_url": get_poster_url(meta["movie_id"]),
    }


def _find_csv(kind: str) -> Optional[str]:
    env = os.environ.get(f"TMDB_{kind.upper()}_CSV")
    if env and os.path.exists(env):
        return env
    for d in (
        ROOT,
        os.path.join(ROOT, "data"),
        os.path.join(ROOT, "data_module"),
        os.path.join(ROOT, "data_module", "data"),
        os.path.join(ROOT, "data_module", "src"),
    ):
        hits = sorted(glob.glob(os.path.join(d, f"tmdb_5000_{kind}*.csv")))
        if hits:
            return hits[0]
    return None


def _parse_list(value) -> list:
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


def _names(value, limit=None) -> list[str]:
    out = [d["name"] for d in _parse_list(value) if d.get("name")]
    return out[:limit] if limit else out


def _clean(x):
    return None if x is None or x != x or x == "" else x


def _build_extra() -> dict:
    extra: dict = {}
    movies_csv, credits_csv = _find_csv("movies"), _find_csv("credits")
    if not movies_csv:
        return extra
    import pandas as pd

    for r in pd.read_csv(movies_csv).to_dict("records"):
        runtime, budget, revenue = (
            _clean(r.get("runtime")),
            _clean(r.get("budget")),
            _clean(r.get("revenue")),
        )
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
            "cast_members": [],
            "voice_cast": [],
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
                people.append(
                    {
                        "name": d.get("name"),
                        "character": re.sub(r"\s*\(.*?\)", "", raw).strip(),
                        "voice": "(voice" in raw.lower(),
                    }
                )
            _CAST20[int(r["movie_id"])] = [(p["name"], p["voice"]) for p in people if p["name"]]
            entry["cast_members"] = [p for p in people if not p["voice"]][:12]
            entry["voice_cast"] = [p for p in people if p["voice"]][:12]
            crew = _parse_list(r.get("crew"))
            entry["crew"] = {
                "writers": list(
                    dict.fromkeys(
                        d["name"]
                        for d in crew
                        if d.get("job") in ("Screenplay", "Writer", "Story", "Novel")
                    )
                )[:3],
                "composers": list(
                    dict.fromkeys(
                        d["name"] for d in crew if d.get("job") == "Original Music Composer"
                    )
                )[:2],
            }
    return extra


def load_extra_metadata() -> dict:
    """Doc CSV 1 lan, giu trong bo nho."""
    global _EXTRA
    with _LOCK:
        if _EXTRA is None:
            _EXTRA = _build_extra()
        return _EXTRA


def _build_index() -> dict:
    """Chi muc ten -> tap movie_id cho loc theo dao dien / dien vien / long tieng / tu khoa."""
    load_extra_metadata()
    idx = {k: {} for k in ("director", "actor", "voice", "keyword")}

    def add(kind, name, mid):
        e = idx[kind].setdefault(fold_text(name), {"name": name, "ids": set()})
        e["ids"].add(mid)

    with movies_db() as c:
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


def get_search_index() -> dict:
    global _INDEX
    with _LOCK:
        if _INDEX is None:
            _INDEX = _build_index()
        return _INDEX


def get_titles_index() -> list:
    """[(movie_id, title, title_da_bo_dau, nam)] xep theo do pho bien giam dan."""
    global _TITLES
    with _LOCK:
        if _TITLES is None:
            with movies_db() as c:
                rows = c.execute(
                    "SELECT movie_id, title, release_date FROM movies ORDER BY popularity DESC"
                ).fetchall()
            _TITLES = [
                (
                    r["movie_id"],
                    r["title"],
                    fold_text(r["title"]),
                    int(r["release_date"][:4])
                    if (r["release_date"] or "")[:4].isdigit()
                    else None,
                )
                for r in rows
            ]
        return _TITLES


def get_cached_all_vectors() -> tuple:
    global _ALL_VECTORS
    if _ALL_VECTORS is None:
        _ALL_VECTORS = get_all_vectors(db_path=DB)
    return _ALL_VECTORS

