# SPEC — Bảng kết quả & chỉ số báo cáo (UNMASK v1.1)

> **Mục đích:** chốt ĐÚNG tên cột + chỉ số + quy ước file để E1–E6 xuất **một lần là khớp**, khỏi sửa tới sửa lui.
> **Dataset:** `dataset_v1.1.csv` (SHA-256 `caed7ef9…02bdeb82`), tập **test = 404 mẫu**.
> **F3 đã khóa 0.475** (`config/thresholds.locked.json`) — **KHÔNG chỉnh ngưỡng sau khi xem điểm.**
> **Người thực hiện:** Đức · **Người nhận kế:** Trúc (vẽ hình) + Khánh (viết Results).

---

## 1. Quy ước tên file

| Loại | Tên | Sinh bởi |
|---|---|---|
| Kết quả trung gian | `results/results_<exp>_<seed>_<packratio>.csv` | `run_experiments.py` |
| Bảng tổng hợp | `results/bang_chinh.csv` + `results/bang_chinh.md` | `build_main_table.py` |
| Bảng kiểm định | `results/stats_mcnemar.csv` *(mới)* | `build_main_table.py` (đấu nối `eval_metrics`) |

- `exp` ∈ `{e0b, e1, e2, e3, e4, e5, e6}` · `seed` ∈ `{0, 1, 2}` · `packratio` ∈ `{0_30, 0_50, 0_70}`.
- Tên file: **chữ thường, gạch dưới, không dấu** (đúng quy ước nhóm).

## 2. Cột BẮT BUỘC của `bang_chinh` (mỗi dòng = 1 cổng)

Các dòng: **F0 · F1 · F2 · F3 · F3a** (F3a = F3 bỏ dual-check, dòng ablation).

| Cột | Nghĩa | Kèm CI? |
|---|---|:---:|
| `gate` | tên cổng (F0/F1/F2/F3/F3a) | — |
| `FTR@30`, `FTR@50`, `FTR@70` | tỉ lệ báo nhầm drift do đổi vỏ, theo tỉ lệ pack 0.3/0.5/0.7 | ✅ Wilson 95% |
| `FNR_G2` | bỏ sót drift thật ở nhóm "đổi lõi" (G2) | ✅ Wilson 95% |
| `FNR_G3` | bỏ sót drift thật ở nhóm "đổi cả hai" (G3) | ✅ Wilson 95% |
| `correct_Pseen` | lọc đúng packer đã gặp (UPX) | ✅ |
| `correct_Punseen` | lọc đúng packer CHƯA gặp (MPRESS) — **chỉ số tổng quát hóa** | ✅ |
| `correct_Plow` | *(N/A ở v1.1 — để trống "—")* | — |
| `correct_Pwild` | *(N/A ở v1.1 — để trống "—")* | — |
| `flagged_rate` | tỉ lệ bị gắn cờ FLAGGED (pack nhưng ruột lạ) | ✅ |

→ Mỗi ô tỉ lệ: báo **mean ± std qua 3 seed**, kèm **Wilson 95% CI**.

## 3. Chỉ số theo chuẩn Q4 (đủ 5 trụ)

1. **Point estimate:** FTR theo từng tỉ lệ pack; FNR **tách riêng G2 vs G3**; correct-filter theo biến thể; flagged_rate.
2. **Wilson 95% CI** cho MỌI tỉ lệ — hàm `wilson_ci()` đã có trong `src/eval_metrics.py`, chỉ cần gọi.
3. **McNemar** (ghép cặp, vì các cổng chấm *cùng* 404 mẫu test): **F3 vs F1**, **F3 vs F2**, **F3 vs F3a** → xuất `p-value` + đếm `b,c` ra `results/stats_mcnemar.csv`.
4. **Variance:** mean ± std qua **3 seed × 3 pack-ratio**.
5. **Ablation:** **F3a** (`--no-dualcheck`) là **một dòng riêng** trong bảng để đo công của dual-check.

## 4. Lưu ý v1.1 (đọc kỹ kẻo hiểu nhầm)

- **P-low / P-wild KHÔNG có trong v1.1** → 2 cột đó để **"—"** (đúng thiết kế, không phải lỗi).
- **P-seen = UPX** (native). **P-unseen = MPRESS** (gồm cả .NET). Học bằng UPX, thi bằng MPRESS.
- **Tập test 404 mẫu**, toàn bộ **G2/G3 (origin "đổi lõi") nằm ở test** — chống rò rỉ.
- **E0b chạy TRƯỚC:** nếu chuông D1 không báo drift trên phần lớn G2 → dừng, báo nhóm (FNR sẽ vô nghĩa).

## 5. Checklist Đức tick trước khi giao

- [ ] E0b pass (chuông nhạy trên G2)
- [ ] Đủ `results_*.csv` cho e1–e6 × 3 seed × 3 pack
- [ ] `bang_chinh.csv/.md` = **số thật** (không còn số mock)
- [ ] Mọi tỉ lệ có **± Wilson CI**
- [ ] `stats_mcnemar.csv` có p-value cho F3vsF1, F3vsF2, F3vsF3a
- [ ] **F3a** có mặt trong bảng
- [ ] Dùng đúng `--f3-config config/thresholds.locked.json` (không train lại)

---

*File này là HỢP ĐỒNG định dạng đầu ra. Đức xuất theo đây → Trúc vẽ & Khánh viết khỏi sửa định dạng.*
