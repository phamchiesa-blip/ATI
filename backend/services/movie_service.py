"""
backend/services/movie_service.py
---------------------------------
Use cases cho kham pha danh muc phim, tim kiem goi y tu dong, chi tiet phim, trailer,
ban dich tom tat tieng Viet va phim tuong tu.
"""

import json
import random
import time
from collections import Counter
from typing import Optional
from urllib.parse import quote_plus

import numpy as np
from fastapi import HTTPException

from backend.core.config import DB
from backend.core.database import accounts_db, movies_db
from backend.core.security import fold_text
from backend.integrations import tmdb_client
from backend.repositories.movie_repository import (
    cache_overview_vi,
    get_cached_all_vectors,
    get_poster_url,
    get_search_index,
    get_titles_index,
    load_extra_metadata,
    to_movie_card,
)
from feature_store import get_movie_metadata, get_movie_vector
from similarity import cosine_similarity_bulk


def list_all_genres() -> list[dict]:
    with movies_db() as c:
        rows = c.execute("SELECT genres FROM movies").fetchall()
    counter = Counter()
    for r in rows:
        counter.update(json.loads(r["genres"] or "[]"))
    return [{"name": g, "count": n} for g, n in counter.most_common()]


def get_showcase_movies(n: int = 12) -> dict:
    with movies_db() as c:
        ids = [
            r["movie_id"]
            for r in c.execute(
                "SELECT movie_id FROM movies WHERE vote_count >= 1000 AND vote_average >= 7 "
                "ORDER BY popularity DESC LIMIT 200"
            )
        ]
    pick = random.sample(ids, min(max(n, 3), len(ids)))
    return {"items": [to_movie_card(get_movie_metadata(i, db_path=DB)) for i in pick]}


def suggest_entities(q: str, limit: int = 4) -> dict:
    key = fold_text(q.strip())
    out = {"movies": [], "director": [], "actor": [], "voice": [], "keyword": []}
    if len(key) < 2:
        return out
    out["movies"] = [
        {"movie_id": mid, "title": title, "release_year": year}
        for mid, title, folded, year in get_titles_index()
        if key in folded
    ][:5]
    idx = get_search_index()
    for kind in ("director", "actor", "voice", "keyword"):
        hits = [(k, e["name"], len(e["ids"])) for k, e in idx[kind].items() if key in k]
        hits.sort(key=lambda h: (not h[0].startswith(key), -h[2]))
        out[kind] = [{"name": n, "count": c} for _, n, c in hits[:limit]]
    return out


def search_movies(
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
        qkey = fold_text(query.strip())
        allowed = {mid for mid, _t, folded, _y in get_titles_index() if qkey in folded}
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

    for kind, value in (
        ("director", director),
        ("actor", actor),
        ("voice", voice),
        ("keyword", keyword),
    ):
        if value:
            ids = get_search_index()[kind].get(fold_text(value), {}).get("ids", set())
            allowed = ids if allowed is None else allowed & ids
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    if allowed is not None and not allowed:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    with movies_db() as c:
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
    items = [to_movie_card(get_movie_metadata(i, db_path=DB)) for i in ids[start : start + page_size]]
    return {"total": len(ids), "page": page, "page_size": page_size, "items": items}


def get_movie_detail(movie_id: int) -> dict:
    meta = get_movie_metadata(movie_id, db_path=DB)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy phim")
    card = to_movie_card(meta)
    detail = {**card, "vote_count": meta.get("vote_count"), **load_extra_metadata().get(movie_id, {})}
    year = card["release_year"] or ""
    detail["trailer_url"] = "https://www.youtube.com/results?search_query=" + quote_plus(
        f"{card['title']} {year} official trailer"
    )
    same = []
    if card["director"]:
        with movies_db() as c:
            ids = [
                r["movie_id"]
                for r in c.execute(
                    "SELECT movie_id FROM movies WHERE director = ? AND movie_id != ? "
                    "ORDER BY popularity DESC LIMIT 6",
                    (card["director"], movie_id),
                )
            ]
        same = [to_movie_card(get_movie_metadata(i, db_path=DB)) for i in ids]
    detail["same_director"] = same
    detail["poster_url"] = get_poster_url(movie_id, "w500") or card["poster_url"]
    return detail


def get_movie_trailer(movie_id: int) -> dict:
    meta = get_movie_metadata(movie_id, db_path=DB)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy phim")
    year = (meta.get("release_date") or "")[:4]
    search_url = "https://www.youtube.com/results?search_query=" + quote_plus(
        f"{meta['title']} {year} official trailer"
    )
    with accounts_db() as c:
        row = c.execute("SELECT * FROM tmdb_cache WHERE movie_id = ?", (movie_id,)).fetchone()
    if row is None and tmdb_client.api_key():
        try:
            d = tmdb_client.fetch(movie_id)
        except Exception:
            return {"key": None, "reason": "unavailable", "search_url": search_url}
        with accounts_db() as c:
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


def get_movie_overview_translated(movie_id: int, lang: str = "vi") -> dict:
    meta = get_movie_metadata(movie_id, db_path=DB)
    if meta is None:
        raise HTTPException(404, "Không tìm thấy phim")
    original = meta.get("overview") or ""
    if lang != "vi" or not original:
        return {"overview": original, "source": "original"}
    with accounts_db() as c:
        row = c.execute(
            "SELECT text, source FROM overview_vi WHERE movie_id = ?", (movie_id,)
        ).fetchone()
    if row and row["text"]:
        return {"overview": row["text"], "source": row["source"]}
    text, source = None, None
    try:
        text = tmdb_client.fetch_overview_vi(movie_id)
        source = "tmdb" if text else None
    except Exception:
        pass
    if not text:
        try:
            text = tmdb_client.machine_translate_vi(original)
            source = "machine" if text else None
        except Exception:
            pass
    if not text:
        return {"overview": original, "source": "original"}
    cache_overview_vi(movie_id, text, source)
    return {"overview": text, "source": source}


def get_similar_movies(movie_id: int, k: int = 8) -> dict:
    vec = get_movie_vector(movie_id, db_path=DB)
    if vec is None:
        raise HTTPException(404, "Không tìm thấy phim")
    ids, matrix = get_cached_all_vectors()
    scores = cosine_similarity_bulk(vec, matrix)
    out = []
    for i in np.argsort(scores)[::-1]:
        mid = int(ids[i])
        if mid == movie_id:
            continue
        card = to_movie_card(get_movie_metadata(mid, db_path=DB))
        card["similarity"] = round(max(0.0, float(scores[i])) * 100)
        out.append(card)
        if len(out) >= min(max(k, 1), 24):
            break
    return {"items": out}

