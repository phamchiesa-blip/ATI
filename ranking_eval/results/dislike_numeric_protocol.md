# Giao thức đánh giá: Dislike không trừ ba chiều số

Giao thức được chốt trước khi chạy benchmark; không tinh chỉnh tham số sau khi xem kết quả.

- Đối chiếu cũ/mới theo cặp: cùng persona, seed và phim tương tác. Chế độ mới chỉ trừ phần nội dung của vector; ba chiều cuối (Rating, Popularity, Năm phát hành) được giữ nguyên. Hành vi mặc định vẫn là cũ.
- Ca chính: onboarding theo genre, rồi 2 hoặc 3 Dislike, không Like. 10 reps cho mỗi ca/persona.
- Ca kiểm tra hỗn hợp: onboarding + 1, 3, 5 hoặc 10 Like và số Dislike lần lượt 2, 2, 3, 3, theo quy ước benchmark hiện tại.
- Seed theo benchmark: `42 + persona_index * 1000 + scenario_index * 100 + rep`. Ca hỗn hợp dùng đúng scenario index cũ (1–4); hai ca chỉ Dislike dùng index mới 5–6.
- Chỉ số: Precision@10 và rating trung bình top-10 Tầng 1. Tổng hợp reps bên trong từng persona; báo mean và CI 95% từ 5.000 lần bootstrap resample persona, cùng CI ghép cặp cho chênh lệch mới trừ cũ.
- Dữ liệu: tạo bản sao tạm của `movies.db`, không ghi tương tác mô phỏng vào DB gốc.
- `tmdb_5000_movies.csv` cung cấp `original_language` và `keywords` để dựng đủ P7/P8. Trong workspace hiện hai CSV được đặt trong `data_module/src/`; benchmark dùng đường dẫn này và chỉ tiếp tục khi cả 8 persona có relevant pool.
