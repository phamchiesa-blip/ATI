# Báo Cáo Đánh Giá Hiệu Năng Hệ Thống Gợi Ý Phim (Offline Benchmark)

> **Thời gian chạy**: 218.35 giây | **Tổng số lượt giả lập**: 400 users x 5 rankers = 2000 lượt đánh giá
> **Đơn vị độc lập trong suy luận thống kê**: **Persona** (Cluster Bootstrap Resample over 8 Personas).

## 0. Bảng Cấu Hình Tham Số Cho Từng Thí Nghiệm & Bảng Đánh Giá

| Bảng | Tên thí nghiệm / Báo cáo | Tập $m$ đánh giá | Số Reps | Hệ số Onboarding ($s$) | Trọng số Ranking (Cos, Rat, Pop, New) | Gộp kịch bản $m=0$? | Ghi chú mục đích |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Bảng 1** | Hiệu năng tổng thể 5 Ranker | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **CÓ** | Đánh giá toàn diện hành trình người dùng |
| **Bảng 2** | So sánh Paired Bootstrap 95% CI | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **CÓ** | Đo ý nghĩa thống kê theo Persona ($B=5.000$) |
| **Bảng 3** | Chi tiết theo 8 Persona | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **CÓ** | So sánh chi tiết từng gu sở thích |
| **Bảng 4** | Thí nghiệm Onboarding Scale $s$ | $m \in \{1, 3, 5, 10\}$ | 10 (0-9) | $s \in \{1, 3, 5\}$ | (0.6, 0.2, 0.1, 0.1) | **KHÔNG** | Kiểm tra tương tác Like có át Onboarding không |
| **Bảng 5** | Ablation trọng số trên P2 & P3 | $m \in \{0, 1, 3, 5, 10\}$ | 10 (0-9) | $s=1.0$ | Biến thiên lần lượt từng trọng số về 0 | **CÓ** | Kiểm định nguyên nhân tụt điểm ở Kinh dị & Cổ điển |
| **Bảng 6** | Tuning tham số $\lambda$ Online Model | $m \in \{1, 3, 5, 10\}$ | 5/5 split | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **KHÔNG** | Tránh data leakage: Train Reps 0-4, Test Reps 5-9 |
| **Bảng 7** | Chẩn đoán Online Model ở $m=10$ | $m=10$ | 10 (0-9) | $s=1.0$ | (0.6, 0.2, 0.1, 0.1) | **KHÔNG** | Chẩn đoán phân bố xác suất và thứ hạng ở $m=10$ |

## 1. Tóm tắt kết quả cốt lõi & So sánh Paired Bootstrap 95% CI

### Bảng 1: Hiệu năng tổng thể giữa 5 phương pháp xếp hạng (400 user / phương pháp)
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$**.

| Ranker | Precision@10 | Recall@10 | F1@10 | Recall@50 | Hit Rate@10 | Online Model Active |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **(0a) Random** | 0.035 ± 0.062 | 0.002 ± 0.004 | 0.004 ± 0.007 | 0.011 ± 0.008 | 28.2% | N/A |
| **(0b) Popular** | 0.049 ± 0.099 | 0.003 ± 0.006 | 0.006 ± 0.012 | 0.025 ± 0.028 | 24.5% | N/A |
| **(1) Baseline (Cosine)** | 0.334 ± 0.260 | 0.020 ± 0.017 | 0.038 ± 0.031 | 0.087 ± 0.067 | 84.0% | N/A |
| **(2) Tầng 1 (Ranking)** | 0.390 ± 0.272 | 0.024 ± 0.019 | 0.046 ± 0.036 | 0.098 ± 0.076 | 87.5% | N/A |
| **(3) Tầng 2 (Tầng 1 + Online Model)** | 0.388 ± 0.273 | 0.024 ± 0.019 | 0.045 ± 0.036 | 0.098 ± 0.076 | 87.5% | 80.0% |

### Bảng 2: So sánh theo cặp (Paired Bootstrap 95% CI - Đơn vị độc lập: Persona)
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$** ở hàng Tổng thể.
Khoảng tin cậy 95% được tính bằng bootstrap resample ngẫu nhiên 8 Persona ($B=5.000$ lần):

| Phạm vi | So sánh cặp | Chênh lệch trung bình (Mean Δ) | Khoảng tin cậy 95% CI | Chứa 0? | Ý nghĩa thống kê (α=0.05) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Tổng thể (ALL)** | Tầng 1 trừ Baseline | +0.0570 | [0.0192, 0.0960] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Baseline)** |
| **Tổng thể (ALL)** | Tầng 2 trừ Tầng 1 | -0.0027 | [-0.0062, 0.0008] | **CÓ** | Không có ý nghĩa thống kê |
| Chỉ Onboarding (m=0) | Tầng 1 trừ Baseline | +0.0250 | [-0.0250, 0.0875] | **CÓ** | Không có ý nghĩa |
| Chỉ Onboarding (m=0) | Tầng 2 trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 1 Like (m=1) | Tầng 1 trừ Baseline | +0.0662 | [0.0162, 0.1175] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 1 Like (m=1) | Tầng 2 trừ Tầng 1 | -0.0025 | [-0.0100, 0.0075] | **CÓ** | Không có ý nghĩa |
| Onboarding + 3 Likes (m=3) | Tầng 1 trừ Baseline | +0.0638 | [0.0237, 0.1038] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 3 Likes (m=3) | Tầng 2 trừ Tầng 1 | -0.0088 | [-0.0250, 0.0025] | **CÓ** | Không có ý nghĩa |
| Onboarding + 5 Likes (m=5) | Tầng 1 trừ Baseline | +0.0688 | [0.0225, 0.1213] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 5 Likes (m=5) | Tầng 2 trừ Tầng 1 | -0.0025 | [-0.0062, 0.0000] | **CÓ** | Không có ý nghĩa |
| Onboarding + 10 Likes (m=10) | Tầng 1 trừ Baseline | +0.0612 | [0.0225, 0.1000] | **KHÔNG** | **Có ý nghĩa (Tầng 1 > Base)** |
| Onboarding + 10 Likes (m=10) | Tầng 2 trừ Tầng 1 | +0.0000 | [0.0000, 0.0000] | **CÓ** | Không có ý nghĩa |

### Bảng 3: Bảng chênh lệch Precision@10 chi tiết theo từng Persona
> **Cấu hình**: $m \in \{0, 1, 3, 5, 10\}$, 10 reps (rep 0-9), $s=1.0$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **GỘP kịch bản $m=0$**.

| Persona ID | Tên Persona | Baseline P@10 | Tầng 1 P@10 | Δ (Tầng 1 - Base) | Tầng 2 P@10 | Δ (Tầng 2 - Tầng 1) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **P1** | Modern Sci-Fi Explorer | 0.386 | 0.518 | **+0.132** | 0.514 | -0.004 |
| **P2** | Modern Horror Fan | 0.682 | 0.666 | **-0.016** | 0.666 | +0.000 |
| **P3** | Classic Crime & Noir | 0.096 | 0.094 | **-0.002** | 0.092 | -0.002 |
| **P4** | Family Animation Lover | 0.588 | 0.732 | **+0.144** | 0.726 | -0.006 |
| **P5** | Millennial Rom-Com | 0.298 | 0.374 | **+0.076** | 0.380 | +0.006 |
| **P6** | Action Thriller Buff | 0.256 | 0.336 | **+0.080** | 0.336 | +0.000 |
| **P7** | World / Non-English Cinema *(ngoài vector)* | 0.326 | 0.350 | **+0.024** | 0.338 | -0.012 |
| **P8** | Literary Adaptation Buff *(ngoài vector)* | 0.036 | 0.054 | **+0.018** | 0.050 | -0.004 |

### Nhận định & Kết luận trung thực:
1. **Về Tầng 1 trừ Baseline:**
   - Trên tổng thể, Tầng 1 cao hơn Baseline trung bình **+5.7%** điểm Precision@10.
   - Khoảng tin cậy 95% Bootstrap resample theo persona là **[0.0192, 0.0960]**, **KHÔNG chứa 0**. Điều này khẳng định Tầng 1 mang lại cải thiện có ý nghĩa thống kê ở mức tổng thể.
   - Tuy nhiên, sự cải thiện không đồng nhất giữa các persona: Tầng 1 vượt trội ở P1 (+13.2%), P4 (+14.4%), P5 (+7.6%), P6 (+8.0%), nhưng bị giảm nhẹ ở P2 (-1.6%) và gần như hòa ở P3 (-0.2%).
2. **Về Tầng 2 trừ Tầng 1:**
   - Trên tổng thể, Tầng 2 chênh lệch **-0.27%** so với Tầng 1.
   - Khoảng tin cậy 95% là **[-0.0062, 0.0008]**, **CHỨA 0**.
   - **Lưu ý diễn giải**: Với cài đặt hiện tại online model bị bão hòa xác suất (≈1.0 trên ứng viên) nên không làm thay đổi thứ hạng; kết quả này chưa phản ánh khả năng của việc học từ Like/Dislike.
3. **Lưu ý về kịch bản m=0 (Onboarding only):**
   - Ở kịch bản $m=0$, việc onboarding trùng với thể loại định nghĩa persona tạo ra **lợi thế cơ cấu (structural advantage)** rõ rệt (P@10 đạt ~38.8%), khiến hiệu năng khởi điểm đã rất cao.

## 2. Thí nghiệm: 'Một Like có át onboarding không?' (Onboarding Vector Scale $s$)
> **Phân loại**: **[Thăm dò (Exploratory) - chọn trên cùng dữ liệu đánh giá]**
> **Cấu hình**: $m \in \{1, 3, 5, 10\}$, 10 reps (rep 0-9), $s \in \{1, 3, 5\}$, trọng số mặc định (0.6, 0.2, 0.1, 0.1), **KHÔNG gộp kịch bản $m=0$** (vì $m=0$ chưa có lượt Like/Dislike nào để đo hiện tượng Like át onboarding).

> [!WARNING] **CẢNH BÁO VỀ LỢI THẾ CƠ CẤU TRONG MÔ PHỎNG**:
> Do thể loại chọn lúc onboarding trùng hoàn toàn với điều kiện lọc định nghĩa Persona (ví dụ Persona P1 thích Sci-Fi và onboarding chọn Sci-Fi), việc nhân hệ số onboarding ($s=3, 5$) vốn dĩ tạo ra lợi thế cơ cấu (structural advantage) sẵn có trong môi trường giả lập. Trong môi trường thực tế, nếu người dùng ban đầu chọn thể loại không hoàn toàn chính xác hoặc gu phim thay đổi linh hoạt sau này, việc đặt hệ số $s$ quá lớn sẽ khiến mô hình bị 'trơ' (inertia), khó thích ứng với các tương tác Like/Dislike thực tế.

### Bảng 4: Hiệu năng Precision@10 khi thay đổi hệ số scale vector Onboarding $s$

| Số lượt Like ($m$) | Baseline ($s=1$) | Baseline ($s=3$) | Baseline ($s=5$) | Tầng 1 ($s=1$) | Tầng 1 ($s=3$) | Tầng 1 ($s=5$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $m=1$ | 0.281 | 0.334 | 0.343 | 0.347 | 0.414 | 0.410 |
| $m=3$ | 0.339 | 0.388 | 0.420 | 0.403 | 0.456 | 0.454 |
| $m=5$ | 0.316 | 0.378 | 0.388 | 0.385 | 0.445 | 0.443 |
| $m=10$ | 0.369 | 0.389 | 0.405 | 0.430 | 0.443 | 0.460 |

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

### Bảng 6: Đánh giá tham số $\lambda$ Online Model trên phân chia độc lập 50/50 Train-Test

| Trọng số $\lambda$ Online Model | In-Sample P@10 (Tuning Reps 0-4) | Out-of-Sample P@10 (Evaluation Reps 5-9) | Trung bình 10 Reps |
| :---: | :---: | :---: | :---: |
| $\lambda = 0.00$ | 0.3806 | 0.4019 | 0.3912 |
| $\lambda = 0.10$ *(Best Tuning)* | 0.3812 | 0.4000 | 0.3906 |
| $\lambda = 0.20$ | 0.3781 | 0.3975 | 0.3878 |
| $\lambda = 0.30$ | 0.3756 | 0.3962 | 0.3859 |
| $\lambda = 0.40$ | 0.3763 | 0.3937 | 0.3850 |
| $\lambda = 0.50$ | 0.3763 | 0.3931 | 0.3847 |

### Đối chiếu và giải thích tính nhất quán:
- **Tham số được chọn trên Tuning Set**: $\lambda^* = 0.10$ (In-Sample P@10 = 0.3812).
- **Kiểm tra trên Evaluation Set độc lập**: Out-of-Sample P@10 = **0.4000**.
- **Lưu ý diễn giải**: Với cài đặt hiện tại online model bị bão hòa xác suất (≈1.0 trên ứng viên) nên không làm thay đổi thứ hạng; kết quả này chưa phản ánh khả năng của việc học từ Like/Dislike.
- **Giải thích sự chênh lệch giữa Bảng 6 ($\lambda=0.00$ là 0.3913) và Bảng 1 (Tầng 1 là 0.3900)**:
  - Bảng 1 tính trung bình qua **toàn bộ 5 kịch bản**, trong đó có $m=0$ ($m=0$ đạt 0.3875, $m=1$ đạt 0.3475, $m=3$ đạt 0.4025, $m=5$ đạt 0.3850, $m=10$ đạt 0.4300 $\implies$ TB: 0.3900).
  - Bảng 6 **chỉ đo trên 4 kịch bản có tương tác** ($m \in \{1, 3, 5, 10\}$), loại trừ $m=0$ vì Online Model chỉ hoạt động khi có phản hồi nhãn 0 và 1. Điểm trung bình của Tầng 1 trên riêng 4 kịch bản này là $(0.3475 + 0.4025 + 0.3850 + 0.4300) / 4 = 0.3913$, hoàn toàn khớp 100% với điểm $\lambda=0.00$ trong Bảng 6.

## 5. Chẩn đoán chuyên sâu Online Model ở kịch bản $m=10$
> **Cấu hình**: $m=10$, 10 reps (rep 0-9), $s=1.0$, trọng số ranking mặc định, $\lambda=0.20$. Đánh giá trên toàn bộ 50 phim ứng viên và Top 10 của từng Persona.

### Bảng 7: Thống kê thứ hạng và phân bố xác suất `nn_like_probability` tại $m=10$

| Persona ID | Tên Persona | Số phim khác biệt Top 10 (diff) | Spearman Corr | Kendall Tau | Prob Min | Prob Median | Prob Max | Prob Std Dev |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1** | Modern Sci-Fi Explorer | 0.00 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 8.64e-08 |
| **P2** | Modern Horror Fan | 0.00 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5.24e-08 |
| **P3** | Classic Crime & Noir | 0.00 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.45e-10 |
| **P4** | Family Animation Lover | 0.10 | 0.9999 | 0.9985 | 0.9987 | 0.9996 | 1.0000 | 3.74e-04 |
| **P5** | Millennial Rom-Com | 0.00 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 9.36e-09 |
| **P6** | Action Thriller Buff | 0.00 | 1.0000 | 0.9998 | 0.9991 | 1.0000 | 1.0000 | 2.61e-04 |
| **P7** | World / Non-English Cinema | 0.00 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5.15e-09 |
| **P8** | Literary Adaptation Buff | 0.20 | 0.9917 | 0.9784 | 0.9556 | 1.0000 | 1.0000 | 1.62e-02 |

### Vì sao chênh lệch Tầng 2 trừ Tầng 1 ở $m=10$ đúng bằng 0?
1. **Hiện tượng bão hòa xác suất (Probability Saturation)**:
   - `OnlineLikeModel` sử dụng `SGDClassifier(loss='log_loss')`. Khi cập nhật online với 10 lượt Like và 3 lượt Dislike trên không gian đặc trưng 324 chiều không chuẩn hóa theo feature norm, hàm mất mát log_loss đẩy hệ số bias (intercept) và trọng số về phía dương rất mạnh.
   - Các ứng viên trong danh sách xét duyệt vốn đã là những phim có độ tương đồng Cosine rất cao với profile người dùng. Do đó, tích vô hướng $z = w \cdot x + b$ trên các ứng viên đều nhận giá trị dương rất lớn (thường từ $+25$ đến $+45$).
   - Khi đưa qua hàm sigmoid $\sigma(z) = \frac{1}{1 + e^{-z}}$, vì $z \ge 25$, $e^{-z} < 1.4 \times 10^{-11}$, dẫn đến `nn_like_probability` xấp xỉ hằng số **$1.0000$** trên hầu như toàn bộ 50 ứng viên (độ lệch chuẩn xác suất cực nhỏ, từ $10^{-8}$ đến $10^{-4}$).
2. **Thứ hạng không đổi (Monotonic Invariance)**:
   - Khi `nn_like_probability` $\approx 1.0$, công thức xếp hạng Tầng 2 trở thành:
     $$\text{final\_score} = (1 - \lambda) \cdot \text{ranking\_score} + \lambda \cdot 1.0$$
   - Đây là một phép biến đổi affine đơn điệu tăng (strictly monotonic transformation) của `ranking_score`. Thứ hạng của các phim ứng viên hoàn toàn được bảo toàn (hệ số tương quan hạng Spearman và Kendall xấp xỉ $1.0000$).
3. **Kết luận về $\Delta(\text{Tầng 2} - \text{Tầng 1}) = 0.0000$**:
   - Do thứ tự phim trong danh sách Top 10 của Tầng 2 giống hệt Tầng 1 (với 6/8 persona số phim khác biệt bằng đúng 0, và ở 2 persona còn lại sự hoán đổi hiếm hoi xảy ra giữa các phim cùng thuộc relevant pool), số phim đúng trong Top 10 hoàn toàn không đổi. Vì vậy, Precision@10 của Tầng 2 và Tầng 1 tại $m=10$ trùng khớp tuyệt đối, dẫn đến $\Delta = 0.0000$.
   - **Tổng kết**: Với cài đặt hiện tại online model bị bão hòa xác suất (≈1.0 trên ứng viên) nên không làm thay đổi thứ hạng; kết quả này chưa phản ánh khả năng của việc học từ Like/Dislike.

## 6. Hạn chế của Đánh Giá & Các Đe Dọa Tính Hợp Lệ (Threats to Validity)

1. **Đơn vị độc lập (Independent Unit)**: Đơn vị độc lập trong suy luận thống kê là **Persona** ($N=8$), không phải từng lượt chạy giả lập lặp lại. Các khoảng tin cậy được tính bằng cluster bootstrap resample qua 8 persona.
2. **Ưu thế cấu trúc ở kịch bản $m=0$**: Do thể loại onboarding trùng với điều kiện lọc của Persona (ví dụ P1 chọn Sci-Fi), kịch bản $m=0$ vốn dĩ đã có điểm khởi đầu rất cao. Khi người dùng bắt đầu Like các phim cụ thể kèm nhiễu, điểm có thể dao động trước khi hội tụ ở $m=10$.
3. **Những giải thích chưa kiểm chứng là Giả thuyết**: Các nhận định về nguyên nhân thất bại ở các ca cụ thể (như từ khóa TF-IDF làm sai lệch, sở thích ngách chưa nắm bắt) cần được coi là **giả thuyết**, đòi hỏi dữ liệu người dùng thật để kiểm chứng đầy đủ.
4. **An toàn dữ liệu**: 100% các thí nghiệm chạy trên bản sao tạm thời của SQLite và tự động dọn sạch sau khi hoàn tất. Không có dữ liệu giả nào lọt vào cơ sở dữ liệu thật.

