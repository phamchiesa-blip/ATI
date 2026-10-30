# Kết quả: Dislike không trừ ba chiều số

8 persona (N=8), 10 reps, seed gốc 42; cũ/mới ghép cặp theo persona và seed. CI 95% bootstrap 5.000 lần resample persona.

| Kịch bản | Cũ P@10 (95% CI) | Mới P@10 (95% CI) | Δ P@10 (95% CI) | Cũ rating top-10 (95% CI) | Mới rating top-10 (95% CI) | Δ rating (95% CI) |
|---|---:|---:|---:|---:|---:|---:|
| dislike_2_only | 0.287 [0.151, 0.436] | 0.350 [0.174, 0.529] | +0.063 [-0.024, +0.165] | 6.576 [6.351, 6.820] | 6.760 [6.568, 6.994] | +0.184 [+0.106, +0.267] |
| dislike_3_only | 0.252 [0.112, 0.397] | 0.300 [0.141, 0.461] | +0.047 [-0.003, +0.110] | 6.649 [6.376, 6.928] | 6.793 [6.576, 7.024] | +0.144 [+0.058, +0.226] |
| mixed_m1 | 0.354 [0.221, 0.486] | 0.394 [0.215, 0.565] | +0.040 [-0.054, +0.155] | 6.463 [6.264, 6.648] | 6.586 [6.382, 6.781] | +0.123 [+0.074, +0.162] |
| mixed_m3 | 0.405 [0.245, 0.566] | 0.422 [0.244, 0.601] | +0.018 [-0.027, +0.062] | 6.556 [6.351, 6.747] | 6.687 [6.424, 6.952] | +0.132 [+0.063, +0.207] |
| mixed_m5 | 0.380 [0.184, 0.597] | 0.409 [0.202, 0.622] | +0.029 [+0.002, +0.055] | 6.591 [6.312, 6.844] | 6.723 [6.417, 7.021] | +0.132 [+0.071, +0.200] |
| mixed_m10 | 0.420 [0.233, 0.620] | 0.443 [0.249, 0.664] | +0.022 [+0.001, +0.045] | 6.653 [6.380, 6.916] | 6.704 [6.422, 6.993] | +0.051 [+0.017, +0.086] |

## Kết luận

1. Ở ca chỉ Dislike, P@10 tăng theo trung bình (+0.063 với 2 Dislike; +0.047 với 3), nhưng CI của cả hai chênh lệch còn chứa 0; chưa đủ bằng chứng kết luận độ phù hợp tăng.
2. Rating top-10 tăng +0.184 và +0.144 ở hai ca chỉ Dislike; CI bootstrap của chênh lệch đều trên 0.
3. Ở ca hỗn hợp, P@10 không giảm; chênh lệch có CI trên 0 ở m=5 và m=10, còn m=1 và m=3 chưa chắc chắn. Rating top-10 trung bình tăng ở cả bốn ca.
4. Đây là benchmark trên 8 persona giả lập; kết quả không thay thế đánh giá với lịch sử người dùng thật.
