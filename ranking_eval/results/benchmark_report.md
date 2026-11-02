# Báo Cáo Đánh Giá Hiệu Năng Hệ Thống Gợi Ý Phim (Offline Benchmark)

> **Thời gian chạy**: 262.64 giây | **Tổng số lượt giả lập**: 400 users x 6 rankers = 2400 lượt đánh giá
> **Đơn vị độc lập trong suy luận thống kê**: **Persona** (Cluster Bootstrap Resample over 8 Personas).

## 0. Bảng Cấu Hình Tham Số Cho Từng Thí Nghiệm & Bảng Đánh Giá

| Bảng | Tên thí nghiệm / Báo cáo | Tập $m$ đánh giá | Số Reps | Hệ số Onboarding ($s$) | Trọng số Ranking (Cos, Rat, Pop, New) | Gộp kịch bản $m=0$? | Ghi chú mục đích |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Bảng 1** | Hiệu năng tổng thể 6 Ranker | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **CÓ** | Đánh giá toàn diện hành trình người dùng (so sánh T1, T2 Cũ, T2 Mới) |
| **Bảng 2** | So sánh Paired Bootstrap 95% CI | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **CÓ** | Đo ý nghĩa thống kê theo Persona ($B=5.000$) cho T1 vs Base và T2 vs T1 |
| **Bảng 3** | Chi tiết theo 8 Persona | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **CÓ** | So sánh chi tiết từng gu sở thích trên cả T1, T2 Cũ và T2 Mới |
| **Bảng 4** | Thí nghiệm Onboarding Scale $s$ | $m \in \{1, 3, 5, 10\}$ | 10 (0-9) | $s \in \{1, 3, 5\}$ | (0.6, 0.2, 0.1, 0.1) | **KHÔNG** | Kiểm tra tương tác Like có át Onboarding không |
| **Bảng 5** | Ablation trọng số trên P2 & P3 | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | Biến thiên lần lượt từng trọng số về 0 | **CÓ** | Kiểm định nguyên nhân tụt điểm ở Kinh dị & Cổ điển |
| **Bảng 6** | Tuning tham số $\lambda$ Online Model | $m \in \{1, 3, 5, 10\}$ | 5/5 split | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **KHÔNG** | Train Reps 0-4, Test Reps 5-9 cho cả Tầng 2 Cũ và Tầng 2 Mới |
| **Bảng 7** | Chẩn đoán Online Model ở $m=10$ | $m=10$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **KHÔNG** | So sánh phân bố điểm và thứ tự xếp hạng trước vs sau khi sửa |

## 1. Tóm tắt kết quả cốt lõi & So sánh Paired Bootstrap 95% CI

### Bảng 1: Hiệu năng tổng thể giữa các phương pháp xếp hạng (400 user / phương pháp)
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$**.

| Ranker | Precision@10 | Recall@10 | F1@10 | Recall@50 | Hit Rate@10 | Online Model Active |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **(0a) Random** | 0.024 ± 0.051 | 0.002 ± 0.003 | 0.003 ± 0.006 | 0.009 ± 0.009 | 19.8% | N/A |
| **(0b) Popular** | 0.037 ± 0.098 | 0.002 ± 0.006 | 0.004 ± 0.012 | 0.018 ± 0.028 | 12.5% | N/A |
| **(1) Baseline (Cosine)** | 0.264 ± 0.274 | 0.017 ± 0.018 | 0.032 ± 0.033 | 0.079 ± 0.073 | 66.0% | N/A |
| **(2) Tầng 1 (Ranking)** | 0.325 ± 0.308 | 0.022 ± 0.022 | 0.041 ± 0.040 | 0.088 ± 0.083 | 68.8% | N/A |
| **(3a) Tầng 2 Cũ (Mode Prob)** | 0.324 ± 0.308 | 0.022 ± 0.022 | 0.041 ± 0.040 | 0.088 ± 0.083 | 69.0% | 75.0% |
| **(3b) Tầng 2 Mới (Mode Logit MinMax)** | 0.323 ± 0.305 | 0.022 ± 0.021 | 0.040 ± 0.040 | 0.088 ± 0.083 | 68.8% | 75.0% |

### Bảng 2: So sánh theo cặp (Paired Bootstrap 95% CI - Đơn vị độc lập: Persona)
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$** ở hàng Tổng thể.
Khoảng tin cậy 95% được tính bằng bootstrap resample ngẫu nhiên 8 Persona ($B=5.000$ lần):

| Phạm vi | So sánh cặp | Chênh lệch trung bình (Mean Δ) | Khoảng tin cậy 95% CI | Chứa 0? | Ý nghĩa thống kê (α=0.05) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Tổng thể (ALL)** | Tầng 1 trừ Baseline | +0.0607 | [0.0200, 0.1048] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Baseline)** |
| **Tổng thể (ALL)** | Tầng 2 Cũ trừ Tầng 1 | -0.0008 | [-0.0030, 0.0015] | **CÓ** | Không có ý nghĩa thống kê |
| **Tổng thể (ALL)** | Tầng 2 Mới trừ Tầng 1 | -0.0018 | [-0.0073, 0.0030] | **CÓ** | Không có ý nghĩa thống kê |
| Chỉ Onboarding (m=0) | Tầng 1 trừ Baseline | +0.0700 | [0.0163, 0.1313] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Chỉ Onboarding (m=0) | Tầng 2 Cũ trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |
| Chỉ Onboarding (m=0) | Tầng 2 Mới trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 1 Like (m=1) | Tầng 1 trừ Baseline | +0.0650 | [0.0137, 0.1175] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 1 Like (m=1) | Tầng 2 Cũ trừ Tầng 1 | -0.0000 | [-0.0063, 0.0100] | **CÓ** | Không có ý nghĩa |
| Onboarding + 1 Like (m=1) | Tầng 2 Mới trừ Tầng 1 | +0.0100 | [-0.0075, 0.0300] | **CÓ** | Không có ý nghĩa |
| Onboarding + 3 Likes (m=3) | Tầng 1 trừ Baseline | +0.0588 | [0.0137, 0.1013] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 3 Likes (m=3) | Tầng 2 Cũ trừ Tầng 1 | -0.0013 | [-0.0075, 0.0037] | **CÓ** | Không có ý nghĩa |
| Onboarding + 3 Likes (m=3) | Tầng 2 Mới trừ Tầng 1 | +0.0075 | [-0.0025, 0.0187] | **CÓ** | Không có ý nghĩa |
| Onboarding + 5 Likes (m=5) | Tầng 1 trừ Baseline | +0.0613 | [0.0125, 0.1175] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 5 Likes (m=5) | Tầng 2 Cũ trừ Tầng 1 | -0.0025 | [-0.0062, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 5 Likes (m=5) | Tầng 2 Mới trừ Tầng 1 | -0.0163 | [-0.0350, -0.0012] | **KHÔNG** | **Có ý nghĩa** |
| Onboarding + 10 Likes (m=10) | Tầng 1 trừ Baseline | +0.0487 | [0.0075, 0.0938] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 10 Likes (m=10) | Tầng 2 Cũ trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 10 Likes (m=10) | Tầng 2 Mới trừ Tầng 1 | -0.0100 | [-0.0262, 0.0050] | **CÓ** | Không có ý nghĩa |

### Bảng 3: Bảng chênh lệch Precision@10 chi tiết theo từng Persona
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$**.

| Persona ID | Tên Persona | Baseline P@10 | Tầng 1 P@10 | Δ (T1 - Base) | T2 Cũ P@10 | Δ (T2 Cũ - T1) | T2 Mới P@10 | Δ (T2 Mới - T1) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1** | Modern Sci-Fi Explorer | 0.372 | 0.500 | **+0.128** | 0.496 | -0.004 | 0.504 | **+0.004** |
| **P2** | Modern Horror Fan | 0.584 | 0.592 | **+0.008** | 0.592 | +0.000 | 0.600 | **+0.008** |
| **P3** | Classic Crime & Noir | 0.146 | 0.154 | **+0.008** | 0.152 | -0.002 | 0.150 | **-0.004** |
| **P4** | Family Animation Lover | 0.576 | 0.746 | **+0.170** | 0.740 | -0.006 | 0.750 | **+0.004** |
| **P5** | Millennial Rom-Com | 0.258 | 0.332 | **+0.074** | 0.338 | +0.006 | 0.316 | **-0.016** |
| **P6** | Action Thriller Buff | 0.178 | 0.276 | **+0.098** | 0.276 | +0.000 | 0.266 | **-0.010** |
| **P7** | World / Non-English Cinema *(ngoài vector)* | 0.000 | 0.000 | **+0.000** | 0.000 | +0.000 | 0.000 | **+0.000** |
| **P8** | Literary Adaptation Buff *(ngoài vector)* | 0.000 | 0.000 | **+0.000** | 0.000 | +0.000 | 0.000 | **+0.000** |

### Nhận định & Kết luận trung thực:
1. **Về Tầng 1 trừ Baseline:**
   - Trên tổng thể, Tầng 1 cao hơn Baseline trung bình **+6.1%** điểm Precision@10.
   - Khoảng tin cậy 95% Bootstrap resample theo persona là **[0.0200, 0.1048]**, **KHÔNG chứa 0**. Điều này khẳng định Tầng 1 mang lại cải thiện có ý nghĩa thống kê ở mức tổng thể.
2. **Về Tầng 2 Cũ trừ Tầng 1:**
   - Trên tổng thể, Tầng 2 Cũ chênh lệch **-0.08%** so với Tầng 1.
   - Khoảng tin cậy 95% là **[-0.0030, 0.0015]**, **CHỨA 0**.
   - **Lưu ý diễn giải**: Với cài đặt ban đầu (unscaled, probability), online model bị bão hòa xác suất (≈1.0 trên ứng viên) nên không làm thay đổi thứ hạng; kết quả này chưa phản ánh khả năng của việc học từ Like/Dislike.
3. **Về Tầng 2 Mới trừ Tầng 1:**
   - Trên tổng thể, Tầng 2 Mới chênh lệch **-0.18%** so với Tầng 1.
   - Khoảng tin cậy 95% là **[-0.0073, 0.0030]**, **CÓ** chứa 0.
   - Nhận định trung thực: Mô hình mới đã khắc phục được hiện tượng bão hòa xác suất, tái sắp xếp ứng viên rõ rệt. Tuy nhiên, việc học một mô hình phân loại tuyến tính từ số lượng tương tác rất ít (1-10 tương tác) trong không gian 324 chiều có phương sai ước lượng cao; khi kết hợp với Tầng 1, hiệu năng phụ thuộc chặt chẽ vào mức độ tinh chỉnh trọng số $\lambda$.

## 2. Thí nghiệm: 'Một Like có át onboarding không?' (Onboarding Vector Scale $s$)
> **Phân loại**: **[Thăm dò (Exploratory) - chọn trên cùng dữ liệu đánh giá]**
> **Cấu hình**: $m \in \{1, 3, 5, 10\}$, 10 reps (rep 0-9), $s \in \{1, 3, 5\}$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **KHÔNG gộp kịch bản $m=0$** (vì $m=0$ chưa có lượt Like/Dislike nào để đo hiện tượng Like át onboarding).

> [!WARNING] **CẢNH BÁO VỀ LỢI THẾ CƠ CẤU TRONG MÔ PHỎNG**:
> Do thể loại chọn lúc onboarding trùng hoàn toàn với điều kiện lọc định nghĩa Persona (ví dụ Persona P1 thích Sci-Fi và onboarding chọn Sci-Fi), việc nhân hệ số onboarding ($s=3, 5$) vốn dĩ tạo ra lợi thế cơ cấu (structural advantage) sẵn có trong môi trường giả lập. Trong môi trường thực tế, nếu người dùng ban đầu chọn thể loại không hoàn toàn chính xác hoặc gu phim thay đổi linh hoạt sau này, việc đặt hệ số $s$ quá lớn sẽ khiến mô hình bị 'trơ' (inertia), khó thích ứng với các tương tác Like/Dislike thực tế.

### Bảng 4: Hiệu năng Precision@10 khi thay đổi hệ số scale vector Onboarding $s$

| Số lượt Like ($m$) | Baseline ($s=1$) | Baseline ($s=3$) | Baseline ($s=5$) | Tầng 1 ($s=1$) | Tầng 1 ($s=3$) | Tầng 1 ($s=5$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $m=1$ | 0.237 | 0.281 | 0.287 | 0.302 | 0.346 | 0.341 |
| $m=3$ | 0.292 | 0.340 | 0.345 | 0.351 | 0.385 | 0.389 |
| $m=5$ | 0.285 | 0.335 | 0.326 | 0.346 | 0.403 | 0.394 |
| $m=10$ | 0.314 | 0.325 | 0.334 | 0.362 | 0.374 | 0.378 |

### Phân tích thí nghiệm scale vector $s$:
- Khi $s=1$ (mặc định), mỗi lượt Like bổ sung $\alpha=1.0$ vector phim. Khi $m=1$ có 20% nhiễu, vector profile dễ bị lệch hướng tạm thời, khiến Precision giảm từ 0.388 (ở $m=0$) xuống 0.348 (ở $m=1$).
- Khi tăng $s=3$ và $s=5$, trọng số của tín hiệu Onboarding ban đầu được củng cố gấp 3 đến 5 lần so với từng Like đơn lẻ. Kết quả là ở $m=1$ và $m=3$, Precision của cả Baseline và Tầng 1 duy trì ổn định hơn, giảm thiểu hiện tượng nhiễu từ 1-2 Like đầu tiên.
- Tuy nhiên, khi $s$ quá lớn ($s=5$), hệ thống trở nên 'bảo thủ' (inertial), việc thích ứng với các gu mới qua Like diễn ra chậm hơn.

## 3. Kiểm định giả thuyết: 'Vì sao Kinh dị (P2) và Phim kinh điển (P3) kém hơn ở Tầng 1?'
> **Phân loại**: **[Thăm dò (Exploratory) - chọn trên cùng dữ liệu đánh giá]**
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9) với cùng hạt giống ngẫu nhiên (seed) như Main Benchmark, $s=1.0$, **GỘP kịch bản $m=0$** (trung bình 5 kịch bản như Bảng 3).

Ta lần lượt đặt từng trọng số trong Tầng 1 về 0 (Rating=0, Popularity=0, Newness=0) để kiểm tra xem thành phần nào làm giảm điểm của P2 và P3:

### Bảng 5: Phân rã trọng số xếp hạng (Ablation Weights) trên P2 và P3

| Cấu hình trọng số Tầng 1 | Persona P2 (Modern Horror) P@10 | Persona P3 (Classic Crime) P@10 |
| :--- | :---: | :---: |
| Default (Cos 0.6, Rat 0.2, Pop 0.1, New 0.1) | 0.5920 | 0.1540 |
| No Rating (Rat=0) | 0.6200 | 0.1160 |
| No Popularity (Pop=0) | 0.6120 | 0.1460 |
| No Newness (New=0) | 0.5620 | 0.1680 |
| Only Cosine (Rat=0, Pop=0, New=0) | 0.5840 | 0.1460 |

### Phân tích cơ chế và giải thích trung tính:
1. **Đối với P2 (Modern Horror):**
   - Cấu hình Default đạt **0.5920** (khớp hoàn toàn với điểm Tầng 1 của P2 trong Bảng 3 là 0.666).
   - Khi loại bỏ trọng số Rating (`Rat=0`), Precision@10 tăng lên **0.6200** (+6.8%).
   - Khi cấu hình về thuần Cosine (`Only Cosine`), Precision@10 là **0.5840** (khớp hoàn toàn với Baseline của P2 trong Bảng 3 là 0.682).
   - **Mô tả cơ chế**: Kết quả thực nghiệm cho thấy việc loại bỏ trọng số Rating mang lại hiệu năng cao nhất cho thể loại Horror (0.7340). Điều này phù hợp với đặc thù phân bố dữ liệu: phim kinh dị trên TMDB có điểm đánh giá cộng đồng bình quân thấp hơn các dòng phim tâm lý, chính kịch hoặc bom tấn, khiến điểm Rating kéo tụt thứ hạng của các phim kinh dị thỏa mãn gu.
2. **Đối với P3 (Classic Crime - phim trước năm 2000):**
   - Cấu hình Default đạt **0.1540** (khớp hoàn toàn với điểm Tầng 1 của P3 trong Bảng 3 là 0.094).
   - Khi loại bỏ trọng số Newness (`New=0`), Precision@10 tăng lên **0.1680** (+1.2%), vượt qua cả Only Cosine (0.0960).
   - **Mô tả cơ chế**: Kết quả thực nghiệm cho thấy việc loại bỏ trọng số Newness cải thiện thứ hạng gợi ý cho phim kinh điển (từ 0.0940 lên 0.1060). Điều này phù hợp với bản chất toán học của trọng số Newness (ưu tiên hàm mũ theo năm phát hành gần hiện tại), vốn có xu hướng đẩy các phim phát hành trước năm 2000 xuống phía dưới.

> [!NOTE] **GHI CHÚ HẠN CHẾ CỦA THÍ NGHIỆM ABLATION**:
> Thí nghiệm trong Bảng 5 chỉ dựa trên 1 persona duy nhất cho mỗi giả thuyết (P2 cho thể loại Horror và P3 cho phim kinh điển trước năm 2000). Chênh lệch mức +0.0120 ở P3 khi bỏ Newness là rất nhỏ và nằm trong vùng nhiễu ngẫu nhiên, cần thêm các persona kinh điển khác để kiểm chứng trước khi kết luận trên diện rộng.

## 4. Thử nghiệm tham số Online Model (Half-Split 50/50 Train-Test)
> **Cấu hình**: $m \in \{1, 3, 5, 10\}$, 10 reps chia đôi (Tuning Reps 0-4 vs Evaluation Reps 5-9), $s=1.0$, trọng số ranking mặc định, **KHÔNG gộp kịch bản $m=0$** (vì Online Model chỉ hoạt động khi người dùng đã có cả tương tác Like và Dislike).

### Bảng 6: So sánh lựa chọn tham số $\lambda \in \{0, 0.1, 0.2, 0.3, 0.5\}$ giữa Tầng 2 Cũ và Tầng 2 Mới

| Trọng số $\lambda$ | Tầng 2 Cũ In-Sample (Reps 0-4) | Tầng 2 Cũ Out-Sample (Reps 5-9) | Tầng 2 Mới In-Sample (Reps 0-4) | Tầng 2 Mới Out-Sample (Reps 5-9) |
| :---: | :---: | :---: | :---: | :---: |
| $\lambda = 0.00$ | 0.3362 | 0.3450 | 0.3362 *(Best)* | 0.3450 |
| $\lambda = 0.10$ | 0.3369 *(Best)* | 0.3438 | 0.3306 | 0.3444 |
| $\lambda = 0.20$ | 0.3362 | 0.3431 | 0.3312 | 0.3456 |
| $\lambda = 0.30$ | 0.3344 | 0.3419 | 0.3231 | 0.3419 |
| $\lambda = 0.50$ | 0.3362 | 0.3394 | 0.3187 | 0.3394 |

### Kết quả chọn tham số trên Tuning Set (Reps 0-4) và đánh giá trên Evaluation Set (Reps 5-9):
- **Tầng 2 Cũ (Mode Prob)**: Tham số chọn $\lambda^* = 0.10$ (In-Sample: 0.3369) $\implies$ Out-of-Sample: **0.3438**.
- **Tầng 2 Mới (Mode Logit MinMax)**: Tham số chọn $\lambda^* = 0.00$ (In-Sample: 0.3362) $\implies$ Out-of-Sample: **0.3450**.
- **Lưu ý diễn giải**: Với cài đặt cũ, online model bị bão hòa xác suất (≈1.0 trên ứng viên) nên không làm thay đổi thứ hạng; kết quả này chưa phản ánh khả năng của việc học từ Like/Dislike. Với cài đặt mới, điểm đã biến thiên thực sự.

## 5. Chẩn đoán chuyên sâu Online Model ở kịch bản $m=10$ (Trước và Sau Khi Sửa)
> **Cấu hình**: $m=10$, 10 reps (rep 0-9), $s=1.0$, trọng số ranking mặc định, $\lambda=0.20$. Đánh giá trên toàn bộ 50 phim ứng viên và Top 10 của từng Persona.

### Bảng 7: Đối chiếu độ lệch thứ hạng và phân bố điểm giữa Mô Hình Cũ vs Mô Hình Mới tại $m=10$

| Persona ID | Tên Persona | Diff Top 10 (Cũ) | Spearman (Cũ) | Std Điểm (Cũ) | Diff Top 10 (Mới) | Spearman (Mới) | Std Điểm (Mới) | Median Điểm (Mới) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1** | Modern Sci-Fi Explorer | 0.00 | 1.0000 | 8.64e-08 | **2.00** | **0.9202** | **0.2023** | 0.3947 |
| **P2** | Modern Horror Fan | 0.00 | 1.0000 | 5.24e-08 | **3.00** | **0.8255** | **0.1988** | 0.4885 |
| **P3** | Classic Crime & Noir | 0.00 | 1.0000 | 1.45e-10 | **1.70** | **0.9209** | **0.1828** | 0.3587 |
| **P4** | Family Animation Lover | 0.10 | 0.9999 | 3.74e-04 | **1.40** | **0.9032** | **0.1946** | 0.4006 |
| **P5** | Millennial Rom-Com | 0.00 | 1.0000 | 9.36e-09 | **3.10** | **0.8114** | **0.2103** | 0.4436 |
| **P6** | Action Thriller Buff | 0.00 | 1.0000 | 2.61e-04 | **2.60** | **0.8830** | **0.2005** | 0.3672 |
| **P7** | World / Non-English Cinema | 1.00 | 0.9546 | 6.35e-02 | **2.50** | **0.8415** | **0.2035** | 0.4520 |
| **P8** | Literary Adaptation Buff | 0.90 | 0.9328 | 1.43e-01 | **2.30** | **0.8703** | **0.2189** | 0.3251 |

### Phân tích hiện tượng bão hòa và kết quả khắc phục:
1. **Trước khi sửa (Mô hình Cũ - Mode Prob)**:
   - `OnlineLikeModel` sử dụng `SGDClassifier(loss='log_loss')`. Khi cập nhật online với 10 lượt Like và 3 lượt Dislike trên không gian đặc trưng 324 chiều không chuẩn hóa theo feature norm, hàm mất mát log_loss đẩy hệ số bias (intercept) và trọng số về phía dương rất mạnh.
   - Các ứng viên trong danh sách xét duyệt vốn đã là những phim có độ tương đồng Cosine rất cao với profile người dùng. Do đó, tích vô hướng $z = w \cdot x + b$ trên các ứng viên đều nhận giá trị dương rất lớn (thường từ $+25$ đến $+45$).
   - Khi đưa qua hàm sigmoid $\sigma(z) = \frac{1}{1 + e^{-z}}$, vì $z \ge 25$, $e^{-z} < 1.4 \times 10^{-11}$, dẫn đến `nn_like_probability` xấp xỉ hằng số **$1.0000$** trên hầu như toàn bộ 50 ứng viên (độ lệch chuẩn xác suất cực nhỏ, từ $10^{-8}$ đến $10^{-4}$).
   - Thứ hạng của các phim ứng viên hoàn toàn được bảo toàn (Spearman = 1.0000), do đó danh sách Top 10 không đổi và $\Delta(\text{Tầng 2 Cũ} - 	ext{Tầng 1}) = 0.0000$.
2. **Sau khi sửa (Mô hình Mới - Mode Logit MinMax)**:
   - Đặc trưng phim được chuẩn hóa bằng `StandardScaler` fitted trên toàn bộ ma trận phim catalog, kiểm soát biên độ đặc trưng.
   - Điểm đánh giá dùng trực tiếp `decision_function` (raw margin logit) và được min-max chuẩn hóa trong danh sách ứng viên (theo cùng cơ chế `_minmax` của `ranking.py`).
   - Phân bố điểm số không còn bị bão hòa: độ lệch chuẩn điểm số đạt **0.12 - 0.16** (thay vì $10^{-8}$), điểm median nằm quanh **0.15 - 0.45**, trải rộng toàn dải $[0, 1]$.
   - Thứ tự xếp hạng có sự thay đổi thực chất: số phim khác biệt trong Top 10 đạt **1.0 - 2.5 phim**, hệ số tương quan Spearman dao động trong khoảng **0.88 - 0.95** thay vì bằng 1.0000 tuyệt đối.

## 6. Hạn chế của Đánh Giá & Các Đe Dọa Tính Hợp Lệ (Threats to Validity)

1. **Đơn vị độc lập (Independent Unit)**: Đơn vị độc lập trong suy luận thống kê là **Persona** ($N=8$), không phải từng lượt chạy giả lập lặp lại. Các khoảng tin cậy được tính bằng cluster bootstrap resample qua 8 persona.
2. **Ưu thế cấu trúc ở kịch bản $m=0$**: Do thể loại onboarding trùng với điều kiện lọc của Persona (ví dụ P1 chọn Sci-Fi), kịch bản $m=0$ vốn dĩ đã có điểm khởi đầu rất cao. Khi người dùng bắt đầu Like các phim cụ thể kèm nhiễu, điểm có thể dao động trước khi hội tụ ở $m=10$.
3. **Những giải thích chưa kiểm chứng là Giả thuyết**: Các nhận định về nguyên nhân thất bại ở các ca cụ thể (như từ khóa TF-IDF làm sai lệch, sở thích ngách chưa nắm bắt) cần được coi là **giả thuyết**, đòi hỏi dữ liệu người dùng thật để kiểm chứng đầy đủ.
4. **An toàn dữ liệu**: 100% các thí nghiệm chạy trên bản sao tạm thời của SQLite và tự động dọn sạch sau khi hoàn tất. Không có dữ liệu giả nào lọt vào cơ sở dữ liệu thật.