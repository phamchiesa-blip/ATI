"""
tmdb_client.py
--------------
Goi TMDB API (can key mien phi) de lay poster va trailer. Chi dung thu vien chuan.
Dat key bang bien moi truong TMDB_API_KEY (ho tro ca API Key v3 lan Read Access Token v4).
"""

import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://api.themoviedb.org/3"


def api_key() -> str:
    return os.environ.get("TMDB_API_KEY", "").strip()


def _request(movie_id: int, key: str) -> dict:
    url = f"{BASE}/movie/{movie_id}?append_to_response=videos"
    headers = {"Accept": "application/json"}
    if len(key) > 40:                       # Read Access Token (JWT)
        headers["Authorization"] = f"Bearer {key}"
    else:                                   # API Key v3
        url += f"&api_key={key}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as r:
        return json.load(r)


def pick_trailer(videos: list) -> "tuple[str | None, str | None]":
    """Chon video tot nhat: YouTube, uu tien Trailer chinh thuc, tieng Anh."""
    best, best_rank = None, None
    for v in videos or []:
        if v.get("site") != "YouTube" or v.get("type") not in ("Trailer", "Teaser") or not v.get("key"):
            continue
        rank = (v.get("type") != "Trailer", not v.get("official"), v.get("iso_639_1") != "en")
        if best_rank is None or rank < best_rank:
            best, best_rank = v, rank
    return (best["key"], best.get("name")) if best else (None, None)


def fetch(movie_id: int, key: "str | None" = None, retries: int = 3) -> dict:
    """Tra ve {poster_path, trailer_key, trailer_name}. Phim khong co tren TMDB -> tat ca None."""
    key = key or api_key()
    if not key:
        raise RuntimeError("Chua dat TMDB_API_KEY")
    for attempt in range(retries):
        try:
            data = _request(movie_id, key)
            tkey, tname = pick_trailer((data.get("videos") or {}).get("results"))
            return {"poster_path": data.get("poster_path"), "trailer_key": tkey, "trailer_name": tname}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"poster_path": None, "trailer_key": None, "trailer_name": None}
            if e.code == 429 and attempt < retries - 1:
                time.sleep(float(e.headers.get("Retry-After", "2")))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError("TMDB khong phan hoi")