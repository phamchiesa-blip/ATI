"""
scripts/fetch_tmdb_posters.py
-----------------------------
Tai poster + trailer cho toan bo phim trong movies.db tu TMDB, luu vao accounts.db
(bang tmdb_cache). Chay 1 lan (~5 phut cho 4772 phim), co the dung giua chung va chay lai:
phim da co se bo qua.

    # PowerShell:  $env:TMDB_API_KEY="khoa_cua_ban"
    python scripts/fetch_tmdb_posters.py
Xong thi khoi dong lai API (hoac doi toi 1 phut) de poster hien len.

Chia se cho ca nhom (nguoi khac KHONG can key):
    python scripts/fetch_tmdb_posters.py --export      # ghi data_module/tmdb_media.csv
    git add data_module/tmdb_media.csv                 # file nay khong chua bi mat, commit duoc
API tu nap file nay khi khoi dong (xem import_media_csv trong backend/core/database.py).
"""

import argparse
import csv
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ho tro chay truc tiep tu thu muc goc hoac tu thu muc scripts/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.integrations import tmdb_client

DB = os.environ.get("MOVIES_DB", os.path.join(ROOT, "data_module", "src", "movies.db"))
ACCOUNTS_DB = os.environ.get("ACCOUNTS_DB", os.path.join(ROOT, "accounts.db"))

SCHEMA = """CREATE TABLE IF NOT EXISTS tmdb_cache (
    movie_id INTEGER PRIMARY KEY, poster_path TEXT, trailer_key TEXT,
    trailer_name TEXT, fetched_at REAL NOT NULL)"""


def export(path: str) -> None:
    """Xuat poster_path / trailer_key da tai ra CSV de commit len git."""
    path = path if os.path.isabs(path) else os.path.join(ROOT, path)
    acc = sqlite3.connect(ACCOUNTS_DB)
    acc.execute(SCHEMA)
    rows = acc.execute("SELECT movie_id, poster_path, trailer_key, trailer_name FROM tmdb_cache "
                       "ORDER BY movie_id").fetchall()
    acc.close()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["movie_id", "poster_path", "trailer_key", "trailer_name"])
        w.writerows([[r[0], r[1] or "", r[2] or "", r[3] or ""] for r in rows])
    print(f"Da xuat {len(rows)} phim ra {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", nargs="?", const=os.path.join("data_module", "tmdb_media.csv"),
                    metavar="DUONG_DAN", help="xuat ket qua da tai ra CSV (khong can key) roi thoat")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="chi tai N phim dau (de thu)")
    args = ap.parse_args()
    if args.export:
        export(args.export)
        return
    if not tmdb_client.api_key():
        sys.exit("Chua dat TMDB_API_KEY. Dang ky mien phi tai themoviedb.org -> Settings -> API.")

    with sqlite3.connect(DB) as c:
        ids = [r[0] for r in c.execute("SELECT movie_id FROM movies ORDER BY popularity DESC")]
    acc = sqlite3.connect(ACCOUNTS_DB)
    acc.execute(SCHEMA)
    done = {r[0] for r in acc.execute("SELECT movie_id FROM tmdb_cache")}
    todo = [i for i in ids if i not in done]
    if args.limit:
        todo = todo[:args.limit]
    total = len(todo)
    if not total:
        print(f"Tat ca {len(done)} phim da co trong cache.")
        acc.close()
        return

    print(f"Can tai {total} phim (da co {len(done)} phim trong cache)...")
    success, errors = 0, 0
    t0 = time.time()

    def task(mid):
        return mid, tmdb_client.fetch(mid)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(task, mid): mid for mid in todo}
        for f in as_completed(futs):
            mid = futs[f]
            try:
                mid, res = f.result()
                now = time.time()
                acc.execute("INSERT OR REPLACE INTO tmdb_cache VALUES (?, ?, ?, ?, ?)",
                            (mid, res["poster_path"], res["trailer_key"], res["trailer_name"], now))
                acc.commit()
                success += 1
            except Exception as e:
                errors += 1
                print(f"[LOI] movie_id={mid}: {e}", file=sys.stderr)
            done_cnt = success + errors
            if done_cnt % 25 == 0 or done_cnt == total:
                elapsed = time.time() - t0
                speed = done_cnt / elapsed if elapsed > 0 else 0
                eta = (total - done_cnt) / speed if speed > 0 else 0
                print(f"[{done_cnt}/{total}] {success} thanh cong, {errors} loi "
                      f"({speed:.1f} phim/s, con khoang {eta/60:.1f} phut)")
    acc.close()
    print(f"Hoan tat: {success} thanh cong, {errors} loi trong {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

