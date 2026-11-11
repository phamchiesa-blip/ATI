"""
build_dataset.py
-----------------
Run the full Data & Feature Engineering pipeline end-to-end:

    tmdb_5000_movies.csv + tmdb_5000_credits.csv
        -> load_raw + clean_and_parse   (data_pipeline.py)
        -> build_feature_vectors        (feature_engineering.py)
        -> save_dataset                 (feature_store.py)
        -> movies.db  (ready for Son/Vo/Don to use)

Usage:
    python build_dataset.py \
        --movies path/to/tmdb_5000_movies.csv \
        --credits path/to/tmdb_5000_credits.csv \
        --db movies.db
"""

import argparse
import csv
import os
import sqlite3
import sys
import time

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from data_pipeline import load_raw, clean_and_parse
from feature_engineering import build_feature_vectors, FeatureConfig
from feature_store import save_dataset, get_all_vectors, get_movie_metadata, DEFAULT_DB_PATH


def main():
    parser = argparse.ArgumentParser(description="Build the movie feature-vector database.")
    parser.add_argument("--movies", required=True, help="path to tmdb_5000_movies.csv")
    parser.add_argument("--credits", required=True, help="path to tmdb_5000_credits.csv")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="output SQLite database path")
    args = parser.parse_args()

    t0 = time.time()

    print("[1/4] Loading raw CSV files...")
    raw = load_raw(args.movies, args.credits)
    print(f"      {len(raw)} movies loaded")

    print("[2/4] Cleaning and parsing...")
    clean = clean_and_parse(raw)
    print(f"      {len(clean)} movies kept after cleaning")

    print("[3/4] Building feature vectors...")
    movie_ids, vectors, info = build_feature_vectors(clean, FeatureConfig())
    print(f"      vector shape: {vectors.shape}  (dims: {info['total_dims']})")

    print(f"[4/4] Saving to {args.db} ...")
    # Sync any existing Vietnamese overview translations from accounts.db or overview_vi.csv into movies.db
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    overview_vi_map = {}
    acc_db = os.path.join(root_dir, "accounts.db")
    if os.path.exists(acc_db):
        try:
            conn = sqlite3.connect(acc_db)
            for mid, txt in conn.execute("SELECT movie_id, text FROM overview_vi WHERE text IS NOT NULL"):
                if txt and str(txt).strip():
                    overview_vi_map[int(mid)] = str(txt).strip()
            conn.close()
        except Exception:
            pass
    csv_vi = os.path.join(root_dir, "data_module", "overview_vi.csv")
    if os.path.exists(csv_vi):
        try:
            with open(csv_vi, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("movie_id") and r.get("text"):
                        overview_vi_map.setdefault(int(r["movie_id"]), r["text"].strip())
        except Exception:
            pass

    save_dataset(clean, movie_ids, vectors, db_path=args.db, overview_vi_map=overview_vi_map)

    print(f"\nDone in {time.time() - t0:.1f}s. Database ready at: {args.db}")

    # Quick self-check so we know the database was written correctly.
    ids_check, matrix_check = get_all_vectors(args.db)
    sample = get_movie_metadata(int(ids_check[0]), args.db)
    print(f"Self-check: {len(ids_check)} vectors stored, dim={matrix_check.shape[1]}")
    print(f"Sample movie: {sample['title']} ({sample['genres']})")


if __name__ == "__main__":
    main()
