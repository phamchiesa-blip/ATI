# Hệ Thống Gợi Ý Phim (Movie Recommendation System)

Hệ thống gợi ý phim cá nhân hóa dựa trên nội dung (**Content-Based Filtering**), kết hợp **Xếp hạng đa mục tiêu (Multi-Objective Ranking)**, **Học trực tuyến (Online Model Reranking)**, **Trợ lý AI gợi ý phim theo ngữ cảnh** và khả năng **tự động đồng bộ phim mới từ TMDB API** mà không làm thay đổi không gian vector 324 chiều.

---

## 1. Tính Năng Nổi Bật

- **Biểu diễn phim bằng Vector 324 chiều:** Kết hợp 20 thể loại (multi-hot), 50 đạo diễn phổ biến + Other (one-hot), 200 diễn viên phổ biến (multi-hot), 50 chiều TF-IDF + SVD từ nội dung tóm tắt, và 3 tín hiệu số chuẩn hóa (`vote_average`, `popularity`, `release_year`).
- **Luồng gợi ý cá nhân hóa 3 tầng:**
  - **Tầng 0 (Core Content-Based):** Cập nhật `UserProfile` theo tương tác Like/Dislike ($\alpha, \beta$) và tính độ tương đồng Cosine.
  - **Tầng 1 (Multi-Objective Ranking):** Kết hợp trọng số Cosine Similarity (`0.6`), Rating (`0.2`), Popularity (`0.1`) và Newness (`0.1`).
  - **Tầng 2 (Online Reranking):** Mô hình Online SGD Logistic Regression (`logit_minmax`) học trực tiếp từ phản hồi của người dùng.
- **Trợ lý AI ("Hôm nay xem gì?"):** Phân tích ý định tự nhiên bằng tiếng Việt/Anh (hỗ trợ Google Gemini / OpenAI hoặc chế độ cục bộ không cần API key) để gợi ý phim phù hợp.
- **Đồng bộ phim mới từ TMDB API (`2017–2026`):** Tự động cập nhật phim đang chiếu, xu hướng hoặc theo từng năm vào `movies.db` (kèm poster, trailer YouTube và bản dịch tóm tắt tiếng Việt `overview_vi`) bằng `IncrementalVectorizer324D` — **giữ cố định 100% hệ trục 324 chiều**, không làm lệch hồ sơ người dùng hiện có.
- **Giao diện Web hiện đại:** Xây dựng trên **React 19 + Vite + Tailwind CSS v4 + Framer Motion**, hỗ trợ đăng ký/đăng nhập, onboarding chọn gu phim, tìm kiếm & lọc nâng cao, xem trailer, phim tương tự và bảng điều khiển đánh giá.

---

## 2. Yêu Cầu Hệ Thống

- **Python:** `3.10` trở lên (đã kiểm thử tốt trên Python `3.10 – 3.14`).
- **Node.js:** `18.0` trở lên và `npm` (cho giao diện web trong `movie-ui/`).

---

## 3. Cài Đặt & Khởi Chạy

### Bước 1: Tạo môi trường ảo và cài thư viện Python

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS (Bash):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Bước 2: Cấu hình biến môi trường `.env` (Tùy chọn)

Hệ thống vẫn hoạt động bình thường khi không có API key (dùng poster placeholder SVG, trailer tìm kiếm YouTube và chatbot cục bộ). Để bật đầy đủ tính năng AI và TMDB:

1. Sao chép file mẫu `.env.example` thành `.env` ở thư mục gốc:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Điền các khóa vào `.env`:
   - `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`): dùng cho trợ lý AI gợi ý phim.
   - `TMDB_API_KEY`: dùng để tải poster, trailer YouTube, tóm tắt tiếng Việt và đồng bộ phim mới từ TMDB.

### Bước 3: Khởi tạo cơ sở dữ liệu nền `movies.db` (Chỉ cần chạy 1 lần)

> **Lưu ý:** Nếu trong dự án đã có sẵn file `data_module/src/movies.db`, bạn có thể bỏ qua bước này.

1. Tải bộ dữ liệu **TMDB 5000 Movie Dataset** từ [Kaggle](https://www.kaggle.com/datasets/tmdb/tmdb-5000-movie-dataset).
2. Đặt 2 file `tmdb_5000_movies.csv` và `tmdb_5000_credits.csv` vào thư mục `data/`.
3. Chạy pipeline trích xuất đặc trưng 324 chiều để tạo `movies.db`:
   ```bash
   python data_module/src/build_dataset.py --movies data/tmdb_5000_movies.csv --credits data/tmdb_5000_credits.csv --db data_module/src/movies.db
   ```

*(Bộ dữ liệu TMDB 5000 đóng vai trò kho phim nền ~4.800 phim và định nghĩa hệ trục tọa độ 324 chiều ban đầu để các lần đồng bộ phim mới từ TMDB API chiếu vào cùng không gian vector.)*

### Bước 4: Khởi chạy Backend API (FastAPI)

```bash
python -m uvicorn api:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

> Khi khởi động, nếu phát hiện `movies.db` có ít hơn 30 phim từ năm `2018` trở đi, backend sẽ tự động chạy tác vụ nền đồng bộ thêm phim mới (`2017–2026`) từ TMDB API.

### Bước 5: Khởi chạy Frontend UI (React + Vite)

Mở một terminal mới:

```bash
cd movie-ui
npm install
npm run dev
```

- Giao diện Web: `http://localhost:5173`

---

## 4. Đồng Bộ Phim Mới & Tiện Ích Dữ Liệu

### Đồng bộ phim mới từ TMDB API

- **Qua CLI (`data_module/src/sync_tmdb.py`):**
  ```bash
  # Cập nhật phim đang chiếu, phổ biến, xu hướng
  python data_module/src/sync_tmdb.py --mode recent --limit 40

  # Quét phim nổi bật theo từng năm
  python data_module/src/sync_tmdb.py --mode years --start-year 2017 --end-year 2026 --per-year 15

  # Đồng bộ theo danh sách TMDB ID cụ thể
  python data_module/src/sync_tmdb.py --mode ids --ids 299534,299536,157336
  ```
- **Qua API:** Gọi `POST /api/movies/sync-tmdb` (hỗ trợ tham số `mode`, `start_year`, `end_year`, `per_year`, `limit`, `force`).

### Tải trước Poster & Dịch tóm tắt tiếng Việt (Tùy chọn)

```bash
# Tải sẵn poster và trailer vào cache accounts.db
python scripts/fetch_tmdb_posters.py

# Dịch tóm tắt phim sang tiếng Việt
python scripts/translate_overviews.py
```

---

## 5. Kiểm Thử & Đánh Giá Hiệu Năng

### Chạy bộ kiểm thử tự động

Chạy trực tiếp từ thư mục gốc:

```bash
# 1. Kiểm thử logic cốt lõi (không cần DB): cập nhật UserProfile, Cosine Similarity, Top-K
python recommendation/test_offline.py

# 2. Kiểm thử tích hợp trực tiếp trên movies.db
python recommendation/test_online.py

# 3. Kiểm thử các ca biên: cold-start, onboarding Top-N, lọc thể loại bị Dislike
python ranking_eval/test_edge_cases.py

# 4. Kiểm thử chatbot gợi ý phim
python recommendation/test_chatbot.py
```

### Chạy Offline Benchmark

Mô phỏng 8 nhóm người dùng (Persona) qua 5 kịch bản tương tác ($m = 0 \rightarrow 10$ lượt Like/Dislike):

```bash
python -m ranking_eval.run_benchmark --reps 10
```

- Toàn bộ quá trình mô phỏng chạy trên bản sao SQLite tạm thời và tự động dọn dẹp, **không ảnh hưởng đến `movies.db` và `accounts.db` thật**.
- Kết quả kèm kiểm định thống kê Paired Bootstrap 95% CI được xuất tự động vào:
  - `ranking_eval/results/benchmark_report.md`
  - `ranking_eval/results/benchmark_summary.csv`
  - `ranking_eval/results/benchmark_detailed.csv`

---

## 6. Kiến Trúc Thư Mục Dự Án

```text
ATI/
├── api.py                        # Entrypoint FastAPI (khởi tạo DB, đăng ký routers, startup sync)
├── requirements.txt              # Danh sách thư viện Python
├── .env.example                  # Mẫu cấu hình API keys (Gemini, OpenAI, TMDB)
│
├── backend/                      # Backend theo Clean Architecture
│   ├── core/                     # config.py, database.py, security.py
│   ├── integrations/             # tmdb_client.py (giao tiếp TMDB API & dịch thuật)
│   ├── repositories/             # movie_repository.py (cache poster/overview, search index, CSV extra)
│   ├── schemas/                  # dto.py (Pydantic Request/Response models)
│   ├── services/                 # auth_service, movie_service, recommendation_service, evaluation_service
│   └── routers/                  # auth_router, movie_router, recommendation_router, evaluation_router
│
├── data/                         # Chứa bộ dữ liệu gốc TMDB 5000 (CSV)
│   ├── tmdb_5000_movies.csv
│   └── tmdb_5000_credits.csv
│
├── data_module/                  # Pipeline dữ liệu & Feature Engineering 324D
│   └── src/
│       ├── build_dataset.py      # Build movies.db ban đầu từ CSV TMDB 5000
│       ├── data_pipeline.py      # Đọc và làm sạch dữ liệu CSV
│       ├── feature_engineering.py# Trích xuất vector đặc trưng 324 chiều
│       ├── feature_store.py      # Giao tiếp SQLite movies.db
│       └── sync_tmdb.py          # Đồng bộ phim mới từ TMDB API giữ nguyên không gian 324D
│
├── recommendation/               # Thuật toán gợi ý cốt lõi (Tầng 0) & Chatbot
│   ├── user_profile.py           # Quản lý Profile vector người dùng (alpha, beta)
│   ├── similarity.py             # Tính Cosine Similarity
│   ├── recommender.py            # Public API gợi ý phim
│   ├── interaction.py            # Lưu lịch sử tương tác Like/Dislike
│   ├── chatbot.py                # Trợ lý AI phân tích ý định & gợi ý phim
│   └── test_*.py                 # Bộ test offline, online, chatbot
│
├── ranking_eval/                 # Xếp hạng đa mục tiêu (Tầng 1–2) & Benchmark
│   ├── ranking.py                # Tầng 1: Cosine + Rating + Popularity + Newness
│   ├── online_model.py           # Tầng 2: Online SGD Classifier (logit_minmax)
│   ├── integration.py            # Tích hợp luồng gợi ý 3 tầng
│   ├── frontend_service.py       # Dịch vụ cung cấp dữ liệu gợi ý cho API
│   ├── evaluation.py             # Precision@K, Recall@K, F1@K
│   ├── simulate_users.py         # Giả lập 8 Persona người dùng
│   ├── run_benchmark.py          # Chạy benchmark và xuất báo cáo
│   └── test_edge_cases.py        # Kiểm thử các trường hợp biên
│
├── scripts/                      # Script tiện ích bổ trợ
│   ├── fetch_tmdb_posters.py     # Tải trước poster & trailer từ TMDB vào cache
│   └── translate_overviews.py    # Dịch tóm tắt phim sang tiếng Việt
│
└── movie-ui/                     # Giao diện web (React 19 + Vite + Tailwind CSS v4)
    ├── package.json
    └── src/
```

---

## 7. Quy Ước Phát Triển Nhóm

1. **Quản lý nhánh:** Luôn tạo nhánh riêng từ `main` mới nhất (`git pull` trước), không push trực tiếp lên `main`.
2. **Bảo mật & Git:** Không commit API key, file `.env`, file `.db` (`movies.db`, `accounts.db`) hoặc `node_modules/`. Không dùng `git add .`, chỉ add đúng các file đã thay đổi.
3. **An toàn dữ liệu:** Không ghi dữ liệu mô phỏng vào `movies.db` hay `accounts.db` thật; mọi thí nghiệm chạy trên bản sao tạm.
4. **Kiểm thử trước khi mở PR:** Chạy `recommendation/test_offline.py`, `recommendation/test_online.py`, `ranking_eval/test_edge_cases.py` và kiểm tra trực tiếp trên giao diện web.
