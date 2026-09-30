# Data & Feature Engineering — hướng dẫn dùng

Module này lo phần "Data Storage" + "Movie Feature Vector" trong kiến trúc hệ
thống (mục 4.1 báo cáo). Ba bạn còn lại (Sơn, Võ, Đôn) không cần đụng vào các
file bên trong `src/`, chỉ cần import và gọi các hàm ở cuối file này.

## 1. Chuẩn bị dữ liệu

Tải 2 file CSV từ Kaggle **TMDB 5000 Movie Dataset**:
- `tmdb_5000_movies.csv`
- `tmdb_5000_credits.csv`

Đặt vào một thư mục bất kỳ (không cần bỏ vào repo, file khá nặng).

## 2. Chạy pipeline (chỉ cần chạy 1 lần, hoặc mỗi khi dataset đổi)

```bash
cd src
pip install -r ../requirements.txt
python build_dataset.py --movies path/to/tmdb_5000_movies.csv \
                         --credits path/to/tmdb_5000_credits.csv \
                         --db movies.db
```

Lệnh trên sẽ tạo ra file `movies.db` (SQLite) chứa:
- **`movies`**: thông tin gốc của phim (title, genres, director, cast, rating, popularity, release_date) — tương ứng "Movie Dataset" + "Movie Rating" trong sơ đồ kiến trúc.
- **`movie_feature_vectors`**: vector đặc trưng đã xử lý của từng phim (324 chiều: genre + director + cast + overview (SVD) + rating/popularity/release year đã chuẩn hóa) — tương ứng "Movie Feature Vectors".
- **`user_interaction_history`**: bảng trống ban đầu, để trống cho Sơn ghi Like/Dislike của user vào.

Chạy thử trên dataset thật (4803 phim), pipeline chạy hết khoảng 7-8 giây, ra 4772 phim sau khi làm sạch (bỏ phim thiếu overview/genre).

## 3. API dùng chung (import từ `feature_store.py`)

```python
from feature_store import (
    get_movie_vector,        # lấy vector của 1 phim
    get_all_vectors,         # lấy toàn bộ vector 1 lần (dùng cho Cosine Similarity)
    get_movie_metadata,      # lấy thông tin hiển thị (title, genres, rating...)
    log_interaction,         # ghi lại 1 lượt Like/Dislike
    get_user_interactions,   # lấy lịch sử Like/Dislike của 1 user
)
```

**Cho Sơn (Recommendation Core):**
```python
vector = get_movie_vector(movie_id, db_path="movies.db")          # 1 phim
movie_ids, matrix = get_all_vectors(db_path="movies.db")          # toàn bộ, để tính Cosine Similarity
log_interaction(user_id, movie_id, "like", db_path="movies.db")   # khi user bấm Like
history = get_user_interactions(user_id, db_path="movies.db")     # để dựng lại User Profile
```

**Cho Võ (Frontend):**
```python
info = get_movie_metadata(movie_id, db_path="movies.db")
# info = {"title": ..., "genres": [...], "director": ..., "cast": [...],
#         "vote_average": ..., "popularity": ..., "release_date": ...}
```

**Cho Đôn (Ranking/NN/Evaluation):** dùng `get_movie_metadata()` để lấy `vote_average`, `popularity`, `release_date` (thô, chưa chuẩn hóa) cho bước Ranking (mục 3.7), và `get_all_vectors()` nếu cần train Neural Network.

## 4. Cấu trúc file trong `src/`

| File | Việc gì |
|---|---|
| `data_pipeline.py` | Đọc 2 CSV, merge, làm sạch, parse cột JSON (genres/cast/crew) |
| `feature_engineering.py` | Xây vector đặc trưng (genre, director, cast, overview, rating/popularity/newness) |
| `feature_store.py` | Lưu vào SQLite + toàn bộ API public ở trên |
| `build_dataset.py` | Script chạy toàn bộ pipeline, tạo `movies.db` |

## 5. Đã kiểm tra

Sanity check: độ giống nhau (Cosine Similarity) giữa *Iron Man* và *Iron Man 2* là **0.83**, trong khi giữa *Iron Man* và một phim không liên quan chỉ **0.33** — cho thấy vector đặc trưng phản ánh đúng nội dung phim.

## Có thể chỉnh sau nếu cần

- Số chiều overview (SVD), số director/cast top-K trong `FeatureConfig` (đầu file `feature_engineering.py`) — tăng lên nếu muốn vector chi tiết hơn, giảm nếu muốn nhẹ/nhanh hơn.
- Trọng số giữa các phần feature (hiện đang cộng thẳng, chưa có trọng số riêng) — nếu sau này thấy gợi ý bị lệch quá nhiều theo 1 yếu tố (ví dụ toàn theo overview), có thể nhân hệ số cho từng khối trước khi ghép.
