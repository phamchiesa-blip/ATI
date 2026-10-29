# Gu Phim: hệ thống gợi ý phim (AI Movie Recommendation System) - tên lỏ thì đổi sau nha

Ứng dụng web gợi ý phim cá nhân hóa dựa trên nội dung phim (content-based) và phản hồi Thích / Không thích của người dùng.
Dữ liệu phim: **TMDB 5000 Movie Dataset**.

- **Giao diện:** React + Vite + Tailwind (`movie-ui/`)
- **API:** FastAPI (`api.py`), gọi lại code của cả nhóm: `data_module/`, `recommendation/`, `ranking_eval/`
- **Dữ liệu:** SQLite (`movies.db` cho phim, `accounts.db` cho tài khoản, cả hai tự tạo trên máy mỗi người)

## Cấu trúc thư mục

```
ATI/
├── api.py                  # API cho giao diện (FastAPI)
├── tmdb_client.py          # gọi TMDB lấy poster / trailer (tùy chọn)
├── fetch_tmdb_posters.py   # tải poster + trailer cho toàn bộ phim (tùy chọn)
├── requirements.txt    # thư viện Python
├── data_module/            # phần Data: làm sạch dữ liệu, tạo vector phim
│   └── src/build_dataset.py
├── recommendation/         # phần Recommendation Core: user profile, cosine
├── ranking_eval/           # phần Ranking, Neural Network, Evaluation
└── movie-ui/               # giao diện React
```

## Yêu cầu

- **Python 3.10 trở lên**
- **Node.js 20 trở lên** (kèm `npm`)
- Git

## Cài đặt lần đầu

### 1. Lấy code và cài thư viện Python

```bash
git clone https://github.com/phamchiesa-blip/ATI.git
cd ATI

# (khuyên dùng) môi trường ảo
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 2. Tải dữ liệu phim

Tải **TMDB 5000 Movie Dataset** trên Kaggle, lấy 2 file `tmdb_5000_movies.csv` và `tmdb_5000_credits.csv`
rồi đặt vào thư mục `data_module/`. (Hai file này không nằm trong repo vì khá nặng. Giữ nguyên tên file,
API sẽ tự tìm thấy chúng để lấy thêm thời lượng, diễn viên, từ khóa cho trang chi tiết phim.)

### 3. Tạo cơ sở dữ liệu `movies.db` (chỉ cần làm 1 lần)

```bash
cd data_module/src
python build_dataset.py --movies ../tmdb_5000_movies.csv --credits ../tmdb_5000_credits.csv --db movies.db
cd ../..
```

Chạy khoảng 10 giây, ra file `data_module/src/movies.db` (4772 phim).

### 4. Cài thư viện cho giao diện

```bash
cd movie-ui
npm install
cd ..
```

## Chạy ứng dụng

Mở **2 cửa sổ terminal** (đều ở thư mục gốc `ATI/`, nhớ kích hoạt môi trường ảo ở cửa sổ chạy API):

```bash
# Terminal 1: API (phải chạy từ thư mục gốc)
uvicorn api:app --reload --port 8000

# Terminal 2: giao diện
cd movie-ui
npm run dev
```

Mở trình duyệt tại **http://localhost:5173**. Tài liệu API tự động ở http://localhost:8000/docs.

## Poster và trailer thật (tùy chọn)

Mặc định phim hiển thị bằng poster chữ có màu theo thể loại và nút Trailer mở tìm kiếm YouTube.
Muốn có poster thật và phát trailer ngay trong trang, cần **TMDB API key miễn phí**
(đăng ký tại themoviedb.org, vào Settings, rồi API):

```powershell
$env:TMDB_API_KEY="khoa_cua_ban"        # Windows PowerShell
# export TMDB_API_KEY=khoa_cua_ban      # macOS / Linux
python fetch_tmdb_posters.py            # khoảng 5 phút, có thể dừng và chạy lại
```

Sau đó khởi động lại API. **Không commit key lên git.** Mỗi người dùng key riêng của mình.

## Tài khoản

- **Không có tài khoản mặc định** (không có sẵn kiểu user/123). Vào web là dùng được ngay với tư cách **khách**.
- Bấm **Đăng ký** để tạo tài khoản: email hợp lệ, tên hiển thị 2 đến 30 ký tự, mật khẩu ít nhất 8 ký tự gồm cả chữ và số
  (không quá phổ biến, không chứa phần đầu email). Khách đăng ký sẽ giữ nguyên thể loại và phim đã đánh giá.
- Sai mật khẩu 5 lần liên tiếp thì email đó bị khóa 5 phút.
- Tài khoản lưu trong file `accounts.db` **trên máy của bạn**, nên mỗi người chạy ứng dụng có dữ liệu tài khoản riêng.

## Các endpoint chính

| Quyền | Endpoint |
|---|---|
| Công khai | `GET /api/movies`, `/api/movies/{id}`, `/api/movies/{id}/similar`, `/api/movies/{id}/trailer`, `/api/genres`, `/api/suggest`, `/api/showcase` |
| Tạo phiên | `POST /api/auth/guest`, `/api/auth/register`, `/api/auth/login` |
| Cần đăng nhập (khách hoặc thành viên) | `GET /api/auth/me`, `POST /api/auth/logout`, `GET/POST /api/onboarding`, `POST /api/feedback`, `GET /api/recommendations`, `GET /api/history`, `DELETE /api/me/profile` |

Các endpoint cần đăng nhập đọc danh tính từ header `Authorization: Bearer <token>`; `user_id` luôn lấy từ token, không nhận từ client.

## Cho bạn bè dùng chung trong mạng LAN (demo)

Máy chủ (người chạy API) lấy địa chỉ IP, ví dụ `192.168.1.10`:

```powershell
$env:CORS_ORIGINS="http://192.168.1.10:5173"
uvicorn api:app --host 0.0.0.0 --port 8000
cd movie-ui
# tạo file movie-ui/.env.local với nội dung:  VITE_API_URL=http://192.168.1.10:8000
npm run dev -- --host
```

Bạn bè mở `http://192.168.1.10:5173`. (Có thể phải cho phép Python/Node qua tường lửa Windows.)
Muốn người ngoài mạng dùng được thì cần đưa API và giao diện lên một máy chủ (deploy), việc này chưa nằm trong phạm vi hiện tại.

## Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| "Chưa kết nối được máy chủ" | API chưa chạy, hoặc chạy khác cổng 8000 (đặt `VITE_API_URL` trong `movie-ui/.env.local`) |
| `Failed to resolve import "lucide-react"` | Chưa cài thư viện giao diện: chạy `npm install` trong `movie-ui/` |
| `ModuleNotFoundError: ranking_eval` | Phải chạy `uvicorn api:app` từ thư mục gốc `ATI/` |
| Không thấy `movies.db` | Chưa chạy bước 3, hoặc đặt biến `MOVIES_DB` trỏ tới file |
| Trang chi tiết thiếu thời lượng, diễn viên, từ khóa | Chưa đặt 2 file CSV vào `data_module/` (hoặc đặt `TMDB_MOVIES_CSV`, `TMDB_CREDITS_CSV`) |
| Lỗi CORS trong console trình duyệt | Giao diện đang chạy ở địa chỉ không phải localhost: đặt `CORS_ORIGINS` |
| Poster thật chưa hiện sau khi tải | Khởi động lại API (hoặc đợi tối đa 1 phút) |

## Làm việc nhóm với Git

- Không commit: `movies.db`, `accounts.db`, file CSV, `node_modules/`, `__pycache__/`, `.env`, TMDB key (đã có trong `.gitignore`).
- Nếu đã lỡ commit các file `.pyc` hoặc `__pycache__/`, gỡ khỏi git bằng: `git rm -r --cached .` rồi `git add .` và commit lại.
- Sau mỗi lần `git pull`, nếu `movie-ui/package.json` thay đổi thì chạy lại `npm install`.

## Nhóm thực hiện

Kiều Huy Đôn, Nguyễn Trịnh Võ, Phạm Chuyên, Nguyễn Thái Sơn.