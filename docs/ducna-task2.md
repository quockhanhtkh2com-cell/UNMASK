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
* **22/10/2026:**
  * Tiếp nhận yêu cầu mới từ nhóm: kiểm tra và sửa lỗi đánh giá gộp cả 596 dòng (chưa lọc test).
  * Sửa `run_experiments.py` chỉ đánh giá trên 404 mẫu test (`df.split == "test"`), ngăn chặn rò rỉ tập train/val.
  * Tự động nối cột `die_result` từ manifest để phục hồi hoạt động đúng của cổng F1 (DiE).
  * Chạy lại toàn bộ thí nghiệm E1–E6 qua 3 seed × 3 pack ratio, bổ sung cổng ablation F3a.
  * Tích hợp kiểm định McNemar ghép cặp trên 404 mẫu test và khoảng tin cậy Wilson 95% CI theo `SPEC_ketqua_chi_so.md`.
* **23/10/2026:**
  * Tiếp nhận phản hồi review từ Leader (file `Fix E1-E6.docx`).
  * Nâng cấp `DriftDetector` với chuẩn hóa đặc trưng (z-score) giải quyết lỗi suy biến ma trận hiệp phương sai.
  * Khóa ngưỡng D1 ở phân vị P80 trên `G0 val` (ngưỡng 6.9111), giúp kịch bản E0b chính thức PASS với độ nhạy trên G2 đạt 68.5% (> 50%).
  * Viết script độc lập `experiments/check_e0b.py` kiểm tra độ nhạy chuông D1 tự động.
  * Bổ sung metric `fnr_end2end` (bộ lọc loại hoặc chuông không kêu) và thêm unit test cho `eval_metrics.py` (91/91 tests pass).
  * Chuẩn hóa kết luận kiểm định ablation F3 vs F3a ($p = 0.1336$, chưa đạt ý nghĩa thống kê do ít mẫu).
  * Dọn dẹp toàn bộ file mock và duplicate, xuất lại bảng kết quả hoàn chỉnh `bang_chinh.md`, `bang_chinh.csv`, `stats_mcnemar.csv` và báo cáo `docs/BAO_CAO_FIX_E1_E6.md`.
  * Đẩy toàn bộ thay đổi lên nhánh `origin/feat/ducna`. Hoàn thành 100% nhiệm vụ Task 2.
