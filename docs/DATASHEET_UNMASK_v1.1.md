# DATASHEET — UNMASK dataset v1.1

*Chuẩn "Datasheets for Datasets" (Gebru et al., 2018) · Dự án IAM302t — UNMASK "Vỏ đổi hay lõi đổi?" · Nhóm 1*

| | |
|---|---|
| **Version** | v1.1 (frozen 2026-10-17) |
| **Số dòng** | 596 (feature tĩnh + hash, KHÔNG kèm mẫu malware) |
| **SHA-256 `dataset_v1.1.csv`** | `caed7ef9feff39621a4146e84f3b803bd87de94ae283addc6e0e580e02bdeb82` |
| **SHA-256 `manifest_v1.1.csv`** | `cad95fbff82a3e8940ba6a064b691e439b9d4e07e5c9fd9087d9e6f5993cf214` |
| **Rule** | Không sửa sau mốc freeze; thay đổi → v1.2, không ghi đè. |

**Changelog vs v1.0:** G0 scale 53→**122** (+69 mẫu AgentTesla mới, DiE xác nhận clean); G1 67→**156** (UPX 39 P-seen + MPRESS 117 P-unseen); manifest bổ sung đủ `MANIFEST_COLS` (die_result, removed_prepacked, pack_failed, source, timestamp_collected, note); train/val dày hơn (64/23 → 140/52).

---

## 1. Motivation (Vì sao dựng)
Đo lường khi một bộ phát hiện drift "kêu chuông", đó là do **đổi vỏ** (đổi packer — cùng malware) hay **đổi lõi** (malware họ mới thật). Dataset thiết kế theo ma trận 2×2 có kiểm soát để **tách bạch packing-induced drift khỏi real concept drift** — khoảng trống Guldemir & Olukoya (2025) chỉ ra nhưng chưa định lượng. Tự xây vì cần **cặp ghép** (cùng lõi, chỉ khác vỏ) để cô lập biến "packing" — điều BenchMFC/BODMAS không cung cấp ở dạng controlled.

## 2. Composition (Thành phần)

| Nhóm | Mô tả | Số mẫu | is_drift_truth |
|---|---|---|---|
| **G0** | AgentTesla — lõi sạch (DiE-clean) | 122 | 0 |
| **G1** | G0 bị pack ("đổi vỏ") — UPX 39 (P-seen, native) + MPRESS 117 (P-unseen) | 156 | 0 |
| **G2** | 8 họ khác ("đổi lõi") — mẫu sống từ MalwareBazaar | 165 | 1 |
| **G3** | G2 bị pack ("đổi cả hai") — MPRESS, ghép cặp với G2 | 153 | 1 |
| | **Tổng** | **596** | |

**Variant:** none 287 · P-seen (UPX) 39 · P-unseen (MPRESS) 270.
**Họ G2-live:** azorult 25 · emotet 25 · formbook 25 · lokibot 25 · nanocore 25 · njrat 25 · remcos 14 · flokibot 1.
**Họ G3:** 7/8 họ (flokibot = 0, xem §7).

**Mỗi dòng** = 1 file PE: 6 cột định danh (`sha256, family, group, variant, packer, origin_sha256`) + **19 feature tĩnh** + `is_drift_truth` + `split`. Nguồn sự thật về cột: `src/schema_cols.py`.

**Split** (chống leakage theo `origin_sha256`): train 140 · val 52 · test 404. Origin "đổi lõi" (G2/G3) → toàn bộ test; origin lõi-gốc (G0/G1) → train/val/test. **0 rò rỉ.**

## 3. Collection Process (Thu thập)
- **G0 / G2-live:** tải từ **MalwareBazaar (abuse.ch)** API `get_file`, truy vấn theo `signature` (flokibot theo `tag`). **Lọc chỉ PE** (loại .js/vbs/doc dropper). Mỗi mẫu **verify SHA-256** sau giải nén. Dedup theo `sha256`.
- **Taxonomy mapping** MOTIF↔MB: lokibot→`Loki`, remcos→`RemcosRAT`, flokibot→tag `FlokiBot` (tránh lẫn GuLoader).
- **Thời điểm:** 2026-10.

## 4. Preprocessing / Labeling
- **Gate lõi sạch:** scanner tự viết (`temp_run_die.py`, pefile) — **122/122 G0 = clean** (0 pre-packed). Lưu ý: cả section-name heuristic lẫn entropy báo nhầm một số native G0, chỉ **import-table (dual-check)** phân biệt đúng → bằng chứng thực nghiệm cho giá trị dual-check.
- **Trích feature:** `src/extract_features.py` (pefile) — **chỉ parse tĩnh, KHÔNG thực thi mẫu**. Cùng 1 tool cho mọi nhóm.
- **Packing:** UPX `--best` (P-seen, native — .NET không pack được); MPRESS v2.19 (P-unseen, cả native lẫn .NET). `origin_sha256` trỏ lõi gốc để chống leakage.
- **Nhãn:** `group/variant/packer` gán lúc sinh; `is_drift_truth` theo `GROUP_IS_DRIFT`; `family` ground-truth từ nguồn.
- **Độ tin cậy nhãn (label confidence):** nhãn `family` lấy từ trường `signature` của MalwareBazaar — **nguồn đơn, không phải đồng thuận đa engine** → coi là nhãn **"silver"** ở mức *họ malware*. Ngược lại, `group` và `is_drift_truth` do nhóm **TỰ kiểm soát khi sinh** (G0/G1 từ cùng một lõi sạch; G2/G3 từ họ khác) nên là nhãn **"gold"**. **Kết luận chính của nghiên cứu dựa trên `is_drift_truth` (gold)** — tách đổi-vỏ / đổi-lõi — **không phụ thuộc vào độ chính xác của tên họ**; tên họ chỉ dùng cho phân tích phụ (per-family).

## 5. Uses
Huấn luyện & đánh giá cổng lọc F3 (UNMASK) so với F0/F1(DiE)/F2(entropy); đo FTR, FNR (tách G2/G3), tổng quát sang packer chưa gặp (train P-seen → test P-unseen). **Không** dùng để tạo malware hay né phát hiện.

## 6. Distribution
Chỉ chia **feature số + hash** (`dataset_v1.1.csv`, `manifest_v1.1.csv`) — **tuyệt đối không kèm mẫu / file packed**. An toàn commit/chia sẻ. Mẫu thật chỉ trong VM cô lập.

## 7. Limitations / Threats to Validity
- **flokibot không có nhánh G3** (1 mẫu live, pack lỗi) → kết luận "đổi cả hai" không áp cho flokibot.
- **P-seen chỉ 1 packer (UPX), native-only** (39 mẫu): đã dày hơn v1.0 (17) nhờ scale, nhưng vẫn 1 packer seen → **construct validity cho "tổng quát packer" còn giới hạn** (ASPack/packer P-seen #2 = future work).
- **G0 chỉ 1 họ (AgentTesla)** → đóng khung **case study**; external validity giới hạn 1 họ (đa họ lõi = future work).
- **MPRESS là NÉN, chưa phải OBFUSCATION** — ConfuserEx/.NET Reactor cho "đổi vỏ" .NET thực chiến = future work (cần VM Windows mới).
- **Chưa có P-low / P-wild** → ô tương ứng trong thí nghiệm để trống (lưu ý: MPRESS-.NET giữ entropy thấp đã phần nào minh hoạ điểm mù F2).
- **Nhãn họ là "silver" (nguồn đơn MB)** → phân tích per-family mang tính tham khảo; kết luận chính dựa trên `is_drift_truth` (gold).
- **N vừa (596)** — controlled design, không thi đua quy mô kiểu BenchMFC; đóng góp là *phương pháp đo*.

**Tập phụ trợ (ngoài 596):** MOTIF disarmed G2 (119 mẫu, 8 họ) giữ **riêng** làm **bộ kiểm nguồn khác (cross-source robustness)**.

## 8. Maintenance
- **Chủ trì:** Khánh (Võ Quốc Khánh, nhóm trưởng). Thay đổi → tăng version, không ghi đè.
- **Tool provenance:** UPX (/usr/bin/upx, Kali); MPRESS v2.19 verify SHA-256 từ Wayback (`19ffee9…736c5`); extract bằng pefile; đóng gói 7z.

---

*Datasheet này đi kèm `dataset_v1.1.csv` như một phần của reproducibility bundle. Mọi số liệu lấy từ quá trình xây dựng thật, không ước lượng.*
