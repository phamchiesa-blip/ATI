"""
translate_overviews.py
----------------------
Dich san tom tat (overview) cua toan bo phim sang tieng Viet, luu vao accounts.db
(bang overview_vi). Nho vay giao dien hien tieng Viet ngay, khong phai doi dich.

Uu tien ban dich tieng Viet tren TMDB (neu co TMDB_API_KEY), khong co thi dich may.
Co the dung giua chung va chay lai: phim da dich se bo qua.

    python translate_overviews.py                # dich tat ca
    python translate_overviews.py --limit 200    # thu 200 phim pho bien nhat
    python translate_overviews.py --export       # ghi data_module/overview_vi.csv de chia se
API tu nap file CSV nay khi khoi dong (xem _import_overview_vi_csv trong api.py).
"""

import argparse
import csv
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import tmdb_client

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("MOVIES_DB", os.path.join(ROOT, "data_module", "src", "movies.db"))
ACCOUNTS_DB = os.environ.get("ACCOUNTS_DB", os.path.join(ROOT, "accounts.db"))
EXPORT = os.path.join(ROOT, "data_module", "overview_vi.csv")

SCHEMA = """CREATE TABLE IF NOT EXISTS overview_vi (
    movie_id INTEGER PRIMARY KEY, text TEXT, source TEXT, fetched_at REAL NOT NULL)"""


def translate(movie_id: int, original: str) -> "tuple[str, str]":
    text = None
    if tmdb_client.api_key():
        try:
            text = tmdb_client.fetch_overview_vi(movie_id)
        except Exception:
            text = None
        if text:
            return text, "tmdb"
    for attempt in range(3):
        try:
            text = tmdb_client.machine_translate_vi(original)
            break
        except Exception:
            time.sleep(1 + attempt * 2)
    if not text:
        raise RuntimeError("khong dich duoc")
    return text, "machine"


def export() -> None:
    acc = sqlite3.connect(ACCOUNTS_DB)
    acc.execute(SCHEMA)
    rows = acc.execute("SELECT movie_id, text, source FROM overview_vi ORDER BY movie_id").fetchall()
    acc.close()
    with open(EXPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["movie_id", "text", "source"])
        w.writerows(rows)
    print(f"Da xuat {len(rows)} phim ra {EXPORT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if args.export:
        export()
        return

    with sqlite3.connect(DB) as c:
        movies = [(r[0], r[1]) for r in c.execute(
            "SELECT movie_id, overview FROM movies WHERE overview IS NOT NULL AND overview != '' "
            "ORDER BY popularity DESC")]
    acc = sqlite3.connect(ACCOUNTS_DB)
    acc.execute(SCHEMA)
    done = {r[0] for r in acc.execute("SELECT movie_id FROM overview_vi WHERE text IS NOT NULL")}
    todo = [m for m in movies if m[0] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(done)} phim da dich, can dich {len(todo)} phim.")

    ok = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(translate, mid, ov): mid for mid, ov in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            mid = futures[fut]
            try:
                text, source = fut.result()
                acc.execute("INSERT OR REPLACE INTO overview_vi VALUES (?, ?, ?, ?)",
                            (mid, text, source, time.time()))
                ok += 1
            except Exception as e:
                fail += 1
                print(f"  loi phim {mid}: {e}")
            if n % 50 == 0:
                acc.commit()
                print(f"  {n}/{len(todo)}  ({time.time() - t0:.0f}s)")
    acc.commit()
    acc.close()
    print(f"Xong: {ok} thanh cong, {fail} loi.")


if __name__ == "__main__":
    main()
