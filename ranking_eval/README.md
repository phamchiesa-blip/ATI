# Ranking, Neural Network & Evaluation

Phần III giữ code trong thư mục riêng nhưng dùng dữ liệu thật từ hai phần
trước. `integration.py` gọi `recommend()` của Phần II để lấy Top-K cosine,
sau đó lấy rating, popularity, ngày phát hành và tên phim từ API của Phần I.
Nó không dựng profile, tính cosine hay tạo user giả.

## Giao diện gọi từ Backend/Frontend

`http_api.py` chạy HTTP server thật (dùng thư viện chuẩn Python, không cần
cài FastAPI). `frontend_service.py` chứa các hàm xử lý mà endpoint gọi.
Khởi chạy từ thư mục gốc sau khi đã build database:

```bash
python -m ranking_eval.http_api --db data_module/src/movies.db --host 127.0.0.1 --port 8000
```

Frontend chạy cùng máy có thể gọi `http://127.0.0.1:8000`. Server hỗ trợ CORS
cho phát triển local; đặt origin cụ thể bằng `--cors-origin` khi cần.

Các hàm JSON-friendly trong `frontend_service.py` là:

| Hàm service | Dùng cho | Input chính |
|---|---|---|
| `list_movies(...)` | Browse Movies | `page`, `page_size`, `genre`, `search` |
| `onboard_user(...)` | Onboarding | `user_id`, `selected_genres`, `favorite_movie_ids` tùy chọn |
| `record_interaction(...)` | Like/Dislike | `user_id`, `movie_id`, `action` |
| `recommendations(...)` | View Recommendations | `user_id`, `limit`, `candidate_k` |

HTTP endpoints có sẵn:

| HTTP | Endpoint đề xuất | Hàm gọi |
|---|---|---|
| `GET` | `/api/movies?page=1&page_size=20&genre=Comedy` | `list_movies()` |
| `POST` | `/api/users/{user_id}/onboarding` | `onboard_user()` |
| `POST` | `/api/users/{user_id}/interactions` | `record_interaction()` |
| `GET` | `/api/users/{user_id}/recommendations?limit=10` | `recommendations()` |

Onboarding body mẫu theo genre: `{"selected_genres":["Comedy"]}`. Nếu gửi
`favorite_movie_ids`, các phim đó được ưu tiên làm tín hiệu khởi tạo profile.
Interaction body mẫu: `{"movie_id":5,"action":"like"}`. Poster chưa có
trong schema hiện tại của database, nên Browse UI cần dùng placeholder cho tới
khi nhóm bổ sung poster data.

## Chạy reranking cho user thật

Trước tiên tạo database theo hướng dẫn Phần I và đảm bảo user có profile hoặc
lịch sử Like/Dislike trong Phần II. Sau đó chạy từ thư mục gốc project:

```bash
python -m ranking_eval.integration --user-id user_001 --db data_module/src/movies.db --candidate-k 100 --top-n 10
```

Phần II đưa 100 phim theo cosine; Phần III xếp lại 100 phim đó và in ra 10
phim đầu. Trọng số mặc định: cosine 0.60, rating 0.20, popularity 0.10,
newness 0.10. Nếu user đã có ít nhất một Like và một Dislike, tầng hai cũng
chấm xác suất Like; điểm cuối trộn 80% điểm ranking Tầng 1 và 20% xác suất
Like. Có thể đổi tỷ lệ bằng `--neural-weight` (đặt 0 để tắt), hoặc chỉnh
trọng số ranking qua `RankingWeights` trong `ranking.py`.

## Đánh giá chất lượng

Để tính Precision@K, Recall@K và F1@K, cần biết trước phim nào user thật sự
thích. Dùng các Like được giữ riêng để kiểm tra, chưa dùng để tạo profile:

```bash
python -m ranking_eval.integration --user-id user_001 --db data_module/src/movies.db --candidate-k 100 --top-n 10 --relevant-ids 11,28,105
```

Các ID trên chỉ minh họa định dạng. Thay bằng các `movie_id` phù hợp trong bộ
đánh giá. Nếu chưa có đáp án kiểu này, vẫn chạy được recommendation và
reranking, nhưng không thể tính metric một cách có ý nghĩa.

## Neural Network tùy chọn

`online_model.py` là thử nghiệm tầng hai dùng `SGDClassifier`. Hàm
`train_online_model_from_history(user_id, db_path)` trong `integration.py`
lấy Like/Dislike và vector thật từ feature store để train. Mô hình chỉ được
dùng khi lịch sử có cả Like và Dislike. Nếu chưa có Dislike, chương trình tự
dùng Tầng 1 và báo Neural Network chưa hoạt động.
