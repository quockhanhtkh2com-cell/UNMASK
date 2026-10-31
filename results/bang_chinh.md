# Bảng chính F0–F3 — v1.1 (Số liệu thực nghiệm)

> Đã chạy E1–E6 trên `dataset_v1.1.csv`. FTR@30/@70 là mean ± std qua 3 seed (kịch bản mô phỏng tỉ lệ pack); FNR_G2/G3, FNR_e2e_G2/G3, correct_Pseen/Punseen, flagged_rate tính trực tiếp 1 lần trên 404 mẫu test đầy đủ — kèm Wilson 95% CI, cùng nguồn với điểm ước lượng (sửa M1: không còn trộn seed-mean với full-set CI).

> Dataset test = 404 mẫu · F3 khóa 0.475 · D1 khóa 6.9111 (P80 chuẩn hóa) · P-low/P-wild = "—" (không có ở v1.1).


## Bảng chính (FTR kèm tỉ lệ pack; FNR tách G2/G3; FNR_e2e toàn trình)


| gate | FTR@30 | FTR@50 | FTR@70 | FNR_G2 (filter) | FNR_G3 (filter) | FNR_e2e_G2 | FNR_e2e_G3 | correct_Pseen | correct_Punseen | correct_Plow | correct_Pwild | flagged_rate |
|:----:|:------:|:------:|:------:|:---------------:|:---------------:|:-----------:|:-----------:|:-------------:|:---------------:|:------------:|:-------------:|:------------:|
| F0 | `0.127 ± 0.004` | `0.158 ± 0.001` [0.121, 0.201] | `0.202 ± 0.015` | `0.000` [0.000, 0.023] | `0.000` [0.000, 0.024] | `0.315` [0.249, 0.390] | `0.000` [0.000, 0.024] | `0.000` [0.000, 0.204] | `0.000` [0.000, 0.099] | — | — | 0 |
| F1-oracle | `0.000 ± 0.000` | `0.000 ± 0.000` [0.000, 0.032] | `0.000 ± 0.000` | `0.000` [0.000, 0.023] | `1.000` [0.976, 1.000] | `0.315` [0.249, 0.390] | `1.000` [0.976, 1.000] | `1.000` [0.796, 1.000] | `1.000` [0.901, 1.000] | — | — | 0 |
| F1-DiE | `0.000 ± 0.000` | `0.000 ± 0.000` [0.000, 0.033] | `0.000 ± 0.000` | `0.012` [0.003, 0.043] | `1.000` [0.976, 1.000] | `0.327` [0.260, 0.402] | `1.000` [0.976, 1.000] | `1.000` [0.796, 1.000] | `1.000` [0.901, 1.000] | — | — | 0 |
| F1-DiE+protected | `0.000 ± 0.000` | `0.000 ± 0.000` [0.000, 0.033] | `0.000 ± 0.000` | `0.042` [0.021, 0.085] | `1.000` [0.976, 1.000] | `0.333` [0.266, 0.408] | `1.000` [0.976, 1.000] | `1.000` [0.796, 1.000] | `1.000` [0.901, 1.000] | — | — | 0 |
| F2 | `0.064 ± 0.028` | `0.088 ± 0.010` [0.069, 0.154] | `0.144 ± 0.018` | `0.097` [0.061, 0.152] | `0.464` [0.387, 0.543] | `0.412` [0.340, 0.488] | `0.464` [0.387, 0.543] | `1.000` [0.796, 1.000] | `0.400` [0.256, 0.564] | — | — | 0 |
| F3 | `0.059 ± 0.025` | `0.082 ± 0.008` [0.063, 0.142] | `0.136 ± 0.014` | `0.012` [0.003, 0.043] | `0.438` [0.362, 0.517] | `0.327` [0.260, 0.402] | `0.438` [0.362, 0.517] | `1.000` [0.796, 1.000] | `0.400` [0.256, 0.564] | — | — | `0.010` [0.004, 0.025] |
| F3a | `0.059 ± 0.025` | `0.083 ± 0.008` [0.064, 0.144] | `0.139 ± 0.015` | `0.012` [0.003, 0.043] | `0.464` [0.387, 0.543] | `0.327` [0.260, 0.402] | `0.464` [0.387, 0.543] | `1.000` [0.796, 1.000] | `0.400` [0.256, 0.564] | — | — | 0 |

* Chú thích: `FNR_G2/G3` = tỉ lệ bỏ sót do bộ lọc loại nhầm; `FNR_e2e` = tỉ lệ bỏ sót toàn trình (bộ lọc loại HOẶC chuông D1 không kêu).
* `FNR_G2/G3`, `FNR_e2e_G2/G3`, `correct_Pseen/Punseen`, `flagged_rate`: tính 1 lần trực tiếp trên 404 mẫu test đầy đủ (không resample, không trung bình qua seed) — điểm ước lượng và `[...]` Wilson 95% CI [lo, hi] cùng 1 nguồn dữ liệu.
* `FTR@50` kèm Wilson 95% CI tính trực tiếp trên 404 mẫu test (kịch bản pack-ratio mặc định). `FTR@30`/`FTR@70` là mean ± std qua 3 seed từ các kịch bản mô phỏng tỉ lệ pack khác, hiện chưa có CI riêng (cần lưu thêm số đếm thô theo từng tỉ lệ) nên không hiển thị CI để tránh hiểu nhầm.*


## Bảng kiểm định McNemar (ghép cặp trên cùng 404 mẫu test)


| So sánh | b (F3 đúng, kia sai) | c (F3 sai, kia đúng) | p-value | Kết luận |
|:---|:---:|:---:|:---:|:---|
| F3 vs F1-DiE (DiE packed) | `86` | `21` | `6.13e-10` | Ý nghĩa thống kê (p_Holm = 1.84e-09 < 0.05) |
| F3 vs F1-DiE+protected (DiE packed+protected) | `93` | `21` | `2.94e-11` | Ý nghĩa thống kê (p_Holm = 1.17e-10 < 0.05) |
| F3 vs F2 (entropy) | `20` | `0` | `2.15e-05` | Ý nghĩa thống kê (p_Holm = 4.30e-05 < 0.05) |
| F3 vs F3a (ablation) | `4` | `0` | `0.1250` | Không đạt ý nghĩa (p_Holm = 0.1250; p_orig = 0.1250) |

> Kết quả đo trực tiếp theo config khóa: F3=0.475, D1=6.9111 (P80 chuẩn hóa) trên 404 mẫu test độc lập.
