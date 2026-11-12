"""
sync_tmdb.py
------------
Pipeline tu dong cap nhat & dong bo phim moi tu TMDB REST API vao `movies.db`
(va cap nhat poster/trailer/overview_vi vao `accounts.db` neu co).

Tinh nang chinh:
1. Giu CO DINH 100% khong gian Vector 324 chieu:
   - [0:20]    20 The loai (Multi-hot)
   - [20:71]   50 Dao dien pho bien + 1 cot Other/Unknown (One-hot)
   - [71:271]  200 Dien vien pho bien (Multi-hot)
   - [271:321] 50 chieu TF-IDF + SVD nen tu Overview tieng Anh (chieu qua ma tran V_T)
   - [321:324] 3 tin hieu so (vote_average, popularity, release_year) chuan hoa [0, 1]
   -> Khong can fit lai toan bo DB, khong lam lech vector UserProfile cua nguoi dung!
2. Ho tro 3 che do cap nhat:
   - `--mode recent`: Cap nhat phim dang chieu (now_playing), pho bien (popular), xu huong (trending)
   - `--mode years`: Quet cac phim noi bat theo tung nam (VD: `--start-year 2017 --end-year 2026 --per-year 20`)
   - `--mode ids`: Dong bo danh sach TMDB movie_id cu the (VD: `--ids 299534,299536,157336`)
3. Tu dong lay:
   - Metadata day du (overview, genres, keywords, cast_details, crew_details, runtime, budget, revenue...)
   - Ban dich tom tat tieng Viet (`overview_vi`) chinh thuc tu TMDB (`language=vi-VN`)
   - Poster & YouTube Trailer key luu vao `accounts.db` (bang `tmdb_cache` va `overview_vi`)

Cach chay:
    python data_module/src/sync_tmdb.py --mode years --start-year 2017 --end-year 2026 --per-year 15
    python data_module/src/sync_tmdb.py --mode recent --limit 40
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any, Optional
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_THIS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _THIS_DIR.parent.parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from feature_store import DEFAULT_DB_PATH, create_schema, get_all_vectors

DEFAULT_ACCOUNTS_DB = str(_ROOT_DIR / "accounts.db")
TMDB_API_BASE = "https://api.themoviedb.org/3"


def load_env_file(env_path: Optional[str] = None) -> None:
    """Tu dong doc TMDB_API_KEY tu file .env o thu muc goc."""
    path = Path(env_path) if env_path else (_ROOT_DIR / ".env")
    placeholders = {"your_gemini_api_key_here", "your_tmdb_api_key_here", "your_openai_api_key_here"}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[7:].strip()
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v and v not in placeholders and not os.environ.get(k):
                        os.environ[k] = v
        except Exception:
            pass
    if not os.environ.get("TMDB_API_KEY"):
        os.environ["TMDB_API_KEY"] = "fcf8e04d0d4d12b9eac083efb9134563"


load_env_file()


class IncrementalVectorizer324D:
    """Khoi phuc chinh xac he truc toa do 324 chieu tu `movies.db` hien tai
    va cho phep bien doi (transform) bat ky phim moi nao tu TMDB API sang vector 324 chieu."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        movie_ids, matrix = get_all_vectors(db_path)
        self.existing_ids: set[int] = {int(m) for m in movie_ids}
        self.matrix = matrix

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT movie_id, overview, genres, director, "cast", vote_average, popularity, release_date '
            "FROM movies ORDER BY movie_id"
        ).fetchall()
        conn.close()

        # 1. Genres [0:20] (sorted alphabetically)
        all_genres: set[str] = set()
        overviews: list[str] = []
        votes: list[float] = []
        pops: list[float] = []
        years: list[int] = []

        for r in rows:
            for g in json.loads(r["genres"] or "[]"):
                all_genres.add(g)
            overviews.append(r["overview"] or "")
            votes.append(float(r["vote_average"] or 0.0))
            pops.append(float(r["popularity"] or 0.0))
            rel = r["release_date"] or ""
            if len(rel) >= 4 and rel[:4].isdigit():
                years.append(int(rel[:4]))

        # Chi giu 20 genre goc cua khong gian 324 chieu
        self.genre_labels: list[str] = sorted(all_genres)[:20]
        self.genre_to_col: dict[str, int] = {g: i for i, g in enumerate(self.genre_labels)}

        # 2. Directors [20:71] (50 top directors + col 70 = Other/Unknown)
        self.director_to_col: dict[str, int] = {}
        for col in range(20, 70):
            active = np.where(matrix[:, col] == 1.0)[0]
            dirs = {rows[i]["director"] for i in active if i < len(rows) and rows[i]["director"]}
            if len(dirs) == 1:
                self.director_to_col[next(iter(dirs))] = col

        # 3. Cast [71:271] (200 top actors)
        self.cast_to_col: dict[str, int] = {}
        for col in range(71, 271):
            active = np.where(matrix[:, col] == 1.0)[0]
            common = None
            for i in active:
                if i >= len(rows):
                    continue
                actors = set(json.loads(rows[i]["cast"] or "[]"))
                common = actors if common is None else (common & actors)
            if common and len(common) == 1:
                self.cast_to_col[next(iter(common))] = col

        # 4. Overview TF-IDF -> 50-D SVD projection [271:321]
        self.tfidf = TfidfVectorizer(max_features=5000, stop_words="english")
        X_tfidf = self.tfidf.fit_transform(overviews)
        Y_svd = matrix[:, 271:321]
        col_norms_sq = np.sum(Y_svd ** 2, axis=0, keepdims=True)
        col_norms_sq = np.where(col_norms_sq == 0, 1.0, col_norms_sq)
        self.svd_projection: np.ndarray = np.asarray(
            (X_tfidf.T @ Y_svd) / col_norms_sq, dtype=np.float32
        )

        # 5. Numeric bounds [321:324] (vote_average, popularity, release_year)
        self.min_vote = min(votes) if votes else 0.0
        self.max_vote = max(votes) if votes else 10.0
        self.min_pop = min(pops) if pops else 0.0
        self.max_pop = max(pops) if pops else 875.58
        self.min_year = min(years) if years else 1916
        self.max_year = max(max(years) if years else 2026, 2026)

    def transform_movie(self, movie: dict[str, Any]) -> np.ndarray:
        """Bien doi metadata cua 1 phim moi thanh vector 324 chieu (float32)."""
        vec = np.zeros(324, dtype=np.float32)

        # 1. Genres [0:20]
        for g in movie.get("genres", []):
            col = self.genre_to_col.get(g)
            if col is not None:
                vec[col] = 1.0

        # 2. Director [20:71]
        director = movie.get("director")
        d_col = self.director_to_col.get(director, 70) if director else 70
        vec[d_col] = 1.0

        # 3. Cast [71:271]
        for actor in movie.get("cast", []):
            a_col = self.cast_to_col.get(actor)
            if a_col is not None:
                vec[a_col] = 1.0

        # 4. Overview SVD [271:321]
        overview = (movie.get("overview") or "").strip()
        if overview:
            tfidf_vec = self.tfidf.transform([overview])
            svd_vec = np.asarray(tfidf_vec @ self.svd_projection, dtype=np.float32).reshape(50)
            vec[271:321] = svd_vec

        # 5. Numeric [321:324]: vote_average, popularity, release_year
        vote = float(movie.get("vote_average") or 0.0)
        pop = float(movie.get("popularity") or 0.0)
        rel_date = movie.get("release_date") or ""
        year = int(rel_date[:4]) if len(rel_date) >= 4 and rel_date[:4].isdigit() else 2020

        vec[321] = float(np.clip((vote - self.min_vote) / max(self.max_vote - self.min_vote, 1e-6), 0.0, 1.0))
        vec[322] = float(np.clip((pop - self.min_pop) / max(self.max_pop - self.min_pop, 1e-6), 0.0, 1.0))
        vec[323] = float(np.clip((year - self.min_year) / max(self.max_year - self.min_year, 1e-6), 0.0, 1.0))

        return vec


def _tmdb_get(endpoint: str, api_key: str, params: Optional[dict[str, Any]] = None, timeout: float = 10.0) -> Optional[dict[str, Any]]:
    query = {"api_key": api_key}
    if params:
        query.update(params)
    url = f"{TMDB_API_BASE}{endpoint}?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ATI-Movie-Sync/1.0"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(1.5)
                continue
            return None
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
                continue
            return None
    return None


def search_tmdb_movie_id_by_title(title: str, api_key: str, timeout: float = 3.5) -> Optional[int]:
    """Tim movie_id tren TMDB theo ten phim tieng Anh hoac tieng Viet."""
    q = (title or "").strip()
    if not q:
        return None
    data = _tmdb_get("/search/movie", api_key, {"query": q, "include_adult": "false", "page": 1}, timeout=timeout)
    if not data or not data.get("results"):
        return None
    # Uu tien ket qua co vote_count >= 15 va vote_average > 0
    results = [r for r in data["results"] if (r.get("vote_count") or 0) >= 15 and (r.get("vote_average") or 0) > 0]
    if not results:
        return None
    q_low = q.lower()
    for r in results:
        if (r.get("title") or "").strip().lower() == q_low or (r.get("original_title") or "").strip().lower() == q_low:
            return int(r["id"])
    return int(results[0]["id"])


def discover_tmdb_movie_ids(
    api_key: str,
    mode: str = "years",
    start_year: int = 2017,
    end_year: int = 2026,
    per_year: int = 15,
    recent_limit: int = 40,
    explicit_ids: Optional[list[int]] = None,
) -> list[int]:
    """Thu thap danh sach TMDB movie_id can dong bo theo che do."""
    found_ids: list[int] = []
    seen: set[int] = set()

    def _add(mid: int) -> None:
        if mid and mid not in seen:
            seen.add(mid)
            found_ids.append(mid)

    if mode == "ids" and explicit_ids:
        for mid in explicit_ids:
            _add(int(mid))
        return found_ids

    if mode in ("recent", "all"):
        endpoints = [
            ("/trending/movie/week", {}),
            ("/movie/now_playing", {"region": "US"}),
            ("/movie/popular", {}),
            ("/movie/top_rated", {}),
        ]
        for ep, extra_params in endpoints:
            for page in (1, 2):
                data = _tmdb_get(ep, api_key, {**extra_params, "page": page})
                if not data:
                    continue
                for item in data.get("results", []):
                    if item.get("id") and (item.get("vote_count") or 0) >= 20:
                        _add(int(item["id"]))
                        if mode == "recent" and len(found_ids) >= recent_limit:
                            return found_ids

    if mode in ("years", "all"):
        today_str = time.strftime("%Y-%m-%d")
        for year in range(start_year, end_year + 1):
            added_for_year = 0
            pages_needed = max(1, (per_year + 19) // 20)
            # Uu tien phim co nhieu luot binh chon (vote_count.desc) va DA PHAT HANH (vote_average > 0)
            for page in range(1, pages_needed + 2):
                data = _tmdb_get(
                    "/discover/movie",
                    api_key,
                    {
                        "primary_release_year": year,
                        "primary_release_date.lte": today_str,
                        "sort_by": "vote_count.desc",
                        "vote_count.gte": 100 if year < 2026 else 30,
                        "vote_average.gte": 4.0,
                        "include_adult": "false",
                        "include_video": "false",
                        "page": page,
                    },
                )
                if not data or not data.get("results"):
                    break
                for item in data.get("results", []):
                    mid = item.get("id")
                    if mid and mid not in seen:
                        _add(int(mid))
                        added_for_year += 1
                        if added_for_year >= per_year:
                            break
                if added_for_year >= per_year:
                    break

    return found_ids


# Anh xa ten the loai TMDB moi ("Science Fiction", "TV Movie"...) khop chuan movies.db
_TMDB_GENRE_NORM = {
    "Sci-Fi": "Science Fiction",
}


def fetch_full_movie_from_tmdb(movie_id: int, api_key: str) -> Optional[dict[str, Any]]:
    """Lay toan bo chi tiet phim (EN + VI + Credits + Keywords + Videos) tu TMDB API."""
    en_data = _tmdb_get(
        f"/movie/{movie_id}",
        api_key,
        {"language": "en-US", "append_to_response": "credits,keywords,videos"},
    )
    if not en_data or not en_data.get("title"):
        return None

    overview_en = (en_data.get("overview") or "").strip()
    if len(overview_en) < 15:
        return None
    if float(en_data.get("vote_average") or 0.0) <= 0.0 or int(en_data.get("vote_count") or 0) < 10:
        return None

    # Lay ban dich tieng Viet chinh thuc tu TMDB
    vi_data = _tmdb_get(f"/movie/{movie_id}", api_key, {"language": "vi-VN"})
    overview_vi = None
    if vi_data:
        ov_vi_raw = (vi_data.get("overview") or "").strip()
        if ov_vi_raw and ov_vi_raw != overview_en:
            overview_vi = ov_vi_raw

    # Genres
    genres: list[str] = []
    for g in en_data.get("genres") or []:
        name = (g.get("name") or "").strip()
        if name:
            name = _TMDB_GENRE_NORM.get(name, name)
            if name not in genres:
                genres.append(name)
    if not genres:
        return None

    # Keywords
    kw_block = en_data.get("keywords") or {}
    kw_items = kw_block.get("keywords") or kw_block.get("results") or []
    keywords = [k["name"].strip() for k in kw_items if isinstance(k, dict) and k.get("name")]

    # Credits: Director, Cast (top 5 + top 20 details), Crew (writers, composers)
    credits = en_data.get("credits") or {}
    raw_cast = sorted(credits.get("cast") or [], key=lambda c: c.get("order", 999))
    cast_top5 = [c["name"].strip() for c in raw_cast[:5] if c.get("name")]
    cast_details: list[dict[str, Any]] = []
    for c in raw_cast[:20]:
        if not c.get("name"):
            continue
        char_raw = c.get("character") or ""
        cast_details.append(
            {
                "name": c["name"].strip(),
                "character": re.sub(r"\s*\(.*?\)", "", char_raw).strip(),
                "voice": "(voice" in char_raw.lower(),
            }
        )

    raw_crew = credits.get("crew") or []
    director = None
    writers: list[str] = []
    composers: list[str] = []
    for member in raw_crew:
        name = (member.get("name") or "").strip()
        job = member.get("job") or ""
        if not name:
            continue
        if job == "Director" and director is None:
            director = name
        if job in ("Screenplay", "Writer", "Story", "Novel") and name not in writers:
            writers.append(name)
        if job in ("Original Music Composer", "Music") and name not in composers:
            composers.append(name)

    # Videos -> YouTube Trailer
    videos = (en_data.get("videos") or {}).get("results") or []
    trailer_key = None
    trailer_name = None
    for v in videos:
        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser") and v.get("key"):
            trailer_key = v["key"]
            trailer_name = v.get("name") or "Official Trailer"
            if v.get("type") == "Trailer" and v.get("official"):
                break

    companies = [c["name"].strip() for c in (en_data.get("production_companies") or []) if c.get("name")]
    countries = [c["name"].strip() for c in (en_data.get("production_countries") or []) if c.get("name")]
    languages = [
        (l.get("english_name") or l.get("name") or "").strip()
        for l in (en_data.get("spoken_languages") or [])
        if l.get("english_name") or l.get("name")
    ]

    return {
        "movie_id": int(en_data["id"]),
        "title": en_data["title"].strip(),
        "overview": overview_en,
        "overview_vi": overview_vi,
        "tagline": (en_data.get("tagline") or "").strip() or None,
        "genres": genres,
        "keywords": keywords,
        "director": director,
        "cast": cast_top5,
        "cast_details": cast_details,
        "crew_details": {"writers": writers[:3], "composers": composers[:2]},
        "runtime": int(en_data["runtime"]) if en_data.get("runtime") else None,
        "budget": int(en_data.get("budget") or 0),
        "revenue": int(en_data.get("revenue") or 0),
        "companies": companies,
        "countries": countries,
        "languages": languages,
        "homepage": (en_data.get("homepage") or "").strip() or None,
        "vote_average": float(en_data.get("vote_average") or 0.0),
        "vote_count": int(en_data.get("vote_count") or 0),
        "popularity": float(en_data.get("popularity") or 0.0),
        "release_date": (en_data.get("release_date") or "").strip() or None,
        "poster_path": en_data.get("poster_path"),
        "trailer_key": trailer_key,
        "trailer_name": trailer_name,
    }


def sync_movies_from_tmdb(
    db_path: str = DEFAULT_DB_PATH,
    accounts_db_path: str = DEFAULT_ACCOUNTS_DB,
    mode: str = "years",
    start_year: int = 2017,
    end_year: int = 2026,
    per_year: int = 15,
    recent_limit: int = 40,
    explicit_ids: Optional[list[int]] = None,
    force_update: bool = False,
    max_workers: int = 6,
) -> dict[str, Any]:
    """Ham dieu phoi chinh: Tim phim tren TMDB -> Tai chi tiet -> Vector hoa 324D -> Luu vao movies.db & accounts.db."""
    load_env_file()
    api_key = (os.environ.get("TMDB_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "Chưa tìm thấy TMDB_API_KEY trong biến môi trường hoặc file .env! "
            "Vui lòng điền TMDB_API_KEY vào file .env ở thư mục gốc."
        )

    t0 = time.time()
    create_schema(db_path)
    vectorizer = IncrementalVectorizer324D(db_path)

    candidate_ids = discover_tmdb_movie_ids(
        api_key=api_key,
        mode=mode,
        start_year=start_year,
        end_year=end_year,
        per_year=per_year,
        recent_limit=recent_limit,
        explicit_ids=explicit_ids,
    )

    if not force_update:
        target_ids = [mid for mid in candidate_ids if mid not in vectorizer.existing_ids]
    else:
        target_ids = candidate_ids

    if not target_ids:
        return {
            "status": "up_to_date",
            "discovered": len(candidate_ids),
            "inserted": 0,
            "total_movies": len(vectorizer.existing_ids),
            "elapsed_sec": round(time.time() - t0, 2),
            "sample_titles": [],
        }

    fetched_movies: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_full_movie_from_tmdb, mid, api_key): mid for mid in target_ids}
        for fut in as_completed(futures):
            try:
                item = fut.result()
                if item is not None:
                    fetched_movies.append(item)
            except Exception:
                pass

    if not fetched_movies:
        return {
            "status": "no_valid_movies",
            "discovered": len(candidate_ids),
            "inserted": 0,
            "total_movies": len(vectorizer.existing_ids),
            "elapsed_sec": round(time.time() - t0, 2),
            "sample_titles": [],
        }

    # Sap xep theo movie_id tang dan
    fetched_movies.sort(key=lambda m: m["movie_id"])

    movie_rows = []
    vector_rows = []
    media_rows = []
    overview_vi_rows = []
    now_ts = time.time()

    for m in fetched_movies:
        mid = m["movie_id"]
        vec = vectorizer.transform_movie(m)
        movie_rows.append(
            (
                mid,
                m["title"],
                m["overview"],
                m["overview_vi"],
                m["tagline"],
                json.dumps(m["genres"], ensure_ascii=False),
                json.dumps(m["keywords"], ensure_ascii=False),
                m["director"],
                json.dumps(m["cast"], ensure_ascii=False),
                json.dumps(m["cast_details"], ensure_ascii=False),
                json.dumps(m["crew_details"], ensure_ascii=False),
                m["runtime"],
                m["budget"],
                m["revenue"],
                json.dumps(m["companies"], ensure_ascii=False),
                json.dumps(m["countries"], ensure_ascii=False),
                json.dumps(m["languages"], ensure_ascii=False),
                m["homepage"],
                m["vote_average"],
                m["vote_count"],
                m["popularity"],
                m["release_date"],
            )
        )
        vector_rows.append((mid, vec.astype(np.float32).tobytes(), int(vec.shape[0])))

        if m.get("poster_path") or m.get("trailer_key"):
            media_rows.append((mid, m.get("poster_path"), m.get("trailer_key"), m.get("trailer_name"), now_ts))
        if m.get("overview_vi"):
            overview_vi_rows.append((mid, m["overview_vi"], "tmdb_vi", now_ts))

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executemany(
        """INSERT OR REPLACE INTO movies
           (movie_id, title, overview, overview_vi, tagline, genres, keywords,
            director, cast, cast_details, crew_details, runtime, budget, revenue,
            companies, countries, languages, homepage,
            vote_average, vote_count, popularity, release_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        movie_rows,
    )
    cur.executemany(
        "INSERT OR REPLACE INTO movie_feature_vectors (movie_id, vector, dims) VALUES (?, ?, ?)",
        vector_rows,
    )
    conn.commit()
    total_after = cur.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    conn.close()

    # Cap nhat luon poster/trailer & overview_vi vao accounts.db de giao dien hien thi ngay lap tuc
    if os.path.exists(accounts_db_path):
        try:
            acc_conn = sqlite3.connect(accounts_db_path)
            if media_rows:
                acc_conn.executemany(
                    "INSERT OR REPLACE INTO tmdb_cache (movie_id, poster_path, trailer_key, trailer_name, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    media_rows,
                )
            if overview_vi_rows:
                acc_conn.executemany(
                    "INSERT OR REPLACE INTO overview_vi (movie_id, text, source, fetched_at) VALUES (?, ?, ?, ?)",
                    overview_vi_rows,
                )
            acc_conn.commit()
            acc_conn.close()
        except Exception:
            pass

    return {
        "status": "ok",
        "discovered": len(candidate_ids),
        "inserted": len(fetched_movies),
        "with_overview_vi": len(overview_vi_rows),
        "with_poster": sum(1 for m in fetched_movies if m.get("poster_path")),
        "total_movies": int(total_after),
        "elapsed_sec": round(time.time() - t0, 2),
        "sample_titles": [
            f"{m['title']} ({(m.get('release_date') or '')[:4]})" for m in fetched_movies[:15]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Đồng bộ phim mới từ TMDB API vào movies.db (giữ nguyên vector 324 chiều).")
    parser.add_argument(
        "--mode",
        choices=["years", "recent", "ids", "all"],
        default="years",
        help="Chế độ đồng bộ: 'years' (theo khoảng năm), 'recent' (phim mới/đang hot), 'ids' (theo ID cụ thể), 'all' (cả hai)",
    )
    parser.add_argument("--start-year", type=int, default=2017, help="Năm bắt đầu (cho --mode years)")
    parser.add_argument("--end-year", type=int, default=2026, help="Năm kết thúc (cho --mode years)")
    parser.add_argument("--per-year", type=int, default=15, help="Số phim nổi bật nhất cần lấy mỗi năm")
    parser.add_argument("--limit", type=int, default=40, help="Số phim tối đa (cho --mode recent)")
    parser.add_argument("--ids", type=str, default="", help="Danh sách TMDB IDs cách nhau dấu phẩy (VD: 299534,157336)")
    parser.add_argument("--force", action="store_true", help="Ghi đè kể cả các phim đã tồn tại trong movies.db")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Đường dẫn tới movies.db")
    args = parser.parse_args()

    explicit_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip().isdigit()] if args.ids else None

    print(f"[TMDB Sync] Đang đồng bộ phim mới từ TMDB API (mode={args.mode})...")
    result = sync_movies_from_tmdb(
        db_path=args.db,
        mode=args.mode,
        start_year=args.start_year,
        end_year=args.end_year,
        per_year=args.per_year,
        recent_limit=args.limit,
        explicit_ids=explicit_ids,
        force_update=args.force,
    )
    print(f"[TMDB Sync] Hoàn tất trong {result['elapsed_sec']}s!")
    print(f"  - Số phim phát hiện từ TMDB : {result['discovered']}")
    print(f"  - Số phim mới đã thêm vào DB: {result['inserted']}")
    print(f"  - Có sẵn tóm tắt tiếng Việt : {result.get('with_overview_vi', 0)}")
    print(f"  - Có sẵn Poster TMDB        : {result.get('with_poster', 0)}")
    print(f"  - Tổng số phim trong DB     : {result['total_movies']}")
    if result.get("sample_titles"):
        print(f"  - Một số phim vừa thêm      : {', '.join(result['sample_titles'][:10])}")


if __name__ == "__main__":
    main()
