# PHÂN CÔNG & HỢP ĐỒNG BÀN GIAO — Nhóm 4 · IAM302t
Khoảng thời gian: 05/10 – 18/10/2026. Hạn chót: **18/10** pip + demo chạy được.

## Ai nhận gì / giao gì
| Người | Giai đoạn | Nhận | Giao |
|---|---|---|---|
| **Khánh** (leader) | GĐ1 — Dữ liệu | script feature từ Tuấn | `dataset.csv` + `manifest.csv` cho Đức & Trúc |
| **Tuấn** | GĐ1 feature + GĐ2 UNMASK | — | `extract_features.py` cho Khánh; `unmask/` (F3+F3a) cho Đức |
| **Đức** | GĐ2 detector + GĐ3 đo | `dataset.csv`, `eval_metrics.py`, F1/F2/F3 | `results_*.csv` + `bang_chinh` cho cả nhóm |
| **Trúc** | GĐ3 metric/biểu đồ + GĐ4 demo | `dataset.csv` | `eval_metrics.py` + F1/F2 cho Đức; demo |

## "Xong" một việc = (bắt buộc đủ 4)
1. Merge vào `main` qua Pull Request (≥1 người review).
2. Chạy được trên **mock** rồi trên **dữ liệu thật** không lỗi.
3. Có file output đúng **tên & định dạng** (xem `schema.md`).
4. Người nhận kế tiếp dùng được.

## Khoá đề thi (TRƯỚC khi chạy E3–E5)
Commit lên git: config ngưỡng/trọng số/seed + SHA-256 tập test (`config/thresholds.locked.json`).
**Không chỉnh ngưỡng sau khi nhìn đề thi.**

## Lịch
- Họp nhanh mỗi tối **21:00** (15') trên Discord: hôm qua xong gì / nay làm gì / kẹt gì.
- Họp cổng: **T5 08/10** (chốt VM + schema + script feature) · **CN 18/10** (nghiệm thu demo).

## Git
- `main` sạch. Mỗi người nhánh `feat/<ten>-<viec>`, merge qua PR.
- **KHÔNG commit mẫu / file đã pack** (chỉ feature, hash, script).
