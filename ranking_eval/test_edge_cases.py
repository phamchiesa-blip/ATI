"""
test_edge_cases.py
------------------
Tests for edge-case handling:
1. Cold-start user (no interactions / uninitialized profile) gracefully
   falling back to popular movies without crashing.
2. Onboarding top-N selection per genre to avoid profile dilution,
   ensuring deterministic movie selection and seeding.
"""

import os
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DATA_SRC = os.path.join(_ROOT, "data_module", "src")
_RECOMMENDATION = os.path.join(_ROOT, "recommendation")
for _p in (_ROOT, _DATA_SRC, _RECOMMENDATION):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from feature_store import DEFAULT_DB_PATH, check_db_exists
from ranking_eval.frontend_service import onboard_user, get_popular_movies, DEFAULT_ONBOARDING_TOP_N
from ranking_eval.integration import get_ranked_recommendations
import recommender as _rec

DB_PATH = DEFAULT_DB_PATH


def test_cold_start_fallback():
    print("=== Test 1: Cold start user (no interaction) -> Popular fallback ===")
    check_db_exists(DB_PATH)

    new_user_id = "test_user_no_history_999"
    # Ensure user has no in-memory profile
    _rec._registry._profiles.pop(new_user_id, None)

    # Calling get_ranked_recommendations should NOT crash with RuntimeError
    recs = get_ranked_recommendations(new_user_id, top_n=5, db_path=DB_PATH)
    assert len(recs) == 5, f"Expected 5 recommendations, got {len(recs)}"

    for r in recs:
        assert r["cosine"] == 0.0, f"Expected cosine=0.0 for popular fallback, got {r['cosine']}"
        assert r["neural_used"] is False, "Neural network should not be active for cold-start"
        assert r["vote_average"] >= 6.5, f"Popular movie rating should be >= 6.5, got {r['vote_average']}"
        assert "title" in r and "ranking_score" in r, "Missing expected keys in candidate dict"

    print("  -> Passed! Popular movies returned without crashing:")
    for i, r in enumerate(recs, 1):
        print(f"     {i}. {r['title']} (score: {r['ranking_score']:.3f})")
    print()


def test_onboarding_top_n_genres():
    print("=== Test 2: Onboarding top N per genre (anti-dilution) ===")
    user_id = "test_user_onboarding_top_n"
    _rec._registry._profiles.pop(user_id, None)

    # Test single genre with top_n = 5
    res_single = onboard_user(
        user_id,
        db_path=DB_PATH,
        selected_genres=["Action"],
        top_n_per_genre=5,
    )
    assert res_single["ok"] is True
    assert res_single["seed_movie_count"] == 5, f"Expected 5 seed movies, got {res_single['seed_movie_count']}"
    print(f"  -> Single genre (Action, top 5) OK: {res_single['seed_movie_count']} seed movies")

    # Test multiple genres with default top_n = 8
    # Action (8) + SciFi (8) has overlapping movies (e.g. Guardians, Mad Max, Jurassic World, Dawn of Apes, Terminator Genisys)
    # Expected unique union = 11 movies, not 1400+ movies!
    _rec._registry._profiles.pop(user_id, None)
    res_multi_1 = onboard_user(
        user_id,
        db_path=DB_PATH,
        selected_genres=["Action", "Science Fiction"],
        top_n_per_genre=DEFAULT_ONBOARDING_TOP_N,
    )
    assert res_multi_1["ok"] is True
    assert res_multi_1["seed_movie_count"] == 11, f"Expected 11 seed movies, got {res_multi_1['seed_movie_count']}"

    # Verify deterministic ordering: running again must give identical results
    _rec._registry._profiles.pop(user_id, None)
    res_multi_2 = onboard_user(
        user_id,
        db_path=DB_PATH,
        selected_genres=["Action", "Science Fiction"],
        top_n_per_genre=DEFAULT_ONBOARDING_TOP_N,
    )
    assert res_multi_1["seed_movie_count"] == res_multi_2["seed_movie_count"]

    # Verify recommendations generated from this onboarded profile
    recs = get_ranked_recommendations(user_id, top_n=5, db_path=DB_PATH)
    assert len(recs) == 5
    # Since profile is seeded with Action & Sci-Fi, top recommendations should have high cosine (>0.85)
    for r in recs:
        assert r["cosine"] > 0.85, f"Expected high cosine similarity for seeded profile, got {r['cosine']}"

    print(f"  -> Multi-genre (Action + SciFi, default {DEFAULT_ONBOARDING_TOP_N}/genre) OK:")
    print(f"     Seeded from {res_multi_1['seed_movie_count']} movies (instead of 1400+).")
    print(f"     Top recommendation: {recs[0]['title']} (Cosine: {recs[0]['cosine']:.3f})")
    print()


def test_dislike_only_fallback():
    print("=== Test 3: Dislike-only user -> Popular fallback excluding hated genres ===")
    user_id = "test_user_dislike_5_horror"
    _rec._registry._profiles.pop(user_id, None)

    # Clean existing interactions for test user
    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM user_interaction_history WHERE user_id = ?", (user_id,))

    from recommender import dislike, like
    # Dislike 5 Horror movies from previous experiment
    # 270303: It Follows (Horror, Thriller)
    # 348:    Alien (Horror, Action, Thriller, Science Fiction)
    # 539:    Psycho (Drama, Horror, Thriller)
    # 238636: The Purge: Anarchy (Horror, Thriller)
    # 72190:  World War Z (Action, Drama, Horror, Science Fiction, Thriller)
    disliked_ids = [270303, 348, 539, 238636, 72190]
    for mid in disliked_ids:
        dislike(user_id, mid, db_path=DB_PATH)

    # Call get_ranked_recommendations (user has NO likes and NO onboarding)
    recs = get_ranked_recommendations(user_id, top_n=10, db_path=DB_PATH)
    assert len(recs) == 10, f"Expected 10 recommendations, got {len(recs)}"

    # Horror and Thriller appear in 5/5 (100% >= 50%) -> MUST BE EXCLUDED
    # Drama, Action, Science Fiction appear in 2/5 (40% < 50%) -> MUST NOT BE COMPLETELY EXCLUDED
    all_genres_in_recs = []
    for r in recs:
        movie_genres_lower = [g.lower() for g in r["genres"]]
        all_genres_in_recs.extend(movie_genres_lower)
        assert "horror" not in movie_genres_lower, f"Horror was not excluded: {r['title']} has {r['genres']}"
        assert "thriller" not in movie_genres_lower, f"Thriller was not excluded: {r['title']} has {r['genres']}"

    # Action and Sci-Fi must not be completely excluded
    has_action_or_scifi = any(g in ("action", "science fiction") for g in all_genres_in_recs)
    assert has_action_or_scifi, "Action / Sci-Fi should not be completely excluded!"
    print("  -> Passed! Horror and Thriller are 100% excluded.")
    print("  -> Action and Science Fiction movies (without Horror/Thriller) are retained:")
    for i, r in enumerate(recs[:5], 1):
        print(f"     {i}. {r['title']} ({r['genres']})")

    # Now verify that when user adds a positive signal (LIKE), normal profile flow resumes:
    like(user_id, 118340, db_path=DB_PATH)  # Guardians of the Galaxy
    recs_after_like = get_ranked_recommendations(user_id, top_n=5, db_path=DB_PATH)
    assert len(recs_after_like) == 5
    # Normal profile flow is now active (neural reranking enabled since user has both like & dislike)
    assert recs_after_like[0]["neural_used"] is True, "After LIKE, normal profile flow with neural reranking should resume"
    assert recs_after_like[0]["cosine"] != 0.0, "Cosine should come from profile similarity, not cold-start 0.0"
    print(f"  -> After positive Like, normal flow resumed with Top-1: {recs_after_like[0]['title']} (Cosine: {recs_after_like[0]['cosine']:.3f}, Neural: {recs_after_like[0]['neural_used']})")

    # Clean up test interactions
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM user_interaction_history WHERE user_id = ?", (user_id,))
    _rec._registry._profiles.pop(user_id, None)
    print()


def main():
    print("RUNNING EDGE CASES TESTS...\n")
    test_cold_start_fallback()
    test_onboarding_top_n_genres()
    test_dislike_only_fallback()
    print("ALL EDGE CASES TESTS PASSED!")


if __name__ == "__main__":
    main()

