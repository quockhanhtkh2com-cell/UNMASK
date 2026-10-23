# Báo Cáo Xử Lý Phản Hồi Review E1–E6 (UNMASK v1.1)

**Người gửi:** Nguyễn Anh Đức  
**Người nhận:** Quốc Khánh (Leader), Bảo Trúc, Minh Tuấn  
**Dự án:** UNMASK — Vỏ đổi hay lõi đổi? (IAM302t · Nhóm 1)  
**Thời gian hoàn thành:** 23/10/2026  
**Nhánh Git:** `feat/ducna`  

---

## 1. Tóm tắt kết quả xử lý các phản hồi từ Leader

| STT | Vấn đề / Yêu cầu review | Phương án xử lý | Kết quả thực tế |
|:---:|:---|:---|:---:|
| 1 | **Chuông D1 bị "điếc"** (chỉ kêu 12.7% trên G2, E0b fail) | Tích hợp chuẩn hóa đặc trưng (z-score) vào `DriftDetector`, hạ phân vị về P80 trên `G0 val`, khóa ngưỡng `6.9111` | **PASS E0b**: Báo drift trên **68.5% G2** ($113/165$), báo nhầm trên G0 sạch chỉ **5.6%** ($2/36$). |
| 2 | **Script E0b thành check thật** | Viết script độc lập `experiments/check_e0b.py` đo độ nhạy chuông trên G2 với ngưỡng tối thiểu $\ge 50\%$ | Script in rõ log định lượng, trả về exit code 0 khi **PASS**. |
| 3 | **Bổ sung cột `FNR_end2end`** | Thêm hàm `fnr_end2end` vào `src/eval_metrics.py`, tính tỉ lệ mẫu drift bị cổng loại HOẶC chuông D1 bỏ sót | Đã thêm vào `bang_chinh.md` & `bang_chinh.csv`, phân tách rõ FNR của bộ lọc vs FNR toàn trình. |
| 4 | **Sửa câu kết luận Ablation (F3 vs F3a)** | Cập nhật câu kết luận chuẩn thống kê cho $p = 0.1336 > 0.05$ | Đã sửa trong `build_main_table.py`, `stats_mcnemar.csv` và `bang_chinh.md`. |
| 5 | **Dọn dẹp file thừa & chống trùng lặp** | Bỏ cơ chế ghi kép trong `run_experiments.py`; xóa toàn bộ file mock và thư mục `results/v1.1` cũ | Thư mục `results/` chỉ còn các file chuẩn `results_*_0_xx.csv`, không còn tình trạng đếm trùng. |
| 6 | **Đánh giá chống rò rỉ & Fix cổng F1** | Đánh giá độc lập trên đúng 404 mẫu test; tự động nạp `die_result` từ manifest | Cổng F1 hoạt động đúng chuẩn baseline; 404 mẫu test không bị rò rỉ dữ liệu học. |

---

## 2. Bảng kết quả chính (F0–F3a) trên 404 mẫu test

> **Điều kiện thực nghiệm:** Dataset test = 404 mẫu (`dataset_v1.1.csv`).  
> **Config khóa:** F3 khóa 0.475; D1 khóa 6.9111 (P80 chuẩn hóa Z-score).  
> **Quy ước:** `±` là độ lệch chuẩn qua 3 seed ($0, 1, 2$); trong ngoặc vuông `[...]` là khoảng tin cậy Wilson 95% CI.  

| gate | FTR@30 | FTR@50 | FTR@70 | FNR_G2 (filter) | FNR_G3 (filter) | FNR_e2e_G2 | FNR_e2e_G3 | correct_Pseen | correct_Punseen | correct_Plow | correct_Pwild | flagged_rate |
|:----:|:------:|:------:|:------:|:---------------:|:---------------:|:-----------:|:-----------:|:-------------:|:---------------:|:------------:|:-------------:|:------------:|
| **F0** | `0.129 ± 0.002` | `0.156 ± 0.002` | `0.157 ± 0.000` | `0.000 ± 0.000` [0.000, 0.023] | `0.000 ± 0.000` [0.000, 0.024] | `0.315 ± 0.000` [0.249, 0.390] | `0.000 ± 0.000` [0.000, 0.024] | `0.000` [0.000, 0.204] | `0.000` [0.000, 0.099] | — | — | 0 |
| **F1** | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000 ± 0.000` | `0.000 ± 0.000` [0.000, 0.023] | `1.000 ± 0.000` [0.976, 1.000] | `0.315 ± 0.000` [0.249, 0.390] | `1.000 ± 0.000` [0.976, 1.000] | `1.000` [0.796, 1.000] | `1.000` [0.901, 1.000] | — | — | 0 |
| **F2** | `0.068 ± 0.006` | `0.102 ± 0.003` | `0.104 ± 0.000` | `0.097 ± 0.000` [0.061, 0.152] | `0.452 ± 0.019` [0.387, 0.543] | `0.412 ± 0.000` [0.340, 0.488] | `0.452 ± 0.019` [0.387, 0.543] | `1.000` [0.796, 1.000] | `0.414` [0.256, 0.564] | — | — | 0 |
| **F3** | `0.062 ± 0.006` | `0.094 ± 0.002` | `0.095 ± 0.000` | `0.012 ± 0.000` [0.003, 0.043] | `0.429 ± 0.015` [0.362, 0.517] | `0.327 ± 0.000` [0.260, 0.402] | `0.429 ± 0.015` [0.362, 0.517] | `1.000` [0.796, 1.000] | `0.414` [0.256, 0.564] | — | — | `0.008 ± 0.003` [0.004, 0.025] |
| **F3a** | `0.062 ± 0.006` | `0.095 ± 0.002` | `0.097 ± 0.000` | `0.012 ± 0.000` [0.003, 0.043] | `0.452 ± 0.019` [0.387, 0.543] | `0.327 ± 0.000` [0.260, 0.402] | `0.452 ± 0.019` [0.387, 0.543] | `1.000` [0.796, 1.000] | `0.414` [0.256, 0.564] | — | — | 0 |

### Phân tích ý nghĩa học thuật từ kết quả:
1. **Sự cần thiết của UNMASK (F3 so với F0):** Khi chuông D1 nhạy, F0 (không lọc) bị báo động nhầm rất nhiều do mẫu G1 lọt vào chuông ($FTR = 15.7\%$). Cổng F3 giúp kéo giảm đáng kể FTR xuống còn $9.5\%$, chứng minh vai trò thực sự của bộ lọc vỏ.
2. **Khắc phục nhược điểm "mù drift" của Detect It Easy (F3 so với F1):** F1 lọc sạch mẫu pack nên đạt $FTR = 0\%$, nhưng đánh đổi bằng việc **bỏ sót 100% mẫu G3** (malware đổi cả lõi lẫn vỏ). F3 giải quyết trọn vẹn điểm nghẽn này khi giữ lại được đa số mẫu G3.
3. **Đóng góp của Dual-Check (F3 so với F3a):** F3 giảm $FNR_{G3}$ từ $45.2\%$ xuống $42.9\%$ (cứu được 4 mẫu malware họ mới bị pack nhầm sang G1).

---

## 3. Bảng kiểm định McNemar (Ghép cặp trên 404 mẫu test)

File lưu trữ: `results/stats_mcnemar.csv`

| So sánh | b (F3 đúng, kia sai) | c (F3 sai, kia đúng) | Chi-square stat | p-value | Kết luận khoa học |
|:---|:---:|:---:|:---:|:---:|:---|
| **F3 vs F1 (DiE)** | 86 | 23 | 35.2661 | **$2.88 \times 10^{-9}$** | **F3 vượt trội có ý nghĩa thống kê** ($p < 0.001$). |
| **F3 vs F2 (Entropy)** | 20 | 0 | 18.0500 | **$2.15 \times 10^{-5}$** | **F3 vượt trội có ý nghĩa thống kê** ($p < 0.001$). |
| **F3 vs F3a (Ablation)** | 4 | 0 | 2.2500 | **$0.1336$** | **dual-check cho thấy xu hướng có lợi (cứu 4 mẫu G3) nhưng chưa đạt ý nghĩa thống kê (p=0.13, do ít mẫu)**. |

---

## 4. Danh mục file đã cập nhật & cam kết bàn giao

1. **Mã nguồn:**
   - `src/detector.py`: Thêm Z-score standardization và xử lý ma trận hiệp phương sai.
   - `src/eval_metrics.py`: Thêm metric `fnr_end2end`.
   - `tests/test_eval_metrics.py`: Bổ sung unit test cho `fnr_end2end` (91/91 tests pass).
   - `experiments/check_e0b.py`: Script kiểm tra E0b tự động.
   - `experiments/run_experiments.py`: Cập nhật lưới chạy, nạp ngưỡng D1 khóa và xuất chuẩn tên file `results_*_0_xx.csv`.
   - `experiments/build_main_table.py`: Xuất bảng chính kèm FNR filter & end-to-end, câu kết luận ablation chuẩn.
2. **Dữ liệu cấu hình & Kết quả:**
   - `config/thresholds.locked.json`: Khóa ngưỡng D1 = 6.9111 (P80 chuẩn hóa).
   - `results/bang_chinh.md`: Bảng Markdown hoàn chỉnh điền số thật.
   - `results/bang_chinh.csv`: Bảng CSV số thuần phục vụ vẽ biểu đồ (Trúc) và báo cáo (Khánh).
   - `results/stats_mcnemar.csv`: Bảng kiểm định thống kê McNemar.
   - Toàn bộ các file kết quả lưới `results/results_*.csv` ($e0b, e1..e6$).
