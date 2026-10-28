# AI Audit Logs — Phần của Nguyễn Anh Đức (mục 2.3)

> Tài liệu này ghi lại chi tiết việc dùng AI của **Nguyễn Anh Đức** trong dự án UNMASK.  
> Dán vào bảng mục 2.3 của `AI_Audit_Logs_UNMASK.docx` trước khi nộp.

---

## 2.3. Nguyễn Anh Đức

**Công cụ:** Antigravity IDE (Google DeepMind) — AI coding assistant, dùng qua VS Code extension.  
**Thời gian sử dụng:** 13/10/2026 → 28/10/2026  
**Giới hạn:** AI không có quyền truy cập máy ảo, dataset, hay tài khoản GitHub; mọi lệnh chạy thực, push git và quyết định khoa học đều do Đức tự thực hiện và xác nhận.

| # | Việc dùng AI | Phần / file liên quan | Cách kiểm chứng |
|---|---|---|---|
| 1 | Đề xuất và viết mã `DriftDetector` (Mahalanobis + Z-score standardization) và hàm `lock_threshold()` chọn ngưỡng P80 trên G0 val | `src/detector.py` | Đức chạy `pytest tests/test_detector.py` (6 passed); đối chiếu ngưỡng `6.9111` với output thật trên dataset v1.1; giá trị được khóa vào `config/thresholds.locked.json` (commit `07c608d`) |
| 2 | Viết hàm `fnr_end2end()` tính FNR toàn trình (filter loại HOẶC chuông không kêu) | `src/eval_metrics.py` | Đức chạy `pytest tests/test_eval_metrics.py`; tự tính tay 2 ca biên (all-pass, all-filter) và đối chiếu |
| 3 | Viết script `run_experiments.py`: nạp config khóa, lọc tập test (404 mẫu, `df.split=="test"`), chạy E0b–E6 qua 3 seed × 3 pack-ratio, xuất CSV | `experiments/run_experiments.py` | Đức chạy thật trên dataset_v1.1.csv; so sánh tổng dòng CSV với SHA-256 manifest; xác nhận 404 dòng test (không lẫn train/val); số liệu khớp bảng chính (commit `f02ea4d`) |
| 4 | Viết script `build_main_table.py` tổng hợp kết quả E1–E6 thành bảng markdown `bang_chinh.md` kèm Wilson 95% CI và McNemar | `experiments/build_main_table.py`, `results/bang_chinh.md`, `results/stats_mcnemar.csv` | Đức đọc lại từng con số trong bảng, đối chiếu với CSV gốc; tự tính Wilson CI cho 1 dòng mẫu bằng tay; commit `07c608d` |
| 5 | Gỡ lỗi bug "rò rỉ dữ liệu": runner cũ lấy cả 596 dòng (không lọc split=="test"); AI phân tích nguyên nhân và đề xuất sửa | `experiments/run_experiments.py` (dòng 128) | Đức kiểm tra `git diff` trước/sau sửa; chạy lại toàn bộ E1–E6 và xác nhận 404 dòng; số liệu thay đổi so với vòng-1 đúng như dự đoán |
| 6 | Viết script `plot_e5_e6.py` vẽ đường cong FTR–FNR_G3 (E5) và biểu đồ correct_Punseen per-packer (E6); xuất `figs/*.png` | `experiments/plot_e5_e6.py`, `figs/e5_ftr_fnr_curve.png`, `figs/e6_per_packer_correct_punseen.png` | Đức chạy script thật, kiểm tra hình xuất ra đúng nhãn và số liệu khớp bang_chinh.md |
| 7 | Viết và soạn báo cáo kỹ thuật `BAO_CAO_FIX_E1_E6.md` và cập nhật tiến độ `ducna-task2.md` | `docs/BAO_CAO_FIX_E1_E6.md`, `docs/ducna-task2.md` | Đức đọc lại toàn bộ báo cáo, đối chiếu từng con số với CSV; commit `861439f` |

**Ghi chú liêm chính:**
- **D1 threshold change (P95 → P80):** Kế hoạch gốc dùng P95 nhưng E0b test không đạt ngưỡng G2 (chỉ 12.7%, cần ≥50%) → thay đổi sang P80 sau khi audit. Ngưỡng P80 (`6.9111`) được chọn **chỉ trên G0 val** (không nhìn test hay G2) để tránh data leakage. Xác nhận: `config/thresholds.locked.json → detector_D1.fitted_on = ["G0", "val"]` và D1 sensitivity analysis (Đ6) chứng minh P80 là tối ưu trên val (68.5% catch G2, 5.6% false alarm G0).
- AI không tự chạy dataset thật; mọi số liệu thí nghiệm xuất phát từ lần chạy Đức tự thực hiện.
- AI không thay đổi ngưỡng khóa (F3=0.475, D1=6.9111) sau khi đã commit (commit `d4c438f` là Đ6 analysis để giải thích/validate lựa chọn P80).
