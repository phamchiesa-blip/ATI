# 🎬 ATI — Coding Plan: Phần 2 (Sơn) & Phần 4 (Đôn)

> **Trạng thái codebase hiện tại**: skeleton đã có đầy đủ — `ai/`, `database/`, `services/`, `api/` đã có file nhưng nhiều phần còn thiếu logic hoặc cần hoàn thiện đúng spec báo cáo.

---

## 🗂️ Tổng quan file cần đụng tới

| File | Người làm | Trạng thái |
|------|-----------|------------|
| `ai/user_profile.py` | Sơn | ⚠️ Cần sửa — công thức chưa đúng spec |
| `ai/similarity.py` | Sơn | ✅ Đã ổn, không cần sửa |
| `ai/recommender.py` | Sơn | ⚠️ Cần bổ sung onboarding cold-start |
| `services/recommendation_service.py` | Sơn | ⚠️ Cần bổ sung onboarding init profile |
| `api/feedback.py` | Sơn | ⚠️ Cần thêm logic gọi update profile |
| `ai/ranking.py` | Đôn | ⚠️ Cần bổ sung vote_average vào blended score |
| `ai/neural_network.py` | Đôn | ⚠️ Cần hoàn thiện với SGDClassifier + partial_fit |
| `ai/evaluation.py` | Đôn | 🆕 Tạo mới hoàn toàn |
| `ai/baseline.py` | Đôn | 🆕 Tạo mới hoàn toàn |
| `services/profile_service.py` | Sơn | 🆕 Tạo mới — quản lý user profile in-memory + DB |

---

---

# PHẦN 2 — SƠN: Recommendation Core

## Mục tiêu cuối

Từ `get_movie_vector(movie_id)` của Chuyên → dựng `UserProfile` → tính Cosine Similarity → trả Top-K cho Đôn rank lại → trả về gợi ý cho Võ hiển thị.

---

## Task 2.1 — Sửa `ai/user_profile.py`

> **Vấn đề hiện tại**: `build_user_profile()` dùng `mean()` thay vì đúng công thức α/β. `update_user_profile()` dùng EMA thay vì cộng/trừ trực tiếp.

### Spec công thức (từ báo cáo 3.3):
```
Like:    UserProfile_new = UserProfile_old + α × V_movie   (α = 1.0)
Dislike: UserProfile_new = UserProfile_old − β × V_movie   (β = 0.5)
```

### Sửa file `ai/user_profile.py` — rewrite 2 hàm:

```python
ALPHA = 1.0   # weight khi Like
BETA  = 0.5   # weight khi Dislike

def build_initial_profile_from_genres(genre_vector: np.ndarray) -> np.ndarray:
    """
    Cold-start onboarding: user mới chọn genre → tạo profile ban đầu.
    genre_vector: multi-hot vector, cùng kích thước với movie feature vector.
                  Chỉ phần genre được set, phần còn lại = 0.
    Trả về profile chuẩn hóa L2 để cosine similarity hoạt động đúng.
    """
    norm = np.linalg.norm(genre_vector)
    if norm == 0:
        return genre_vector.astype(np.float32)
    return (genre_vector / norm).astype(np.float32)


def update_user_profile(
    current_profile: np.ndarray,
    new_vector: np.ndarray,
    action: str,          # 'like' hoặc 'dislike'
    alpha: float = ALPHA,
    beta: float = BETA,
) -> np.ndarray:
    """
    Cập nhật profile theo đúng công thức trong báo cáo:
        Like:    profile = profile + alpha * v_movie
        Dislike: profile = profile - beta  * v_movie
    Không normalize — để biên độ profile phản ánh mức độ sở thích.
    """
    if current_profile is None:
        if action == "like":
            return (alpha * new_vector).astype(np.float32)
        return None   # dislike đầu tiên không tạo profile

    if action == "like":
        updated = current_profile + alpha * new_vector
    else:
        updated = current_profile - beta * new_vector
    return updated.astype(np.float32)


def build_user_profile(liked_vectors: list, disliked_vectors: list = None) -> np.ndarray:
    """
    Build profile từ đầu từ toàn bộ history (dùng khi load lại từ DB).
    Áp dụng lần lượt: start từ zero vector, cộng dồn likes, trừ dislikes.
    """
    if not liked_vectors:
        return None

    dim = liked_vectors[0].shape[0]
    profile = np.zeros(dim, dtype=np.float32)

    for v in liked_vectors:
        profile += ALPHA * v
    for v in (disliked_vectors or []):
        profile -= BETA * v

    return profile.astype(np.float32)
```

### Thêm hàm helper để tạo genre vector:

```python
def make_genre_profile_vector(
    selected_genres: list,   # ['Action', 'Comedy']
    genre_labels: list,      # danh sách genre từ feature_info['genre_labels']
    total_dims: int,         # tổng số chiều của feature vector
) -> np.ndarray:
    """
    Tạo genre vector (multi-hot) có cùng kích thước với movie feature vector.
    Chỉ phần genre (đầu vector) được fill, phần còn lại = 0.
    """
    vec = np.zeros(total_dims, dtype=np.float32)
    genre_set = set(selected_genres)
    for i, g in enumerate(genre_labels):
        if g in genre_set:
            vec[i] = 1.0
    return vec
```

---

## Task 2.2 — Tạo mới `services/profile_service.py`

> **Mục đích**: tách biệt quản lý User Profile ra khỏi `recommendation_service.py`, vì profile cần được lưu và load giữa các request.

```python
"""
profile_service.py
-------------------
Quản lý User Profile vector: khởi tạo (onboarding), cập nhật (like/dislike),
lưu vào DB và load lại khi cần.

Schema DB cần thêm (bổ sung vào database.py):
    user_profiles (user_id TEXT PK, profile BLOB, dims INTEGER, updated_at TEXT)
"""

import numpy as np
from database.database import (
    get_movie_vector, get_user_interactions,
    save_user_profile, load_user_profile,  # 2 hàm cần thêm vào database.py
    DEFAULT_DB_PATH,
)
from ai.user_profile import (
    build_user_profile,
    update_user_profile,
    build_initial_profile_from_genres,
    make_genre_profile_vector,
)


def initialize_profile_from_onboarding(
    user_id: str,
    selected_genres: list,       # từ màn hình Onboarding của Võ
    genre_labels: list,          # lấy từ feature_info, lưu khi build DB
    total_dims: int,
    db_path=DEFAULT_DB_PATH,
) -> np.ndarray:
    """
    Gọi khi user mới hoàn thành onboarding.
    Tạo profile ban đầu từ genres đã chọn và lưu vào DB.
    """
    genre_vec = make_genre_profile_vector(selected_genres, genre_labels, total_dims)
    profile = build_initial_profile_from_genres(genre_vec)
    save_user_profile(user_id, profile, db_path=db_path)
    return profile


def process_feedback_and_update(
    user_id: str,
    movie_id: int,
    action: str,    # 'like' hoặc 'dislike'
    db_path=DEFAULT_DB_PATH,
) -> np.ndarray:
    """
    Gọi khi user bấm Like/Dislike.
    Load profile hiện tại → update → lưu lại.
    """
    current_profile = load_user_profile(user_id, db_path=db_path)
    movie_vec = get_movie_vector(movie_id, db_path=db_path)
    if movie_vec is None:
        return current_profile

    updated = update_user_profile(current_profile, movie_vec, action)
    save_user_profile(user_id, updated, db_path=db_path)
    return updated


def get_or_rebuild_profile(user_id: str, db_path=DEFAULT_DB_PATH) -> np.ndarray:
    """
    Load profile từ DB. Nếu chưa có → rebuild từ interaction history.
    Fallback an toàn khi DB bị reset.
    """
    profile = load_user_profile(user_id, db_path=db_path)
    if profile is not None:
        return profile

    # Rebuild từ history
    interactions = get_user_interactions(user_id, db_path=db_path)
    liked_vecs = [get_movie_vector(i["movie_id"], db_path) for i in interactions if i["action"] == "like"]
    disliked_vecs = [get_movie_vector(i["movie_id"], db_path) for i in interactions if i["action"] == "dislike"]
    liked_vecs = [v for v in liked_vecs if v is not None]
    disliked_vecs = [v for v in disliked_vecs if v is not None]

    return build_user_profile(liked_vecs, disliked_vecs)
```

---

## Task 2.3 — Bổ sung vào `database/database.py`

> Thêm table `user_profiles` và 2 hàm CRUD cho profile.

**Thêm vào `create_schema()`:**
```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id    TEXT PRIMARY KEY,
    profile    BLOB NOT NULL,   -- float32 numpy array
    dims       INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Thêm 2 hàm mới:**
```python
def save_user_profile(user_id: str, profile: np.ndarray, db_path=DEFAULT_DB_PATH):
    """Lưu (hoặc cập nhật) user profile vector vào DB."""
    conn = _connect(db_path)
    conn.execute(
        """INSERT OR REPLACE INTO user_profiles (user_id, profile, dims, updated_at)
           VALUES (?, ?, ?, ?)""",
        (user_id, profile.astype(np.float32).tobytes(),
         profile.shape[0], datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def load_user_profile(user_id: str, db_path=DEFAULT_DB_PATH) -> np.ndarray | None:
    """Load user profile vector từ DB. Trả None nếu chưa có."""
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT profile, dims FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    blob, dims = row
    return np.frombuffer(blob, dtype=np.float32).reshape(dims)
```

---

## Task 2.4 — Sửa `api/feedback.py`

> Sau khi ghi interaction, cần trigger update profile ngay.

```python
from database.database import log_interaction, get_user_interactions, DEFAULT_DB_PATH
from services.profile_service import process_feedback_and_update


def submit_feedback(user_id: str, movie_id: int, action: str, db_path: str = DEFAULT_DB_PATH) -> dict:
    """POST /api/feedback — ghi like/dislike và cập nhật profile ngay."""
    log_interaction(user_id, movie_id, action, db_path=db_path)
    process_feedback_and_update(user_id, movie_id, action, db_path=db_path)
    return {"status": "ok", "user_id": user_id, "movie_id": movie_id, "action": action}
```

---

## Task 2.5 — Sửa `services/recommendation_service.py`

> Thay vì rebuild profile từ history mỗi request, load từ `profile_service`.

**Thay đoạn build liked/disliked vectors bằng:**
```python
from services.profile_service import get_or_rebuild_profile

def recommend_for_user(user_id: str, top_n: int = 10, db_path=DEFAULT_DB_PATH) -> list:
    _ensure_cache(db_path)

    profile = get_or_rebuild_profile(user_id, db_path=db_path)

    interactions = get_user_interactions(user_id, db_path=db_path)
    all_interacted = [i["movie_id"] for i in interactions]

    if profile is None:
        # Cold-start hoàn toàn (chưa onboarding lẫn chưa like/dislike)
        from services.movie_service import get_popular_movies
        return get_popular_movies(db_path=db_path, limit=top_n)

    from ai.similarity import top_k_similar
    from ai.ranking import rank_candidates

    candidates = top_k_similar(
        query_vector=profile,
        movie_ids=_cached_ids,
        matrix=_cached_matrix,
        k=50,
        exclude_ids=all_interacted,
    )

    return rank_candidates(candidates, _cached_metadata, top_n=top_n)
```

---

## Task 2.6 — Thêm API endpoint onboarding

> Tạo `api/onboarding.py` (mới) để Võ gọi khi user hoàn thành màn hình onboarding.

```python
"""api/onboarding.py"""
from services.profile_service import initialize_profile_from_onboarding
from database.database import DEFAULT_DB_PATH

# genre_labels và total_dims cần load từ feature_info
# (lưu vào 1 file JSON khi chạy main.py hoặc từ DB metadata)

def handle_onboarding(
    user_id: str,
    selected_genres: list,  # ['Action', 'Comedy']
    db_path: str = DEFAULT_DB_PATH,
) -> dict:
    """POST /api/onboarding"""
    profile = initialize_profile_from_onboarding(
        user_id=user_id,
        selected_genres=selected_genres,
        genre_labels=_load_genre_labels(db_path),   # helper bên dưới
        total_dims=_load_total_dims(db_path),
        db_path=db_path,
    )
    return {"status": "ok", "user_id": user_id, "profile_norm": float(np.linalg.norm(profile))}
```

> **Lưu ý**: `genre_labels` và `total_dims` cần được lưu khi `main.py` chạy xong. Thêm vào `main.py`:
> ```python
> import json
> with open("feature_info.json", "w") as f:
>     json.dump({k: list(v) if isinstance(v, (list, tuple)) else v
>                for k, v in info.items() if k != "column_ranges"}, f)
> ```

---

## Task 2.7 — Mock data để test khi chờ phần Data

```python
# tests/mock_data.py — dùng khi movies.db chưa có
import numpy as np

N_FEATURES = 320   # tổng dims dự kiến (20 genre + 51 director + 200 cast + 50 overview + 3 numeric)
N_MOVIES = 100

def make_mock_matrix():
    np.random.seed(42)
    ids = np.arange(1, N_MOVIES + 1)
    matrix = np.random.rand(N_MOVIES, N_FEATURES).astype(np.float32)
    return ids, matrix

def make_mock_metadata():
    import random
    genres_pool = ["Action", "Comedy", "Drama", "Horror", "Sci-Fi"]
    return {
        i: {
            "title": f"Mock Movie {i}",
            "genres": random.sample(genres_pool, k=2),
            "vote_average": round(random.uniform(5, 9), 1),
            "popularity": random.uniform(10, 200),
            "release_date": f"{random.randint(2000, 2023)}-01-01",
        }
        for i in range(1, N_MOVIES + 1)
    }
```

---

---

# PHẦN 4 — ĐÔN: Ranking + Neural Network + Evaluation

## Mục tiêu cuối

Nhận Top-K từ Sơn (Cosine Similarity) → re-rank với blended score → Neural Network Tier 2 (optional) → Evaluation với simulated users → Báo cáo Precision@K, Recall@K, F1@K.

---

## Task 4.1 — Sửa `ai/ranking.py`

> **Vấn đề**: thiếu `vote_average` (Rating) trong blended score. Báo cáo mục 3.7 yêu cầu kết hợp: Cosine Similarity + Rating + Popularity + Newness.

**Sửa function signature và logic:**

```python
def rank_candidates(
    candidates: list,
    metadata_map: dict,
    similarity_weight: float = 0.50,   # cosine sim
    rating_weight: float = 0.20,       # vote_average
    popularity_weight: float = 0.20,   # popularity
    recency_weight: float = 0.10,      # release year
    diversity_max_per_genre: int = 3,
    top_n: int = 10,
) -> list:
    """
    Re-rank theo công thức:
        score = w_sim * sim_n + w_rating * rating_n + w_pop * pop_n + w_rec * year_n
    """
    # ... (giữ nguyên cấu trúc, thêm rating_scores)

    rating_scores = np.array(
        [metadata_map.get(mid, {}).get("vote_average", 0.0) or 0.0 for mid in ids],
        dtype=np.float32,
    )
    rating_n = _normalize(rating_scores)

    blended = (
        similarity_weight * sim_n
        + rating_weight    * rating_n
        + popularity_weight * pop_n
        + recency_weight   * year_n
    )
    # ... diversity filter giữ nguyên
```

---

## Task 4.2 — Tạo mới `ai/baseline.py`

> Baseline là hệ thống đơn giản hơn để **so sánh** với proposed approach (theo mục 3.9 báo cáo).

```python
"""
ai/baseline.py
---------------
Baseline recommender — không có Ranking module, không có Neural Network.
Chỉ dùng average của liked vectors làm profile, sort thuần theo cosine similarity.

Dùng để so sánh với proposed approach trong Evaluation.
"""

import numpy as np
from ai.similarity import cosine_similarity_matrix


def baseline_recommend(
    liked_vectors: list,
    all_movie_ids: np.ndarray,
    all_vectors: np.ndarray,
    exclude_ids: list = None,
    top_n: int = 10,
) -> list:
    """
    Baseline: average profile → cosine sim → sort → Top-N (không re-rank).

    Returns
    -------
    list of dict: [{'movie_id': int, 'score': float}, ...]
    """
    if not liked_vectors:
        return []

    # Simple average — không dùng alpha/beta
    profile = np.mean(np.vstack(liked_vectors), axis=0).astype(np.float32)

    sims = cosine_similarity_matrix(profile, all_vectors)

    exclude_set = set(exclude_ids or [])
    results = [
        {"movie_id": int(mid), "score": float(score)}
        for mid, score in zip(all_movie_ids, sims)
        if int(mid) not in exclude_set
    ]
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
```

---

## Task 4.3 — Hoàn thiện `ai/neural_network.py`

> Sửa để dùng `SGDClassifier` của scikit-learn với `partial_fit` (đúng như spec báo cáo), thay vì implement gradient descent thủ công.

```python
"""
ai/neural_network.py
---------------------
Tier 2 Neural Network: dùng SGDClassifier (logistic regression với SGD)
từ scikit-learn, học online từ Like/Dislike history.

KHÔNG thay thế Tier 1 (cosine similarity + ranking).
Chỉ re-score lại candidates từ Tier 1 để tinh chỉnh thêm.

Cách dùng:
    1. Sau khi có đủ interaction data (ít nhất 5-10 like/dislike)
    2. Train model với fit_from_interactions()
    3. Dùng rerank_with_nn() để re-score candidates từ Tier 1
"""

import numpy as np
from sklearn.linear_model import SGDClassifier
import pickle, os


class OnlineNeuralRanker:
    """
    Logistic Regression online learner dùng SGDClassifier.
    partial_fit() cho phép học từng batch nhỏ (mỗi lần like/dislike).
    """

    MODEL_PATH = "nn_ranker.pkl"

    def __init__(self, n_features: int):
        self.n_features = n_features
        self.model = SGDClassifier(
            loss="log_loss",        # logistic regression
            learning_rate="optimal",
            random_state=42,
            max_iter=1,             # partial_fit sẽ gọi nhiều lần
            warm_start=True,
        )
        self._fitted = False

    def partial_fit(self, X: np.ndarray, y: np.ndarray):
        """
        Online update: gọi mỗi khi có Like/Dislike mới.
        X: (n_samples, n_features) — feature vectors
        y: (n_samples,) — 1 = like, 0 = dislike
        """
        classes = np.array([0, 1])
        self.model.partial_fit(X, y, classes=classes)
        self._fitted = True

    def predict_scores(self, X: np.ndarray) -> np.ndarray:
        """Trả về xác suất 'like' cho mỗi candidate. Shape: (n_samples,)."""
        if not self._fitted:
            return np.zeros(X.shape[0], dtype=np.float32)
        proba = self.model.predict_proba(X)[:, 1]  # P(like)
        return proba.astype(np.float32)

    def save(self, path: str = MODEL_PATH):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str = MODEL_PATH) -> "OnlineNeuralRanker":
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)


def rerank_with_nn(
    candidates: list,
    all_vectors: np.ndarray,
    all_movie_ids: np.ndarray,
    ranker: OnlineNeuralRanker,
    blend_alpha: float = 0.3,  # weight của NN score vs Tier-1 score
) -> list:
    """
    Blend Tier-1 score với NN score:
        final_score = (1 - alpha) * tier1_score + alpha * nn_score

    Parameters
    ----------
    candidates : list of dict từ rank_candidates() — đã có 'score' và 'movie_id'
    blend_alpha : 0 = ignore NN, 1 = only NN
    """
    if not ranker._fitted or not candidates:
        return candidates

    mid_to_idx = {int(mid): i for i, mid in enumerate(all_movie_ids)}
    vecs = np.vstack([
        all_vectors[mid_to_idx[c["movie_id"]]]
        for c in candidates
        if c["movie_id"] in mid_to_idx
    ]).astype(np.float32)

    nn_scores = ranker.predict_scores(vecs)

    for i, c in enumerate(candidates):
        tier1 = c["score"]
        nn    = float(nn_scores[i]) if i < len(nn_scores) else 0.0
        c["score"] = (1 - blend_alpha) * tier1 + blend_alpha * nn

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates
```

---

## Task 4.4 — Tạo mới `ai/evaluation.py` ⭐ (Task quan trọng nhất của Đôn)

```python
"""
ai/evaluation.py
-----------------
Evaluation module: đo Precision@K, Recall@K, F1@K cho hệ thống gợi ý.

Workflow:
1. Tạo simulated users với sở thích rõ ràng (thích genre X, ghét genre Y)
2. Sinh interaction history giả (like/dislike một số phim)
3. Chạy cả proposed system và baseline, lấy Top-K
4. Đo Precision@K, Recall@K, F1@K — so sánh 2 approach
5. Test failure case: new user chỉ mới onboarding, chưa like/dislike

Output: bảng kết quả + in ra console
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def precision_at_k(recommended: list, relevant: set, k: int) -> float:
    """Tỉ lệ phim trong Top-K mà user thực sự sẽ thích."""
    topk = [r["movie_id"] for r in recommended[:k]]
    hits = sum(1 for mid in topk if mid in relevant)
    return hits / k if k > 0 else 0.0


def recall_at_k(recommended: list, relevant: set, k: int) -> float:
    """Tỉ lệ phim thích được xuất hiện trong Top-K."""
    topk = [r["movie_id"] for r in recommended[:k]]
    hits = sum(1 for mid in topk if mid in relevant)
    return hits / len(relevant) if relevant else 0.0


def f1_at_k(recommended: list, relevant: set, k: int) -> float:
    p = precision_at_k(recommended, relevant, k)
    r = recall_at_k(recommended, relevant, k)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# ---------------------------------------------------------------------------
# Simulated User
# ---------------------------------------------------------------------------

@dataclass
class SimulatedUser:
    user_id: str
    preferred_genres: list      # ['Action', 'Sci-Fi']
    disliked_genres: list       # ['Horror', 'Romance']
    n_likes: int = 10           # số phim like trong training set
    n_dislikes: int = 5


def create_simulated_users() -> list:
    """
    Tạo tập user giả lập đa dạng cho evaluation.
    Mỗi user có sở thích rõ ràng để dễ đo độ chính xác.
    """
    return [
        SimulatedUser("eval_action_fan",
                      preferred_genres=["Action", "Adventure"],
                      disliked_genres=["Romance", "Musical"]),
        SimulatedUser("eval_drama_fan",
                      preferred_genres=["Drama", "Biography"],
                      disliked_genres=["Horror", "Thriller"]),
        SimulatedUser("eval_scifi_fan",
                      preferred_genres=["Science Fiction", "Fantasy"],
                      disliked_genres=["Comedy", "Family"]),
        SimulatedUser("eval_comedy_fan",
                      preferred_genres=["Comedy", "Animation"],
                      disliked_genres=["War", "Crime"]),
    ]


def _movies_by_genre(metadata_map: dict, genres: list, n: int, exclude: set = None) -> list:
    """Lấy n phim có genre thuộc list genres (dùng để build training set)."""
    genre_set = set(genres)
    result = []
    for mid, meta in metadata_map.items():
        if exclude and mid in exclude:
            continue
        if genre_set & set(meta.get("genres", [])):
            result.append(mid)
        if len(result) >= n * 5:   # lấy nhiều hơn để shuffle
            break
    np.random.shuffle(result)
    return result[:n]


# ---------------------------------------------------------------------------
# Main Evaluation Runner
# ---------------------------------------------------------------------------

def run_evaluation(
    all_movie_ids: np.ndarray,
    all_vectors: np.ndarray,
    metadata_map: dict,
    proposed_system: Callable,    # fn(liked_vecs, disliked_vecs, exclude) -> list of dict
    baseline_system: Callable,    # fn(liked_vecs, exclude) -> list of dict
    k: int = 10,
    seed: int = 42,
) -> dict:
    """
    Chạy evaluation đầy đủ.

    Parameters
    ----------
    proposed_system : callable
        Signature: (liked_vectors, disliked_vectors, exclude_ids) -> list[dict]
    baseline_system : callable
        Signature: (liked_vectors, exclude_ids) -> list[dict]
    k : int
        K trong Precision@K, Recall@K, F1@K

    Returns
    -------
    dict với keys: 'proposed', 'baseline', 'per_user'
    """
    np.random.seed(seed)
    simulated_users = create_simulated_users()

    results = {
        "proposed": {"precision": [], "recall": [], "f1": []},
        "baseline": {"precision": [], "recall": [], "f1": []},
        "per_user": {},
    }

    for user in simulated_users:
        # --- Build training set (phim đã like/dislike) ---
        liked_ids = _movies_by_genre(metadata_map, user.preferred_genres, user.n_likes)
        disliked_ids = _movies_by_genre(
            metadata_map, user.disliked_genres, user.n_dislikes,
            exclude=set(liked_ids),
        )

        liked_vecs = [all_vectors[np.where(all_movie_ids == mid)[0][0]]
                      for mid in liked_ids if mid in all_movie_ids]
        disliked_vecs = [all_vectors[np.where(all_movie_ids == mid)[0][0]]
                         for mid in disliked_ids if mid in all_movie_ids]

        # --- Ground truth: phim chưa được dùng trong training, cùng genre ---
        trained_set = set(liked_ids + disliked_ids)
        ground_truth_ids = _movies_by_genre(
            metadata_map, user.preferred_genres, n=50, exclude=trained_set
        )
        relevant = set(ground_truth_ids)

        exclude_ids = list(trained_set)

        # --- Run proposed system ---
        proposed_recs = proposed_system(liked_vecs, disliked_vecs, exclude_ids)
        p_p = precision_at_k(proposed_recs, relevant, k)
        r_p = recall_at_k(proposed_recs, relevant, k)
        f_p = f1_at_k(proposed_recs, relevant, k)

        # --- Run baseline system ---
        baseline_recs = baseline_system(liked_vecs, exclude_ids)
        p_b = precision_at_k(baseline_recs, relevant, k)
        r_b = recall_at_k(baseline_recs, relevant, k)
        f_b = f1_at_k(baseline_recs, relevant, k)

        results["proposed"]["precision"].append(p_p)
        results["proposed"]["recall"].append(r_p)
        results["proposed"]["f1"].append(f_p)
        results["baseline"]["precision"].append(p_b)
        results["baseline"]["recall"].append(r_b)
        results["baseline"]["f1"].append(f_b)

        results["per_user"][user.user_id] = {
            "proposed": {"precision@k": p_p, "recall@k": r_p, "f1@k": f_p},
            "baseline": {"precision@k": p_b, "recall@k": r_b, "f1@k": f_b},
        }

    # Average across users
    for sys in ("proposed", "baseline"):
        for metric in ("precision", "recall", "f1"):
            vals = results[sys][metric]
            results[sys][f"avg_{metric}"] = float(np.mean(vals))

    return results


def run_cold_start_test(
    all_movie_ids: np.ndarray,
    all_vectors: np.ndarray,
    metadata_map: dict,
    proposed_system: Callable,
    selected_genres: list,        # genre user chọn lúc onboarding
    genre_labels: list,
    total_dims: int,
    k: int = 10,
) -> dict:
    """
    Failure case: user mới chỉ onboarding, chưa like/dislike gì.
    Kiểm tra xem Ranking có trả kết quả hợp lý không.

    Kết quả hợp lý = ít nhất X% phim trong Top-K thuộc genre user đã chọn.
    """
    from ai.user_profile import make_genre_profile_vector, build_initial_profile_from_genres
    from ai.similarity import top_k_similar
    from ai.ranking import rank_candidates

    genre_vec = make_genre_profile_vector(selected_genres, genre_labels, total_dims)
    profile = build_initial_profile_from_genres(genre_vec)

    candidates = top_k_similar(profile, all_movie_ids, all_vectors, k=k * 3)
    recs = rank_candidates(candidates, metadata_map, top_n=k)

    # Đo: bao nhiêu phim trong Top-K thuộc genre user chọn
    genre_set = set(selected_genres)
    hits = 0
    for rec in recs[:k]:
        meta = metadata_map.get(rec["movie_id"], {})
        if genre_set & set(meta.get("genres", [])):
            hits += 1

    genre_match_rate = hits / k if k > 0 else 0.0

    print(f"\n[Cold-Start Test] Genres: {selected_genres}")
    print(f"  Top-{k} recommendations genre match rate: {genre_match_rate:.0%}")
    for rec in recs[:k]:
        meta = metadata_map.get(rec["movie_id"], {})
        print(f"  - {meta.get('title', '?')} | genres: {meta.get('genres', [])} | score: {rec['score']:.3f}")

    return {"genre_match_rate": genre_match_rate, "recommendations": recs}


def print_evaluation_report(results: dict, k: int):
    """In bảng kết quả ra console."""
    print(f"\n{'='*60}")
    print(f"  EVALUATION REPORT — Precision/Recall/F1 @{k}")
    print(f"{'='*60}")
    print(f"{'Metric':<20} {'Proposed':>12} {'Baseline':>12} {'Δ':>10}")
    print(f"{'-'*60}")
    for metric in ("precision", "recall", "f1"):
        p = results["proposed"][f"avg_{metric}"]
        b = results["baseline"][f"avg_{metric}"]
        delta = p - b
        sign = "+" if delta >= 0 else ""
        print(f"  {metric.capitalize()+'@K':<18} {p:>12.4f} {b:>12.4f} {sign+f'{delta:.4f}':>10}")
    print(f"{'='*60}\n")
```

---

## Task 4.5 — Tạo `evaluate.py` (script chạy evaluation)

```python
"""
evaluate.py
------------
Script chạy evaluation end-to-end. Chạy sau khi movies.db đã được build.

Usage:
    python evaluate.py --db movies.db --k 10
"""

import argparse
import numpy as np

from database.database import get_all_vectors, get_all_metadata, DEFAULT_DB_PATH
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

    # Cold-start test
    # (cần feature_info.json từ main.py — load genre_labels và total_dims)
    import json, os
    if os.path.exists("feature_info.json"):
        with open("feature_info.json") as f:
            fi = json.load(f)
        run_cold_start_test(
            all_ids, all_vecs, metadata,
            proposed_system=proposed,
            selected_genres=["Action", "Adventure"],
            genre_labels=fi["genre_labels"],
            total_dims=fi["total_dims"],
            k=args.k,
        )


if __name__ == "__main__":
    main()
```

---

---

# 📋 Thứ tự ưu tiên thực thi

## Sơn — thứ tự code:
```
1. [NGAY] ai/user_profile.py       — sửa công thức α/β (30 phút)
2. [NGAY] database/database.py     — thêm user_profiles table + save/load (30 phút)
3. [NGAY] services/profile_service.py — tạo mới (1 giờ)
4. [SAU]  api/feedback.py          — thêm update profile call (15 phút)
5. [SAU]  services/recommendation_service.py — dùng profile_service (30 phút)
6. [SAU]  api/onboarding.py        — tạo mới (45 phút)
7. [SAU]  main.py                  — export feature_info.json (15 phút)
8. [CUỐI] tests/mock_data.py       — mock để test độc lập
```

## Đôn — thứ tự code:
```
1. [NGAY] ai/ranking.py            — thêm vote_average vào blended (30 phút)
2. [NGAY] ai/baseline.py           — tạo mới (45 phút)
3. [NGAY] ai/evaluation.py         — tạo mới (2-3 giờ, task lớn nhất)
4. [NGAY] evaluate.py              — script runner (30 phút)
5. [SAU]  ai/neural_network.py     — rewrite với SGDClassifier (1 giờ)
6. [CUỐI] integrate NN vào pipeline (optional)
```

---

# ⚠️ Điều cần thống nhất với cả team

| Vấn đề | Người liên quan | Cần quyết định |
|--------|-----------------|----------------|
| `feature_info.json` path | Sơn + Đôn + Chuyên | Lưu ở root? Hay hardcode vào DB? |
| `genre_labels` format | Sơn + Võ | Võ cần gửi genre names đúng format khi onboarding |
| API endpoint list | Sơn + Võ + Đôn | POST /api/onboarding, POST /api/feedback, GET /api/recommendations |
| DB path mặc định | Tất cả | `movies.db` ở root — cần nhất quán |
| `candidate_pool` mặc định | Sơn + Đôn | 50 candidates từ Cosine trước khi rank — ok? |

---

# 🔌 Interface Contract (API giữa các phần)

```python
# Sơn xuất sang Đôn:
candidates: list[dict]  = [
    {"movie_id": 123, "score": 0.87},  # score = cosine similarity
    ...
]   # Top-50, sorted desc

# Đôn trả về cho Võ (qua recommendation_service):
recommendations: list[dict] = [
    {
        "movie_id": 123,
        "title": "Inception",
        "genres": ["Action", "Sci-Fi"],
        "score": 0.76,           # blended final score
        "sim_score": 0.87,       # cosine similarity gốc
        "vote_average": 8.8,
        "popularity": 120.5,
        "release_date": "2010-07-16",
    },
    ...
]   # Top-10, sorted desc

# Võ gửi vào hệ thống:
# POST /api/onboarding  → body: {user_id, selected_genres: ["Action", "Comedy"]}
# POST /api/feedback    → body: {user_id, movie_id, action: "like"|"dislike"}
# GET  /api/recommendations/{user_id}?top_n=10
```
