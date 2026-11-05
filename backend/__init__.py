"""
backend/
--------
Clean Architecture package cho Backend API cua he thong goi y phim.
Chia thanh 3 tang ro rang:
  - core/           : Cau hinh he thong, ket noi DB SQLite, bao mat & tien ich xu ly chuoi.
  - schemas/        : Cac Request/Response DTO (Pydantic models).
  - repositories/   : Truy cap du lieu (accounts.db, movies.db, CSV metadata, TMDB cache, chi muc tim kiem).
  - services/       : Nghiep vu (Use Cases): Auth, Movie Catalog, Recommendation/Profile, Tonight/Chat, Evaluation.
  - routers/        : FastAPI Presentation Layer (HTTP endpoints).
"""

