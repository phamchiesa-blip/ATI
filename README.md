# Hệ Thống Gợi Ý Phim (Movie Recommendation System)

Dự án xây dựng hệ thống gợi ý phim cá nhân hóa theo nội dung (Content-Based Filtering), kết hợp kỹ thuật xếp hạng đa mục tiêu (Multi-Objective Ranking) và mô hình học trực tuyến (Online Model Reranking), đi kèm giao diện web tương tác hoàn chỉnh.

---

## 1. Yêu Cầu Hệ Thống

- **Python**: Phiên bản `3.10` trở lên (đã kiểm thử tương thích tốt với Python 3.10 – 3.14).
- **Node.js**: Phiên bản `18.0` trở lên và `npm` (dành cho giao diện web trong `movie-ui/`).

---

## 2. Hướng Dẫn Cài Đặt & Khởi Chạy (Từng Bước)

### Bước 1: Tạo môi trường ảo Python

**Trên Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Trên Linux / macOS (Bash):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Bước 2: Cài đặt các thư viện phụ thuộc

Cài đặt toàn bộ các thư viện backend cần thiết từ file `requirements.txt` duy nhất ở gốc repository:

```bash
pip install -r requirements.txt
```

*(Các thư viện chính bao gồm: `pandas`, `numpy`, `scikit-learn`, `scipy`, `fastapi`, `uvicorn[standard]`, `pydantic`).*

---

### Bước 3: Chuẩn bị dữ liệu phim TMDB 5000

1. Tải bộ dữ liệu **TMDB 5000 Movie Dataset** miễn phí từ Kaggle:
   - Link: [Kaggle - TMDB 5000 Movie Dataset](https://www.kaggle.com/datasets/tmdb/tmdb-5000-movie-dataset)
2. Giải nén lấy 2 file:
   - `tmdb_5000_movies.csv`
   - `tmdb_5000_credits.csv`
3. Đặt 2 file CSV này vào thư mục `data/` ở thư mục gốc của dự án (nếu chưa có thư mục, hãy tạo mới `data/`).

---

### Bước 4: Tạo cơ sở dữ liệu `movies.db` (Chỉ cần chạy 1 lần)

Chạy pipeline xử lý dữ liệu và trích xuất đặc trưng (feature engineering) để tạo file SQLite `movies.db`:

**Trên Windows (PowerShell):**
```powershell
python data_module/src/build_dataset.py --movies data/tmdb_5000_movies.csv --credits data/tmdb_5000_credits.csv --db data_module/src/movies.db
```

**Trên Linux / macOS (Bash):**
```bash
python data_module/src/build_dataset.py --movies data/tmdb_5000_movies.csv --credits data/tmdb_5000_credits.csv --db data_module/src/movies.db
```

> **Lưu ý**: Lệnh trên sẽ sinh ra file `data_module/src/movies.db` chứa thông tin phim và ma trận vector đặc trưng 324 chiều. Toàn bộ các module trong hệ thống đều mặc định trỏ tới đường dẫn tuyệt đối này.

---

### Bước 5: Khởi chạy Backend API (FastAPI)

Khởi động máy chủ backend tại cổng `8000`:

```bash
uvicorn api:app --reload --port 8000
```
*(hoặc `python -m uvicorn api:app --reload --port 8000`)*

- Địa chỉ API: `http://localhost:8000`
- Tài liệu tương tác Swagger UI: `http://localhost:8000/docs`

---

### Bước 6: Khởi chạy Frontend UI (React + Vite)

Mở một cửa sổ dòng lệnh (terminal) mới và khởi động giao diện người dùng:

```bash
cd movie-ui
npm install
npm run dev
```

- Giao diện web sẽ chạy tại: `http://localhost:5173`
- Mở trình duyệt và truy cập `http://localhost:5173` để trải nghiệm tìm kiếm, onboarding, xem phim tương tự và nhận gợi ý cá nhân hóa.

---

### Bước 7: Cấu hình Poster & Trailer từ TMDB (Tùy chọn)

Hệ thống được thiết kế để **hoạt động bình thường ngay cả khi không có API key** (sử dụng poster placeholder dạng SVG gradient và trailer dự phòng).

Nếu muốn tải poster và trailer chính thức từ TMDB:
1. Đăng ký tài khoản và lấy API key miễn phí tại: [TheMovieDB API Settings](https://www.themoviedb.org/settings/api).
2. Thiết lập biến môi trường `TMDB_API_KEY`:

   **Trên Windows (PowerShell):**
   ```powershell
   $env:TMDB_API_KEY="dien_khoa_cua_ban_o_day"
   ```

   **Trên Linux / macOS (Bash):**
   ```bash
   export TMDB_API_KEY="dien_khoa_cua_ban_o_day"
   ```

3. *(Tùy chọn)* Chạy script tải sẵn poster vào database cache `accounts.db`:
   ```bash
   python fetch_tmdb_posters.py
   ```

---

## 3. Chạy Kiểm Thử (Tests)

Hệ thống có 3 bộ kiểm thử tự động, có thể chạy trực tiếp từ thư mục gốc của repository:

1. **Kiểm thử logic cốt lõi (không cần database)**:
   ```bash
   python recommendation/test_offline.py
   ```
   *Kiểm tra tính đúng đắn của phép cập nhật User Profile ($\alpha, \beta$), tính toán Cosine Similarity và trích xuất Top-K.*

2. **Kiểm thử gợi ý trực tiếp trên `movies.db`**:
   ```bash
   python recommendation/test_online.py
   ```
   *Kiểm tra luồng đọc vector, like phim và sinh gợi ý trực tiếp từ cơ sở dữ liệu.*

3. **Kiểm thử các ca biên (Edge Cases)**:
   ```bash
   python ranking_eval/test_edge_cases.py
   ```
   *Kiểm tra cơ chế fallback phim phổ biến cho user mới (cold-start), chống loãng profile khi onboarding (chọn Top N), và cơ chế lọc thể loại bị ghét khi user chỉ bấm Dislike.*

---

## 4. Đánh Giá Hiệu Năng & Offline Benchmark

Hệ thống tích hợp bộ công cụ benchmark toàn diện, mô phỏng 8 nhóm người dùng (Persona) với 5 kịch bản tương tác (từ cold-start $m=0$ đến $m=10$ lượt tương tác Like/Dislike):

```bash
python -m ranking_eval.run_benchmark --reps 10
```

- Toàn bộ dữ liệu giả lập được chạy trên bản sao SQLite tạm thời trong bộ nhớ cache của hệ điều hành và tự động xóa sau khi chạy xong, đảm bảo **an toàn 100% cho `movies.db` và `accounts.db`**.
- Báo cáo phân tích chuyên sâu kèm kiểm định thống kê Paired Bootstrap 95% Confidence Interval được lưu tự động tại:
  - `ranking_eval/results/benchmark_report.md`
  - `ranking_eval/results/benchmark_summary.csv`
  - `ranking_eval/results/benchmark_detailed.csv`

---

## 5. Kiến Trúc Thư Mục Dự Án

```text
ATI/
├── api.py                    # FastAPI server cung cấp REST API cho Frontend
├── requirements.txt          # Thư viện Python phụ thuộc duy nhất của dự án
├── fetch_tmdb_posters.py     # Script tải poster & trailer từ TMDB vào cache
├── tmdb_client.py            # Client gọi API TheMovieDB
│
├── data_module/              # Module xử lý dữ liệu và trích xuất đặc trưng
│   └── src/
│       ├── build_dataset.py  # Script chạy pipeline tạo movies.db
│       ├── data_pipeline.py  # Đọc CSV, làm sạch dữ liệu
│       ├── feature_engineering.py # Xây dựng vector đặc trưng 324 chiều
│       └── feature_store.py  # Giao tiếp SQLite movies.db và kiểm tra an toàn DB
│
├── recommendation/           # Module thuật toán gợi ý cốt lõi (Tầng 0 / Part II)
│   ├── user_profile.py       # Quản lý Profile vector người dùng (alpha, beta)
│   ├── similarity.py         # Tính Cosine Similarity
│   ├── recommender.py        # Public API gợi ý phim
│   ├── interaction.py        # Lưu lịch sử tương tác Like/Dislike
│   ├── test_offline.py       # Test unit offline
│   └── test_online.py        # Test tích hợp với movies.db
│
├── ranking_eval/             # Module Xếp hạng đa mục tiêu & Đánh giá (Part III)
│   ├── ranking.py            # Tầng 1: Xếp hạng theo Cosine, Rating, Popularity, Newness
│   ├── online_model.py       # Tầng 2: Online SGD Classifier (chế độ logit_minmax)
│   ├── integration.py        # Tích hợp luồng gợi ý 3 tầng
│   ├── frontend_service.py   # Dịch vụ cung cấp dữ liệu cho API web
│   ├── evaluation.py         # Hàm tính Precision@K, Recall@K, F1@K
│   ├── simulate_users.py     # Giả lập 8 Persona người dùng
│   ├── run_benchmark.py      # Runner benchmark và xuất báo cáo markdown
│   └── test_edge_cases.py    # Test các trường hợp biên
│
└── movie-ui/                 # Giao diện web người dùng (React 18 + Vite)
    ├── package.json          # Cấu hình phụ thuộc Node.js
    └── src/                  # Mã nguồn giao diện (Browse, Recommend, Taste, Detail...)
```
<!-- python -m uvicorn api:app --reload --port 8000 -->

Lời nhắn chung cho cả nhóm (gửi kèm để AI của mỗi người có đủ ngữ cảnh)
Dự án: hệ thống gợi ý phim content-based (TMDB 5000, vector phim 324 chiều, user profile cập nhật khi Like/Dislike, ranking = Cosine 0.6 + Rating 0.2 + Popularity 0.1 + Newness 0.1, Tầng 2 là online logistic regression làm reranker). Repo: <link GitHub>.
Quy tắc: 
1. Tạo nhánh riêng từ main mới nhất (git pull trước). Không push thẳng main.
2. Không bao giờ commit API key TMDB, file .db, .env, node_modules. Dùng biến môi trường. Không dùng `git add .`, chỉ add đúng file đã sửa.
3. Không ghi dữ liệu mô phỏng vào movies.db hay accounts.db thật. Mọi thí nghiệm chạy trên bản sao tạm.
4. Trước khi mở PR: chạy recommendation/test_offline.py, recommendation/test_online.py, ranking_eval/test_edge_cases.py và chạy thử web.
5. Báo cáo trung thực: nếu thay đổi không cải thiện thì ghi rõ là không cải thiện. Không chỉnh tham số trên dữ liệu test để số đẹp hơn.

