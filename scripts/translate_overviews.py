"""
scripts/translate_overviews.py
------------------------------
Dich san tom tat (overview) cua toan bo phim sang tieng Viet, luu vao accounts.db
(bang overview_vi). Nho vay giao dien hien tieng Viet ngay, khong phai doi dich.

Uu tien ban dich tieng Viet tren TMDB (neu co TMDB_API_KEY), khong co thi dich may.
Co the dung giua chung va chay lai: phim da dich se bo qua.

    python scripts/translate_overviews.py                # dich tat ca
    python scripts/translate_overviews.py --limit 200    # thu 200 phim pho bien nhat
    python scripts/translate_overviews.py --export       # ghi data_module/overview_vi.csv de chia se
API tu nap file CSV nay khi khoi dong (xem import_overview_vi_csv trong backend/core/database.py).
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
    return text, "google"


def export(path: str = EXPORT) -> None:
    path = path if os.path.isabs(path) else os.path.join(ROOT, path)
    acc = sqlite3.connect(ACCOUNTS_DB)
    acc.execute(SCHEMA)
    rows = acc.execute("SELECT movie_id, text, source FROM overview_vi ORDER BY movie_id").fetchall()
    acc.close()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["movie_id", "text", "source"])
        w.writerows(rows)
    print(f"Da xuat {len(rows)} ban dich ra {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", nargs="?", const=EXPORT, metavar="DUONG_DAN",
                    help="xuat bang overview_vi ra file CSV roi thoat")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="chi dich N phim dau")
    args = ap.parse_args()
    if args.export:
        export(args.export)
        return

    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT movie_id, overview FROM movies "
            "WHERE overview IS NOT NULL AND trim(overview) != '' "
            "ORDER BY popularity DESC"
        ).fetchall()

    acc = sqlite3.connect(ACCOUNTS_DB)
    acc.execute(SCHEMA)
    done = {r[0] for r in acc.execute("SELECT movie_id FROM overview_vi")}
    todo = [(mid, ov) for mid, ov in rows if mid not in done]
    if args.limit:
        todo = todo[:args.limit]
    total = len(todo)
    if not total:
        print(f"Tat ca {len(done)} phim da co ban dich trong cache.")
        acc.close()
        return

    src_label = "TMDB (uu tien) + Google Translate" if tmdb_client.api_key() else "Google Translate"
    print(f"Can dich {total} phim (da co {len(done)} phim trong cache)... Nguon: {src_label}")
    success, errors = 0, 0
    t0 = time.time()

    def task(item):
        mid, ov = item
        t, src = translate(mid, ov)
        return mid, t, src

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(task, it): it[0] for it in todo}
        for f in as_completed(futs):
            mid = futs[f]
            try:
                mid, txt, src = f.result()
                now = time.time()
                acc.execute("INSERT OR REPLACE INTO overview_vi VALUES (?, ?, ?, ?)",
                            (mid, txt, src, now))
                acc.commit()
                success += 1
            except Exception as e:
                errors += 1
                print(f"[LOI] movie_id={mid}: {e}", file=sys.stderr)
            done_cnt = success + errors
            if done_cnt % 20 == 0 or done_cnt == total:
                elapsed = time.time() - t0
                speed = done_cnt / elapsed if elapsed > 0 else 0
                eta = (total - done_cnt) / speed if speed > 0 else 0
                print(f"[{done_cnt}/{total}] {success} thanh cong, {errors} loi "
                      f"({speed:.1f} phim/s, con khoang {eta/60:.1f} phut)")
    acc.close()
    print(f"Hoan tat: {success} thanh cong, {errors} loi trong {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

