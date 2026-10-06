"""
test_offline.py
---------------
Kiem tra toan bo Recommendation Core KHONG can movies.db.
Su dung mock cho get_movie_vector va get_all_vectors.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np

# ── 1. Test UserProfile ──────────────────────────────────────────────────────
from user_profile import UserProfile, ALPHA, BETA

print("=== 1. UserProfile ===")
p = UserProfile("user_001")
assert not p.is_initialized(), "Profile phai chua duoc khoi tao"

# Onboarding
v_action = np.array([1.0, 0.0, 0.0, 0.5], dtype=np.float32)   # Action genre
v_scifi  = np.array([0.0, 1.0, 0.0, 0.5], dtype=np.float32)   # SciFi genre
p.seed_from_movies([v_action, v_scifi])
expected_seed = np.array([0.5, 0.5, 0.0, 0.5], dtype=np.float32)
assert np.allclose(p.vector, expected_seed), f"Seed sai: {p.vector}"
print(f"  seed_from_movies OK: {p.vector}")

# Like
v_like = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)
p.apply_like(v_like)
expected_like = expected_seed + ALPHA * v_like
assert np.allclose(p.vector, expected_like), f"Like sai: {p.vector}"
print(f"  apply_like OK:       {p.vector}")

# Dislike
v_dislike = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
p.apply_dislike(v_dislike)
expected_dislike = expected_like - BETA * v_dislike
assert np.allclose(p.vector, expected_dislike), f"Dislike sai: {p.vector}"
print(f"  apply_dislike OK:    {p.vector}")
print()

# ── 2. Test cosine_similarity ────────────────────────────────────────────────
from similarity import cosine_similarity, cosine_similarity_bulk, get_top_k_movies

print("=== 2. Cosine Similarity ===")
u = np.array([1.0, 0.0])
m_same      = np.array([1.0, 0.0])
m_ortho     = np.array([0.0, 1.0])
m_opposite  = np.array([-1.0, 0.0])

assert cosine_similarity(u, m_same)     == 1.0,  "Same vector phai bang 1.0"
assert cosine_similarity(u, m_ortho)    == 0.0,  "Ortho vector phai bang 0.0"
assert cosine_similarity(u, m_opposite) == -1.0, "Opposite vector phai bang -1.0"
# Zero vector
assert cosine_similarity(np.zeros(2), m_same) == 0.0, "Zero vector phai tra 0.0"
print("  cosine_similarity OK")

# Bulk
user_vec = np.array([1.0, 0.0, 0.0])
matrix = np.array([
    [1.0, 0.0, 0.0],   # phim 0: score = 1.0
    [0.0, 1.0, 0.0],   # phim 1: score = 0.0
    [0.5, 0.5, 0.0],   # phim 2: score ~0.707
    [0.0, 0.0, 0.0],   # phim 3: score = 0.0 (zero vector)
])
scores = cosine_similarity_bulk(user_vec, matrix)
assert np.isclose(scores[0], 1.0), f"Bulk score[0] sai: {scores[0]}"
assert np.isclose(scores[1], 0.0), f"Bulk score[1] sai: {scores[1]}"
assert scores[2] > 0.7, f"Bulk score[2] sai: {scores[2]}"
assert np.isclose(scores[3], 0.0), f"Bulk zero sai: {scores[3]}"
print(f"  cosine_similarity_bulk OK: {scores}")
print()

# ── 3. Test get_top_k_movies ─────────────────────────────────────────────────
print("=== 3. Top-K ===")
movie_ids = np.array([10, 20, 30, 40, 50])
movie_mat = np.array([
    [1.0, 0.0],   # movie 10: score 1.0
    [0.9, 0.1],   # movie 20: score ~0.994
    [0.0, 1.0],   # movie 30: score 0.0
    [0.8, 0.2],   # movie 40: score ~0.970
    [0.7, 0.3],   # movie 50: score ~0.920
], dtype=np.float32)
user_v = np.array([1.0, 0.0], dtype=np.float32)

top3 = get_top_k_movies(user_v, movie_ids, movie_mat, k=3)
assert len(top3) == 3, f"Top-K phai tra 3 phan tu, nhan {len(top3)}"
top3_ids = [t[0] for t in top3]
assert top3_ids[0] == 10, f"Phan tu dau phai la movie 10, nhan {top3_ids[0]}"
print(f"  Top-3: {top3}")

# Loai phim da tuong tac
top3_excl = get_top_k_movies(user_v, movie_ids, movie_mat, k=3, exclude_ids={10, 20})
top3_excl_ids = [t[0] for t in top3_excl]
assert 10 not in top3_excl_ids, "Movie 10 phai bi loai"
assert 20 not in top3_excl_ids, "Movie 20 phai bi loai"
print(f"  Top-3 (exclude 10,20): {top3_excl}")
print()

print("=== ALL TESTS PASSED ===")
