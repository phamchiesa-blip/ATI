# AI Movie Recommendation

Hệ thống gợi ý phim dựa trên AI, sử dụng Content-Based Filtering với Cosine Similarity.

## Cấu trúc dự án

```
ATI/
│
├── main.py                          # Chạy pipeline xây dựng database
├── evaluate.py                      # Chạy evaluation Precision/Recall/F1@K
│
├── backend/
│   ├── api/
│   │   ├── auth.py                  # Route: đăng ký / đăng nhập
│   │   ├── movies.py                # Route: tìm phim, xem chi tiết
│   │   ├── feedback.py              # Route: like / dislike
│   │   ├── onboarding.py            # Route: onboarding chọn genre
│   │   └── recommendations.py      # Route: lấy gợi ý
│   │
│   ├── models/
│   │   ├── user.py                  # Data model: User
│   │   ├── movie.py                 # Data model: Movie
│   │   └── feedback.py             # Data model: Feedback
│   │
│   ├── services/
│   │   ├── auth_service.py          # Logic: xác thực người dùng
│   │   ├── movie_service.py         # Logic: tìm kiếm, phim phổ biến
│   │   ├── profile_service.py       # Logic: quản lý User Profile (onboarding/like/dislike)
│   │   └── recommendation_service.py # Logic: gọi AI pipeline
│   │
│   └── database/
│       └── database.py              # SQLite: lưu/đọc dữ liệu, API chung
│
├── ai/
│   ├── preprocessing.py             # Bước 1: đọc CSV, làm sạch dữ liệu
│   ├── feature_engineering.py       # Bước 2: xây vector đặc trưng
│   ├── tfidf.py                     # TF-IDF + SVD cho overview
│   ├── user_profile.py              # Xây dựng User Profile từ like/dislike
│   ├── similarity.py                # Cosine Similarity
│   ├── ranking.py                   # Re-ranking: similarity + rating + popularity + recency
│   ├── baseline.py                  # Baseline: average profile, không re-rank
│   ├── neural_network.py            # Tier 2: SGDClassifier online learner
│   ├── evaluation.py                # Evaluation: Precision/Recall/F1@K + simulated users
│   └── recommender.py              # Orchestrator: profile -> similarity -> ranking
│
├── data/
│   └── movies.csv                   # Đặt file TMDB CSV ở đây
│
├── tests/
│   └── mock_data.py                 # Dữ liệu giả để test khi chưa có movies.db
│
├── frontend/                        # React project
│
├── requirements.txt
└── README.md
```

## Cách dùng

### 1. Chuẩn bị dữ liệu

Tải 2 file CSV từ Kaggle **TMDB 5000 Movie Dataset**:
- `tmdb_5000_movies.csv`
- `tmdb_5000_credits.csv`

Đặt vào thư mục `data/`.

### 2. Xây dựng database (chạy 1 lần)

```bash
pip install -r requirements.txt

python main.py \
    --movies data/tmdb_5000_movies.csv \
    --credits data/tmdb_5000_credits.csv \
    --db movies.db
```

Pipeline sẽ tạo file `movies.db` (SQLite) chứa:
- **`movies`**: thông tin phim (title, genres, director, cast, rating...)
- **`movie_feature_vectors`**: vector đặc trưng (genre + director + cast + TF-IDF + numeric)
- **`user_interaction_history`**: bảng ghi like/dislike
- **`user_profiles`**: vector User Profile đã persist (khởi tạo từ onboarding, cập nhật mỗi like/dislike)

### 3. API cho các module khác

```python
from backend.database.database import (
    get_movie_vector,        # vector của 1 phim
    get_all_vectors,         # toàn bộ vector (dùng cho Cosine Similarity)
    get_movie_metadata,      # thông tin hiển thị (title, genres, rating...)
    log_interaction,         # ghi Like/Dislike
    get_user_interactions,   # lịch sử Like/Dislike của 1 user
)

from backend.services.recommendation_service import recommend_for_user

recs = recommend_for_user(user_id="user123", top_n=10, db_path="movies.db")
```

### 4. Kiểm tra chất lượng vector

Cosine Similarity giữa *Iron Man* và *Iron Man 2* ~ **0.83**, trong khi giữa *Iron Man* và phim không liên quan ~ **0.33** — vector phản ánh đúng nội dung phim.

## Module AI

| File | Chức năng |
|------|-----------|
| `preprocessing.py` | Đọc 2 CSV, merge, làm sạch, parse cột JSON |
| `feature_engineering.py` | Xây vector (genre, director, cast, overview, numeric) |
| `tfidf.py` | TF-IDF + SVD cho phần overview |
| `user_profile.py` | Tổng hợp profile user từ lịch sử like/dislike (α=1.0, β=0.5) + init từ genre onboarding |
| `similarity.py` | Cosine Similarity giữa profile và toàn bộ phim |
| `ranking.py` | Re-rank theo similarity + rating + popularity + recency + diversity |
| `baseline.py` | Baseline: average profile, sort cosine, không re-rank (để so sánh) |
| `recommender.py` | Orchestrator: gọi toàn bộ pipeline AI |
| `neural_network.py` | Tier 2: SGDClassifier online learner (partial_fit), re-score Tier-1 |
| `evaluation.py` | Simulated users, Precision/Recall/F1@K, cold-start test |
