# Báo cáo Tiến độ Công việc - Task 2: Drift Detector D1 & Thử nghiệm

**Thực hiện:** Đức  
**Dự án:** UNMASK — Vỏ đổi hay lõi đổi? (IAM302t - Nhóm 1)  
**Mốc thời hạn:** 13/10/2026 (Detector D1) & 16/10/2026 (Kết quả thí nghiệm E1–E6)  

---

## 1. Mục tiêu công việc

Xây dựng bộ phát hiện bất thường Drift Detector D1 (sử dụng thuật toán Mahalanobis Distance hoặc Isolation Forest) đóng vai trò làm chuông cảnh báo chung cho cả 4 cổng lọc (F0, F1, F2, F3).

Mô hình D1 được huấn luyện (`fit`) trên tập mẫu lành tính thuộc tập `train`, khóa ngưỡng cảnh báo ở phân vị 95% (Percentile 95) trên tập `val`, sau đó đánh giá hiệu năng trên tập `test` qua các kịch bản thí nghiệm (E0b đến E6).

---

## 2. Hiện trạng dữ liệu (Data Status)

File dữ liệu thử nghiệm: `mock/mock_dataset.csv`

* Tổng số mẫu: 112 dòng (28 origin_sha256 độc nhất).
* Phân chia tập dữ liệu (`split`):
  * Tập `train`: 37 dòng (G0: 7, G1: 30) — Dùng để fit mô hình.
  * Tập `val`: 11 dòng (G0: 2, G1: 9) — Dùng để khóa ngưỡng P95.
  * Tập `test`: 64 dòng (G0: 3, G1: 13, G2: 12, G3: 36) — Dùng để đánh giá đề thi.
* Kiểm tra chất lượng dữ liệu (`check_data.py`): Đạt PASS toàn bộ 8/8 tiêu chí, 0% rò rỉ dữ liệu giữa các tập.

---

## 3. Danh sách công việc chi tiết (Checklist)

### Giai đoạn 1: Chuẩn bị & Cập nhật mã nguồn
- [x] **Task 2.1:** Cập nhật luồng huấn luyện D1 trong `experiments/run_experiments.py`.
  - Cấu hình D1 `fit()` trên tập `G0` thuộc `train`.
  - Cấu hình D1 `lock_threshold(p=95)` trên tập `G0` thuộc `val`.
  - Bổ sung tham số dòng lệnh `--detector` cho phép chọn `mahalanobis` hoặc `isolation_forest`.
- [x] **Task 2.2:** Viết Unit Test cho `DriftDetector` tại `tests/test_detector.py`.
  - Kiểm tra tính đúng đắn của các hàm `fit()`, `score()`, `lock_threshold()`, `predict()`.
  - Ràng buộc báo lỗi nếu gọi `predict()` khi chưa khóa ngưỡng.

### Giai đoạn 2: Thực thi thí nghiệm & Tổng hợp kết quả
- [x] **Task 2.3:** Chạy driver thí nghiệm `experiments/run_experiments.py` trên mock data.
  - Chạy quét qua các hạt giống (`seed`: 0, 1, 2) và các tỉ lệ pack (`pack-ratio`: 0.3, 0.5, 0.7).
  - Xuất các file kết quả trung gian `results/results_<exp>_<seed>_<pack_ratio>.csv`.
- [x] **Task 2.4:** Tổng hợp bảng kết quả chính bằng `experiments/build_main_table.py`.
  - Đọc toàn bộ các file `results_*.csv`.
  - Tính trung bình các chỉ số FTR@50%, FNR G2, FNR G3, tỉ lệ lọc đúng P-seen/unseen/low/wild.
  - Xuất bảng kết quả cuối cùng ra `results/bang_chinh.csv` và `results/bang_chinh.md`.

### Giai đoạn 3: Kiểm thử toàn hệ thống
- [x] **Task 2.5:** Chạy bộ kiểm thử tự động `pytest -q` đảm bảo toàn bộ hệ thống đạt chuẩn.

---

## 4. Nhật ký tiến độ (Progress Log)

* **07/10/2026:**
  * Đã đọc và trích xuất yêu cầu chi tiết từ tài liệu phân công tuần 5-6 và file ảnh `requirements.png`.
  * Đã kiểm tra tính hợp lệ của tập dữ liệu `mock/mock_dataset.csv`, xác nhận đạt 8/8 tiêu chí an toàn dữ liệu và 0% rò rỉ split.
  * Đã khởi tạo file theo dõi tiến độ `ducna-task2.md`.
  * Hoàn thành **Task 2.1**: Cập nhật `experiments/run_experiments.py` tự động fit D1 trên G0 `train`, lock P95 trên G0 `val`, thêm cờ `--detector` hỗ trợ lựa chọn Mahalanobis hoặc Isolation Forest. Đã chạy thử nghiệm thành công cả 2 phương pháp.
  * Hoàn thành **Task 2.2**: Tạo bộ unit test `tests/test_detector.py` bao phủ toàn bộ API `DriftDetector` (Assertion lỗi method rác, kiểm tra ném RuntimeError khi gọi predict trước khi lock threshold, test fit/score/lock_threshold/predict cho cả 2 thuật toán Mahalanobis & Isolation Forest). Đã chạy `pytest` vượt qua toàn bộ 11/11 tests.
  * Hoàn thành **Task 2.3**: Chạy lưới thí nghiệm e2 trên mock data qua 3 seed (0, 1, 2) x 3 tỉ lệ pack (0.3, 0.5, 0.7). Tất cả 9 file `results_e2_*.csv` đã được tự động sinh ra trong thư mục `results/`.
  * Hoàn thành **Task 2.4**: Thực thi `build_main_table.py` tổng hợp 9 file kết quả thí nghiệm ra `results/bang_chinh.csv` và `results/bang_chinh.md` (trung bình FTR@50%, FNR G2/G3, correct_filter, flagged_rate cho 4 cổng F0-F3).
  *  **Task 2.5**: Đã chạy bộ test tự động `pytest -q`, 100% test pass (11/11 tests).
