import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
_DATA_MODULE_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data_module", "src")
)
sys.path.insert(0, _DATA_MODULE_SRC)

from recommender import like, dislike, recommend
from feature_store import get_movie_metadata

DB_PATH = os.path.join(_DATA_MODULE_SRC, "movies.db")


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at: {DB_PATH}")
        print("Please run build_dataset.py first.")
        return

    user_id = "test_user_01"
    movie_id_seed = 5

    print("=== TEST ONLINE RECOMMENDATION WITH MOVIES.DB ===")
    print(f"Database: {DB_PATH}")
    seed_movie = get_movie_metadata(movie_id_seed, db_path=DB_PATH)
    print(f"\n1. User '{user_id}' LIKES movie:")
    print(f"   -> [{movie_id_seed}] {seed_movie['title']} ({seed_movie['genres']})")
    like(user_id, movie_id_seed, db_path=DB_PATH)

    print("\n2. Top 5 Recommended Movies:")
    recommendations = recommend(user_id, k=5, db_path=DB_PATH)

    for rank, (m_id, score) in enumerate(recommendations, start=1):
        meta = get_movie_metadata(m_id, db_path=DB_PATH)
        print(f"   {rank}. [{m_id}] {meta['title']} ({meta['genres']}) - Score: {score:.4f}")

    print("\n=== TEST PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
