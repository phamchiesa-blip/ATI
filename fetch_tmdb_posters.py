"""
fetch_tmdb_posters.py
---------------------
Tai poster + trailer cho toan bo phim trong movies.db tu TMDB, luu vao accounts.db
(bang tmdb_cache). Chay 1 lan (~5 phut cho 4772 phim), co the dung giua chung va chay lai:
phim da co se bo qua.

    # PowerShell:  $env:TMDB_API_KEY="khoa_cua_ban"
    python fetch_tmdb_posters.py
Xong thi khoi dong lai API (hoac doi toi 1 phut) de poster hien len.
"""

import argparse
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import tmdb_client

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("MOVIES_DB", os.path.join(ROOT, "data_module", "src", "movies.db"))
ACCOUNTS_DB = os.environ.get("ACCOUNTS_DB", os.path.join(ROOT, "accounts.db"))

SCHEMA = """CREATE TABLE IF NOT EXISTS tmdb_cache (
    movie_id INTEGER PRIMARY KEY, poster_path TEXT, trailer_key TEXT,
    trailer_name TEXT, fetched_at REAL NOT NULL)"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="chi tai N phim dau (de thu)")
    args = ap.parse_args()
    if not tmdb_client.api_key():
        sys.exit("Chua dat TMDB_API_KEY. Dang ky mien phi tai themoviedb.org -> Settings -> API.")

    with sqlite3.connect(DB) as c:
        ids = [r[0] for r in c.execute("SELECT movie_id FROM movies ORDER BY popularity DESC")]
    acc = sqlite3.connect(ACCOUNTS_DB)
    acc.execute(SCHEMA)
    done = {r[0] for r in acc.execute("SELECT movie_id FROM tmdb_cache")}
    todo = [i for i in ids if i not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(done)} phim da co, can tai {len(todo)} phim.")

    ok = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(tmdb_client.fetch, mid): mid for mid in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            mid = futures[fut]
            try:
                d = fut.result()
                acc.execute("INSERT OR REPLACE INTO tmdb_cache VALUES (?, ?, ?, ?, ?)",
                            (mid, d["poster_path"], d["trailer_key"], d["trailer_name"], time.time()))
                ok += 1
            except Exception as e:           # loi mang: bo qua, chay lai de tai tiep
                fail += 1
                print(f"  loi phim {mid}: {e}")
            if n % 50 == 0:
                acc.commit()
                print(f"  {n}/{len(todo)}  ({time.time() - t0:.0f}s)")
    acc.commit()
    acc.close()
    print(f"Xong: {ok} thanh cong, {fail} loi. Khoi dong lai API de thay poster.")


if __name__ == "__main__":
    main()