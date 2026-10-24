# Thử nghiệm và phân tích hành vi thuật toán khi người dùng chỉ bấm Dislike mà chưa có tín hiệu dương.

import sys
import os
import sqlite3
import json
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "data_module", "src"))
sys.path.insert(0, os.path.join(_ROOT, "recommendation"))
sys.path.insert(0, os.path.join(_ROOT, "ranking_eval"))

from feature_store import get_movie_vector, get_all_vectors, get_movie_metadata
from user_profile import UserProfile
from similarity import cosine_similarity_bulk

db = os.path.join(_ROOT, "data_module", "src", "movies.db")
conn = sqlite3.connect(db)

# 1. Chon 5 phim Horror pho bien nhat
rows = conn.execute(
    'SELECT movie_id, title, genres FROM movies WHERE genres LIKE \'%"Horror"%\' ORDER BY popularity DESC LIMIT 5'
).fetchall()
print("=== 5 Disliked Horror Movies ===")
disliked_ids = []
for mid, title, g in rows:
    disliked_ids.append(mid)
    print(f"Dislike: [{mid}] {title} ({g})")

# 2. Tao profile va dislike ca 5 phim
user_id = "test_dislike_only_user"
p = UserProfile(user_id)
for mid in disliked_ids:
    vec = get_movie_vector(mid, db_path=db)
    p.apply_dislike(vec)

print("\n=== Profile Vector Stats ===")
print(f"Shape: {p.vector.shape}")
print(f"Min: {p.vector.min():.4f}, Mean: {p.vector.mean():.4f}, Max: {p.vector.max():.4f}")
print(f"Negative elements: {(p.vector < 0).sum()} / {len(p.vector)}")
print(f"Zero elements:     {(p.vector == 0).sum()} / {len(p.vector)}")
print(f"Positive elements: {(p.vector > 0).sum()} / {len(p.vector)}")

# In chi tiet 3 chieu cuoi (vote_average, popularity, release_year)
print(f"Numeric dims (rating, popularity, year) in profile vector: {p.vector[-3:]}")

# 3. Tinh Cosine similarity voi toan bo kho phim
movie_ids, matrix = get_all_vectors(db_path=db)
scores = cosine_similarity_bulk(p.vector, matrix)

print("\n=== Score Distribution Across All 4772 Movies ===")
print(f"Min score:    {np.min(scores):.4f}")
print(f"Median score: {np.median(scores):.4f}")
print(f"Mean score:   {np.mean(scores):.4f}")
print(f"Max score:    {np.max(scores):.4f}")
print(f"Scores < 0:   {(scores < 0).sum()} ({(scores < 0).sum() / len(scores) * 100:.1f}%)")
print(f"Scores == 0:  {(scores == 0).sum()} ({(scores == 0).sum() / len(scores) * 100:.1f}%)")
print(f"Scores > 0:   {(scores > 0).sum()} ({(scores > 0).sum() / len(scores) * 100:.1f}%)")

# 4. Loai cac phim da dislike
mask = np.array([mid not in disliked_ids for mid in movie_ids], dtype=bool)
filtered_ids = movie_ids[mask]
filtered_scores = scores[mask]

sorted_idx = np.argsort(filtered_scores)[::-1]
print("\n=== Top 10 Recommended Movies (by Cosine Score) ===")
for i in range(10):
    idx = sorted_idx[i]
    mid = int(filtered_ids[idx])
    sc = float(filtered_scores[idx])
    meta = get_movie_metadata(mid, db_path=db)
    print(f"{i+1:2d}. [{mid:6d}] {meta['title']:<35} | {meta['genres']} | Cosine: {sc:+.4f}")

print("\n=== Bottom 5 Movies (Worst Negative Cosine Score) ===")
for i in range(1, 6):
    idx = sorted_idx[-i]
    mid = int(filtered_ids[idx])
    sc = float(filtered_scores[idx])
    meta = get_movie_metadata(mid, db_path=db)
    print(f"{i:2d}. [{mid:6d}] {meta['title']:<35} | {meta['genres']} | Cosine: {sc:+.4f}")
