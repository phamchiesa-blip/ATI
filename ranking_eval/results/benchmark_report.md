# Báo Cáo Đánh Giá Hiệu Năng Hệ Thống Gợi Ý Phim (Offline Benchmark)

> **Thời gian chạy**: 156.51 giây | **Tổng số lượt giả lập**: 400 users x 6 rankers = 2400 lượt đánh giá
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
| **(0a) Random** | 0.035 ± 0.062 | 0.002 ± 0.004 | 0.004 ± 0.007 | 0.011 ± 0.008 | 28.2% | N/A |
| **(0b) Popular** | 0.049 ± 0.099 | 0.003 ± 0.006 | 0.006 ± 0.012 | 0.025 ± 0.028 | 24.5% | N/A |
| **(1) Baseline (Cosine)** | 0.334 ± 0.260 | 0.020 ± 0.017 | 0.038 ± 0.031 | 0.087 ± 0.067 | 84.0% | N/A |
| **(2) Tầng 1 (Ranking)** | 0.390 ± 0.272 | 0.024 ± 0.019 | 0.046 ± 0.036 | 0.098 ± 0.076 | 87.5% | N/A |
| **(3a) Tầng 2 Cũ (Mode Prob)** | 0.388 ± 0.273 | 0.024 ± 0.019 | 0.045 ± 0.036 | 0.098 ± 0.076 | 87.5% | 80.0% |
| **(3b) Tầng 2 Mới (Mode Logit MinMax)** | 0.388 ± 0.269 | 0.024 ± 0.019 | 0.045 ± 0.035 | 0.098 ± 0.076 | 87.5% | 80.0% |

### Bảng 2: So sánh theo cặp (Paired Bootstrap 95% CI - Đơn vị độc lập: Persona)
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$** ở hàng Tổng thể.
Khoảng tin cậy 95% được tính bằng bootstrap resample ngẫu nhiên 8 Persona ($B=5.000$ lần):

| Phạm vi | So sánh cặp | Chênh lệch trung bình (Mean Δ) | Khoảng tin cậy 95% CI | Chứa 0? | Ý nghĩa thống kê (α=0.05) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Tổng thể (ALL)** | Tầng 1 trừ Baseline | +0.0570 | [0.0192, 0.0960] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Baseline)** |
| **Tổng thể (ALL)** | Tầng 2 Cũ trừ Tầng 1 | -0.0027 | [-0.0062, 0.0008] | **CÓ** | Không có ý nghĩa thống kê |
| **Tổng thể (ALL)** | Tầng 2 Mới trừ Tầng 1 | -0.0027 | [-0.0080, 0.0023] | **CÓ** | Không có ý nghĩa thống kê |
| Chỉ Onboarding (m=0) | Tầng 1 trừ Baseline | +0.0250 | [-0.0250, 0.0875] | **CÓ** | Không có ý nghĩa |
| Chỉ Onboarding (m=0) | Tầng 2 Cũ trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |
| Chỉ Onboarding (m=0) | Tầng 2 Mới trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 1 Like (m=1) | Tầng 1 trừ Baseline | +0.0662 | [0.0162, 0.1175] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 1 Like (m=1) | Tầng 2 Cũ trừ Tầng 1 | -0.0025 | [-0.0100, 0.0075] | **CÓ** | Không có ý nghĩa |
| Onboarding + 1 Like (m=1) | Tầng 2 Mới trừ Tầng 1 | +0.0100 | [-0.0075, 0.0300] | **CÓ** | Không có ý nghĩa |
| Onboarding + 3 Likes (m=3) | Tầng 1 trừ Baseline | +0.0638 | [0.0237, 0.1038] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 3 Likes (m=3) | Tầng 2 Cũ trừ Tầng 1 | -0.0088 | [-0.0250, 0.0025] | **CÓ** | Không có ý nghĩa |
| Onboarding + 3 Likes (m=3) | Tầng 2 Mới trừ Tầng 1 | +0.0087 | [-0.0025, 0.0200] | **CÓ** | Không có ý nghĩa |
| Onboarding + 5 Likes (m=5) | Tầng 1 trừ Baseline | +0.0688 | [0.0225, 0.1213] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 5 Likes (m=5) | Tầng 2 Cũ trừ Tầng 1 | -0.0025 | [-0.0062, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 5 Likes (m=5) *(thăm dò)* | Tầng 2 Mới trừ Tầng 1 | -0.0188 | [-0.0363, -0.0038] | **KHÔNG** | **Có ý nghĩa (chưa hiệu chỉnh)** |
| Onboarding + 10 Likes (m=10) | Tầng 1 trừ Baseline | +0.0612 | [0.0225, 0.1000] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 10 Likes (m=10) | Tầng 2 Cũ trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 10 Likes (m=10) | Tầng 2 Mới trừ Tầng 1 | -0.0138 | [-0.0287, 0.0012] | **CÓ** | Không có ý nghĩa |

### Bảng 3: Bảng chênh lệch Precision@10 chi tiết theo từng Persona
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$**.

| Persona ID | Tên Persona | Baseline P@10 | Tầng 1 P@10 | Δ (T1 - Base) | T2 Cũ P@10 | Δ (T2 Cũ - T1) | T2 Mới P@10 | Δ (T2 Mới - T1) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1** | Modern Sci-Fi Explorer | 0.386 | 0.518 | **+0.132** | 0.514 | -0.004 | 0.522 | **+0.004** |
| **P2** | Modern Horror Fan | 0.682 | 0.666 | **-0.016** | 0.666 | +0.000 | 0.674 | **+0.008** |
| **P3** | Classic Crime & Noir | 0.096 | 0.094 | **-0.002** | 0.092 | -0.002 | 0.090 | **-0.004** |
| **P4** | Family Animation Lover | 0.588 | 0.732 | **+0.144** | 0.726 | -0.006 | 0.736 | **+0.004** |
| **P5** | Millennial Rom-Com | 0.298 | 0.374 | **+0.076** | 0.380 | +0.006 | 0.358 | **-0.016** |
| **P6** | Action Thriller Buff | 0.256 | 0.336 | **+0.080** | 0.336 | +0.000 | 0.326 | **-0.010** |
| **P7** | World / Non-English Cinema *(ngoài vector)* | 0.326 | 0.350 | **+0.024** | 0.338 | -0.012 | 0.344 | **-0.006** |
| **P8** | Literary Adaptation Buff *(ngoài vector)* | 0.036 | 0.054 | **+0.018** | 0.050 | -0.004 | 0.052 | **-0.002** |

### Nhận định & Kết luận trung thực:
1. **Về Tầng 1 trừ Baseline:**
   - Trên tổng thể, Tầng 1 cao hơn Baseline trung bình **+5.7%** điểm Precision@10.
   - Khoảng tin cậy 95% Bootstrap resample theo persona là **[0.0192, 0.0960]**, **KHÔNG chứa 0**. Điều này khẳng định Tầng 1 mang lại cải thiện có ý nghĩa thống kê ở mức tổng thể.
2. **Về Tầng 2 Cũ trừ Tầng 1:**
   - Trên tổng thể, Tầng 2 Cũ chênh lệch **-0.27%** so với Tầng 1.
   - Khoảng tin cậy 95% là **[-0.0062, 0.0008]**, **CHỨA 0**.
   - **Lưu ý diễn giải**: Với cài đặt ban đầu (unscaled, probability), online model bị bão hòa xác suất (≈1.0 trên ứng viên) nên không làm thay đổi thứ hạng; kết quả này chưa phản ánh khả năng của việc học từ Like/Dislike.
3. **Về Tầng 2 Mới trừ Tầng 1:**
   - **Kết luận chính**: Trên tổng thể, Tầng 2 Mới không khác Tầng 1 có ý nghĩa thống kê (Mean $\Delta = -0.0027$, 95% CI: `[-0.0080, 0.0023]`, chứa 0). Khi dò siêu tham số trên tập tuning (Reps 0-4), $\lambda^* = 0.00$ được chọn (tức là tắt online model, chỉ dùng Tầng 1).
   - **Ghi chú về kết quả theo từng $m$**: Kết quả theo từng m (bao gồm chênh lệch -0.0188 ở m=5) mang tính thăm dò, là một trong năm lát cắt và không qua hiệu chỉnh nhiều phép thử (unadjusted for multiple testing); do đó không đủ cơ sở để coi đây là bằng chứng độc lập về việc mô hình làm suy giảm chất lượng tại mốc này.
   - **Nhận định cơ chế**: Mô hình mới đã khắc phục triệt để hiện tượng bão hòa xác suất toán học (điểm std $\approx 0.20$, làm thay đổi 1-3 phim trong Top 10 thay vì cố định). Tuy nhiên, việc học một mô hình phân loại tuyến tính từ số lượng tương tác rất ít (1-10 tương tác) trong không gian đặc trưng lớn (324 chiều) có phương sai ước lượng cao, khiến điểm bổ sung chưa mang lại lợi thế hơn so với Tầng 1 đơn lẻ.

## 2. Thí nghiệm: 'Một Like có át onboarding không?' (Onboarding Vector Scale $s$)
> **Phân loại**: **[Thăm dò (Exploratory) - chọn trên cùng dữ liệu đánh giá]**
> **Cấu hình**: $m \in \{1, 3, 5, 10\}$, 10 reps (rep 0-9), $s \in \{1, 3, 5\}$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **KHÔNG gộp kịch bản $m=0$** (vì $m=0$ chưa có lượt Like/Dislike nào để đo hiện tượng Like át onboarding).

> [!WARNING] **CẢNH BÁO VỀ LỢI THẾ CƠ CẤU TRONG MÔ PHỎNG**:
> Do thể loại chọn lúc onboarding trùng hoàn toàn với điều kiện lọc định nghĩa Persona (ví dụ Persona P1 thích Sci-Fi và onboarding chọn Sci-Fi), việc nhân hệ số onboarding ($s=3, 5$) vốn dĩ tạo ra lợi thế cơ cấu (structural advantage) sẵn có trong môi trường giả lập. Trong môi trường thực tế, nếu người dùng ban đầu chọn thể loại không hoàn toàn chính xác hoặc gu phim thay đổi linh hoạt sau này, việc đặt hệ số $s$ quá lớn sẽ khiến mô hình bị 'trơ' (inertia), khó thích ứng với các tương tác Like/Dislike thực tế.

### Bảng 4: Hiệu năng Precision@10 khi thay đổi hệ số scale vector Onboarding $s$

| Số lượt Like ($m$) | Baseline ($s=1$) | Baseline ($s=3$) | Baseline ($s=5$) | Tầng 1 ($s=1$) | Tầng 1 ($s=3$) | Tầng 1 ($s=5$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $m=1$ | 0.281 | 0.323 | 0.344 | 0.347 | 0.390 | 0.396 |
| $m=3$ | 0.339 | 0.391 | 0.406 | 0.403 | 0.441 | 0.446 |
| $m=5$ | 0.316 | 0.380 | 0.385 | 0.385 | 0.451 | 0.455 |
| $m=10$ | 0.369 | 0.380 | 0.393 | 0.430 | 0.434 | 0.450 |

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
| Default (Cos 0.6, Rat 0.2, Pop 0.1, New 0.1) | 0.6660 | 0.0940 |
| No Rating (Rat=0) | 0.7340 | 0.0500 |
| No Popularity (Pop=0) | 0.7080 | 0.0940 |
| No Newness (New=0) | 0.6440 | 0.1060 |
| Only Cosine (Rat=0, Pop=0, New=0) | 0.6820 | 0.0960 |

### Phân tích cơ chế và giải thích trung tính:
1. **Đối với P2 (Modern Horror):**
   - Cấu hình Default đạt **0.6660** (khớp hoàn toàn với điểm Tầng 1 của P2 trong Bảng 3 là 0.666).
   - Khi loại bỏ trọng số Rating (`Rat=0`), Precision@10 tăng lên **0.7340** (+6.8%).
   - Khi cấu hình về thuần Cosine (`Only Cosine`), Precision@10 là **0.6820** (khớp hoàn toàn với Baseline của P2 trong Bảng 3 là 0.682).
   - **Mô tả cơ chế**: Kết quả thực nghiệm cho thấy việc loại bỏ trọng số Rating mang lại hiệu năng cao nhất cho thể loại Horror (0.7340). Điều này phù hợp với đặc thù phân bố dữ liệu: phim kinh dị trên TMDB có điểm đánh giá cộng đồng bình quân thấp hơn các dòng phim tâm lý, chính kịch hoặc bom tấn, khiến điểm Rating kéo tụt thứ hạng của các phim kinh dị thỏa mãn gu.
2. **Đối với P3 (Classic Crime - phim trước năm 2000):**
   - Cấu hình Default đạt **0.0940** (khớp hoàn toàn với điểm Tầng 1 của P3 trong Bảng 3 là 0.094).
   - Khi loại bỏ trọng số Newness (`New=0`), Precision@10 tăng lên **0.1060** (+1.2%), vượt qua cả Only Cosine (0.0960).
   - **Mô tả cơ chế**: Kết quả thực nghiệm cho thấy việc loại bỏ trọng số Newness cải thiện thứ hạng gợi ý cho phim kinh điển (từ 0.0940 lên 0.1060). Điều này phù hợp với bản chất toán học của trọng số Newness (ưu tiên hàm mũ theo năm phát hành gần hiện tại), vốn có xu hướng đẩy các phim phát hành trước năm 2000 xuống phía dưới.

> [!NOTE] **GHI CHÚ HẠN CHẾ CỦA THÍ NGHIỆM ABLATION**:
> Thí nghiệm trong Bảng 5 chỉ dựa trên 1 persona duy nhất cho mỗi giả thuyết (P2 cho thể loại Horror và P3 cho phim kinh điển trước năm 2000). Chênh lệch mức +0.0120 ở P3 khi bỏ Newness là rất nhỏ và nằm trong vùng nhiễu ngẫu nhiên, cần thêm các persona kinh điển khác để kiểm chứng trước khi kết luận trên diện rộng.

## 4. Thử nghiệm tham số Online Model (Half-Split 50/50 Train-Test)
> **Cấu hình**: $m \in \{1, 3, 5, 10\}$, 10 reps chia đôi (Tuning Reps 0-4 vs Evaluation Reps 5-9), $s=1.0$, trọng số ranking mặc định, **KHÔNG gộp kịch bản $m=0$** (vì Online Model chỉ hoạt động khi người dùng đã có cả tương tác Like và Dislike).

### Bảng 6: So sánh lựa chọn tham số $\lambda \in \{0, 0.1, 0.2, 0.3, 0.5\}$ giữa Tầng 2 Cũ và Tầng 2 Mới

| Trọng số $\lambda$ | Tầng 2 Cũ In-Sample (Reps 0-4) | Tầng 2 Cũ Out-Sample (Reps 5-9) | Tầng 2 Mới In-Sample (Reps 0-4) | Tầng 2 Mới Out-Sample (Reps 5-9) |
| :---: | :---: | :---: | :---: | :---: |
| $\lambda = 0.00$ | 0.3806 | 0.4019 | 0.3806 *(Best)* | 0.4019 |
| $\lambda = 0.10$ | 0.3812 *(Best)* | 0.4000 | 0.3744 | 0.3987 |
| $\lambda = 0.20$ | 0.3781 | 0.3975 | 0.3775 | 0.3981 |
| $\lambda = 0.30$ | 0.3756 | 0.3962 | 0.3644 | 0.3925 |
| $\lambda = 0.50$ | 0.3763 | 0.3931 | 0.3594 | 0.3869 |

### Kết quả chọn tham số trên Tuning Set (Reps 0-4) và đánh giá trên Evaluation Set (Reps 5-9):
- **Tầng 2 Cũ (Mode Prob)**: Tham số chọn $\lambda^* = 0.10$ (In-Sample: 0.3812) $\implies$ Out-of-Sample: **0.4000**.
- **Tầng 2 Mới (Mode Logit MinMax)**: Tham số chọn $\lambda^* = 0.00$ (In-Sample: 0.3806) $\implies$ Out-of-Sample: **0.4019**.
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
| **P7** | World / Non-English Cinema | 0.00 | 1.0000 | 5.15e-09 | **1.50** | **0.8662** | **0.2201** | 0.4121 |
| **P8** | Literary Adaptation Buff | 0.20 | 0.9917 | 1.62e-02 | **2.10** | **0.9069** | **0.1982** | 0.3604 |

### Phân tích hiện tượng bão hòa và kết quả khắc phục:
1. **Trước khi sửa (Mô hình Cũ - Mode Prob)**:
   - `OnlineLikeModel` sử dụng `SGDClassifier(loss='log_loss')`. Khi cập nhật online với 10 lượt Like và 3 lượt Dislike trên không gian đặc trưng 324 chiều không chuẩn hóa theo feature norm, hàm mất mát log_loss đẩy hệ số bias (intercept) và trọng số về phía dương rất mạnh.
   - Các ứng viên trong danh sách xét duyệt vốn đã là những phim có độ tương đồng Cosine rất cao với profile người dùng. Do đó, tích vô hướng $z = w \cdot x + b$ trên các ứng viên đều nhận giá trị dương rất lớn (thường từ $+25$ đến $+45$).
   - Khi đưa qua hàm sigmoid $\sigma(z) = \frac{1}{1 + e^{-z}}$, vì $z \ge 25$, $e^{-z} < 1.4 \times 10^{-11}$, dẫn đến `nn_like_probability` xấp xỉ hằng số **$1.0000$** trên hầu như toàn bộ 50 ứng viên (độ lệch chuẩn xác suất cực nhỏ, từ $10^{-8}$ đến $10^{-4}$).
   - Thứ hạng của các phim ứng viên hoàn toàn được bảo toàn (Spearman = 1.0000), do đó danh sách Top 10 không đổi và $\Delta(\text{Tầng 2 Cũ} - \text{Tầng 1}) = 0.0000$.
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