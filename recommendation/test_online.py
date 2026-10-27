import os
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(__file__))
_DATA_MODULE_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data_module", "src")
)
sys.path.insert(0, _DATA_MODULE_SRC)

from feature_store import DEFAULT_DB_PATH, check_db_exists, get_movie_metadata
from recommender import like, dislike, recommend

DB_PATH = DEFAULT_DB_PATH


def main():
    check_db_exists(DB_PATH)

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
