"""
evaluate.py
------------
Script to run end-to-end evaluation. Run after movies.db has been built.

Usage:
    python evaluate.py --db movies.db --k 10
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np

from backend.database.database import get_all_vectors, get_all_metadata
from ai.baseline import baseline_recommend
from ai.ranking import rank_candidates
from ai.similarity import top_k_similar
from ai.user_profile import build_user_profile
from ai.evaluation import run_evaluation, run_cold_start_test, print_evaluation_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="movies.db")
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()

    print("Loading database...")
    all_ids, all_vecs = get_all_vectors(args.db)
    metadata = get_all_metadata(args.db)

    # Proposed system wrapper
    def proposed(liked_vecs, disliked_vecs, exclude_ids):
        profile = build_user_profile(liked_vecs, disliked_vecs)
        if profile is None:
            return []
        candidates = top_k_similar(profile, all_ids, all_vecs, k=50, exclude_ids=exclude_ids)
        return rank_candidates(candidates, metadata, top_n=args.k)

    # Baseline wrapper
    def baseline(liked_vecs, exclude_ids):
        return baseline_recommend(liked_vecs, all_ids, all_vecs, exclude_ids, top_n=args.k)

    print("Running evaluation...")
    results = run_evaluation(all_ids, all_vecs, metadata, proposed, baseline, k=args.k)
    print_evaluation_report(results, args.k)

    # Cold-start test (needs feature_info.json from main.py)
    if os.path.exists("feature_info.json"):
        with open("feature_info.json", encoding="utf-8") as f:
            fi = json.load(f)
        run_cold_start_test(
            all_ids, all_vecs, metadata,
            proposed_system=proposed,
            selected_genres=["Action", "Adventure"],
            genre_labels=fi["genre_labels"],
            total_dims=fi["total_dims"],
            k=args.k,
        )
    else:
        print("Skipping cold-start test: feature_info.json not found (run main.py first).")


if __name__ == "__main__":
    main()
