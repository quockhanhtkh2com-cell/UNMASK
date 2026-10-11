# UNMASK — dataset.csv (BẢN PILOT) — giao team 2026-10-11

## Tóm tắt
Dataset đặc trưng tĩnh (static features) cho đề tài "Vỏ đổi hay lõi đổi?".
**189 dòng**, trích bằng `extract_features.py` (cùng 1 công cụ cho mọi nhóm).

| Nhóm | Số mẫu | Là gì | is_drift_truth |
|---|---|---|---|
| G0 | 53 | AgentTesla lõi sạch (36 .NET + 17 native) | 0 |
| G1 | 17 | G0 (native) bị pack UPX = "đổi vỏ" | 0 |
| G2 | 119 | 8 họ khác (MOTIF) = "đổi lõi" | 1 |

Split (theo `origin_sha256`, **chống leakage** — mọi biến thể cùng gốc nằm cùng tập):
- train 37 · val 13 · test 139 (toàn bộ G2 vào test = đề thi đo FNR).
- Đã kiểm: **0 rò rỉ origin giữa train/val và test**.

## Cột
`sha256, family, group, variant, packer, origin_sha256` + 19 feature tĩnh + `is_drift_truth, split`.
Xem `src/schema_cols.py` là nguồn sự thật về cột. `manifest.csv` = ID + nguồn gốc (provenance).

## ⚠️ ĐÂY LÀ PILOT — còn thiếu (làm phiên sau)
1. **G1/G3 cho .NET**: UPX KHÔNG pack được .NET (68% G0 là .NET) → cần packer .NET
   (ConfuserEx cho P-seen; .NET Reactor/Eazfuscator cho P-unseen). Hiện G1 chỉ phủ 17 native.
2. **G3** (G2 bị pack) chưa có — và phải pack từ G2 **sống**, KHÔNG dùng mẫu MOTIF (đã disarmed).
3. **Scale G0** lên ~100-130 (đang 53) khi lấy được Auth-Key MalwareBazaar.
4. **Provenance** cho 45 mẫu G0 tải tay chưa đầy đủ (chờ key để backfill).

## Dùng được ngay cho
- Code & chạy thử `detector`, `packed_score`, `dual_check`, `filter`, `eval_metrics` trên **dữ liệu thật** (thay mock).
- Kiểm pipeline E1–E6 ở quy mô nhỏ. Kết quả còn hẹp (N nhỏ, CI rộng) — chờ bản đầy đủ mới chốt số.

## Lưu ý an toàn
File này CHỈ chứa **đặc trưng số + hash** — KHÔNG có mẫu malware. An toàn để commit/chia sẻ.
Mẫu thật (exe) không bao giờ lên git.
