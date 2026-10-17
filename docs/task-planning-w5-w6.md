# Phân công & Quy trình làm việc — Tuần 5 & 6

> **Dự án:** UNMASK — Vỏ đổi hay lõi đổi?  
> **Môn học:** IAM302t · Nhóm 1  
> **Thời gian:** 05/10 – 18/10/2026  
> **Hạn chót:** **18/10/2026** (pip + demo chạy được)

---

## 1. Dự án làm gì & Sản phẩm cuối

**Mục tiêu:**  
UNMASK đo khi chuông báo drift kêu thì vì đổi vỏ (đổi packer) hay đổi lõi (malware mới thật). Nhóm dựng cổng lọc **F3 (UNMASK)** rồi so với **F0** (không lọc), **F1** (Detect It Easy), **F2** (luật entropy cũ). Cả 4 cổng dùng chung một chuông **D1**. Học bằng UPX, thi bằng mọi thứ còn lại.

**Sản phẩm cuối (đến 18/10):**
1. `dataset.csv` + `manifest.csv` — chỉ feature & hash, không kèm file mẫu.
2. Module pip `unmask` — gọi `filter(file)` → `{packed_score, decision, evidence}`.
3. Kết quả E0–E6 — bảng chính F0–F3 + biểu đồ (3 seed × 3 tỉ lệ pack).
4. Demo Streamlit — chạy localhost, hiện `packed_score` + `evidence`.
5. Báo cáo & slide làm sau, khi phần demo đã chạy ổn.

---

## 2. Sơ đồ quy trình (giai đoạn × người, theo mốc ngày)

*Mỗi dòng là một bước; làm theo thứ tự trên xuống, các bước cùng mốc chạy song song.*

| Giai đoạn | Bước | Người | Mốc |
| :--- | :--- | :--- | :--- |
| **GĐ0** | Chốt schema `dataset.csv`/`manifest` + tạo `mock_dataset.csv` (file giả) → cả nhóm code song song ngay | Khánh + Tuấn | 05/10 |
| **GĐ1** | Dựng VM; pilot pack .NET; viết script trích feature (test trên PE lành) | Khánh · Tuấn | 06–08/10 |
| **GĐ1** | Thu G0/G2 từ MalwareBazaar; lọc mẫu pack sẵn (DiE); pack G1, G3; tạo P-low/P-wild | Khánh | 09–11/10 |
| **GĐ1** | Chạy script feature trong VM → `dataset.csv` + `manifest` THẬT | Khánh | 11/10 |
| **GĐ1** | Chia tập theo mẫu gốc (chống rò rỉ); viết `eval_metrics.py` + script E0 | Đức · Trúc | 09–11/10 |
| **GĐ2** | F3: packed score + dual-check + quét ngưỡng → khóa; cổng F1, F2 | Tuấn · Trúc | 12–13/10 |
| **GĐ2** | Detector D1 (P95) khóa trên validation; E0b độ nhạy chuông | Đức | 13/10 |
| **GĐ3** | Chạy E1–E6 (3 seed × 3 tỉ lệ) → `results_*.csv` + bảng chính | Đức | 14–16/10 |
| **GĐ3** | Biểu đồ FTR/đường FTR–FNR/per-packer | Trúc | 16/10 |
| **GĐ4** | Đóng gói pip `unmask`; demo Streamlit | Tuấn · Trúc | 16–17/10 |

---

## 3. Việc của từng người

### 👨‍💻 Khánh
**Nhận từ / giao cho:**  
- **Nhận:** script feature từ Tuấn (GĐ1).  
- **Giao:** `dataset.csv` + `manifest` cho Đức & Trúc.

| # | Việc | Output yêu cầu (tên file · định dạng · tiêu chí) | Hạn |
| :-: | :--- | :--- | :-: |
| 1 | Chốt schema `dataset.csv` + `manifest`; tạo file giả để cả nhóm code ngay | `mock_dataset.csv` · CSV · đúng tên & kiểu cột manifest, ≥20 dòng phủ G0–G3 + biến thể | 05/10 |
| 2 | Dựng VM (Linux cho UPX/pefile/LIEF, Windows cho MPRESS/ASPack), tắt AV trong VM | VM cô lập, không thư mục chia sẻ ghi được | 06/10 |
| 3 | Pilot pack 10–20 mẫu .NET bằng 3 packer để biết sớm tỉ lệ lỗi | `pilot_pack.csv` · tỉ lệ pack lỗi theo packer | 08/10 |
| 4 | Thu G0 (AgentTesla) + G2 (njRAT/Formbook/AgentTesla khác thời kỳ) từ MalwareBazaar | `data/raw/` · ≥150 G0, ≥150 G2 · zip có mật khẩu | 09/10 |
| 5 | Lọc mẫu đã pack sẵn bằng DiE, ghi số bị loại theo họ vào manifest | manifest cột `die_result` + số mẫu loại/họ | 09/10 |
| 6 | Pack G1 = G0×3 packer, G3 = G2×3 packer; tạo P-low; thu P-wild | `data/packed/`, `lowentropy/`, `wild/` · ghi tỉ lệ pack lỗi/packer | 11/10 |
| 7 | Chạy script feature của Tuấn trong VM → bộ dữ liệu thật | `dataset.csv` + `manifest` THẬT (thay file giả) | 11/10 |

---

### 👨‍💻 Tuấn
**Nhận từ / giao cho:**  
- **Giao:** script feature cho Khánh (GĐ1); F3 + F3a cho Đức chạy thí nghiệm.

| # | Việc | Output yêu cầu (tên file · định dạng · tiêu chí) | Hạn |
| :-: | :--- | :--- | :-: |
| 1 | Chốt cột `dataset.csv`/`manifest` cùng Khánh (entropy, section, import, header, overlay, .NET, hash…) | `schema.md` · danh sách cột + kiểu | 05/10 |
| 2 | Viết script trích feature (pefile/LIEF); test trên PE lành tính | `extract_features.py` · chạy ra CSV đúng schema | 08/10 |
| 3 | Packed score đa đặc trưng (logistic regression học trên G0 + G1-UPX) | trong `unmask/` · không thấy P-unseen/low/wild khi học | 12/10 |
| 4 | Dual-check: bỏ feature packing, so phần còn lại với tập tham chiếu | hàm `dual_check()` · phân biệt đổi vỏ / lõi lạ | 13/10 |
| 5 | Quét ngưỡng → khóa; output 3 giá trị PASS/FILTERED/FLAGGED + evidence | `unmask_filter.py` · config ngưỡng đã khóa (commit) | 13/10 |
| 6 | Bản ablation F3a = F3 bỏ dual-check (để đo riêng công dual-check) | cờ `--no-dualcheck` hoặc F3a riêng | 14/10 |
| 7 | Đóng gói module pip `unmask` & viết hướng dẫn | `pip install unmask` chạy được; `README` | 16/10 |

---

### 👨‍💻 Đức
**Nhận từ / giao cho:**  
- **Nhận:** `dataset.csv` từ Khánh; `eval_metrics.py` từ Trúc; F1/F2/F3 từ Tuấn & Trúc.  
- **Giao:** `results_*.csv` + bảng chính cho cả nhóm.

| # | Việc | Output yêu cầu (tên file · định dạng · tiêu chí) | Hạn |
| :-: | :--- | :--- | :-: |
| 1 | Chia tập theo mẫu gốc — mọi biến thể của 1 mẫu nằm cùng tập; đề ôn = G0 + UPX | cột `split` trong `dataset.csv` · kiểm 0 rò rỉ | 11/10 |
| 2 | Detector D1 (Mahalanobis / Isolation Forest), ngưỡng P95 học trên validation rồi khóa | `src/detector.py` · ngưỡng đã khóa | 13/10 |
| 3 | E0b — độ nhạy chuông: với F0, chuông phải báo drift trên phần lớn G2 | kết quả E0b · nếu fail thì FNR vô nghĩa | 13/10 |
| 4 | E1 FTR cơ sở (luồng không lọc, 3 tỉ lệ pack) | `results_A.csv` · FTR-A theo tỉ lệ | 14/10 |
| 5 | E2 so 4 cổng + E3 tổng quát (P-unseen/low/wild) | `results_B.csv` · tỉ lệ lọc đúng/biến thể | 15/10 |
| 6 | E4 (G2, G3) + E5 đường FTR–FNR + E6 per-packer; chạy 3 seed × 3 tỉ lệ | `results_*.csv` · FNR tách G2/G3 | 16/10 |
| 7 | Ghép bảng kết quả chính F0–F3 | `bang_chinh.csv`/`.md` · điền số thật | 16/10 |

---

### 👩‍💻 Trúc
**Nhận từ / giao cho:**  
- **Nhận:** `dataset.csv` từ Khánh.  
- **Giao:** `eval_metrics.py` + F1/F2 cho Đức; demo nhận output của cả nhóm.

| # | Việc | Output yêu cầu (tên file · định dạng · tiêu chí) | Hạn |
| :-: | :--- | :--- | :-: |
| 1 | `eval_metrics.py`: FTR, FNR, tỉ lệ lọc đúng, %FLAGGED, Wilson CI, McNemar | `src/eval_metrics.py` · có unit test trên file giả | 09/10 |
| 2 | Script E0 kiểm tra dữ liệu: đúng schema, không rò rỉ split, P-low entropy thấp thật | `check_data.py` · báo PASS/FAIL từng mục | 10/10 |
| 3 | Cổng F1 — Detect It Easy: đọc cột `die_result`, 'packed' → loại | `f1_die.py` · quyết định theo manifest | 12/10 |
| 4 | Cổng F2 — luật cũ: `entropy_max > 7.0` VÀ section lạ | `f2_rule.py` · chạy trên `dataset.csv` | 12/10 |
| 5 | Biểu đồ: cột FTR/cổng, đường FTR–FNR, per-packer | `figs/*.png` · nhãn rõ, kèm tỉ lệ pack | 16/10 |
| 6 | Demo Streamlit: đọc `dataset.csv` + output JSON, hiện `packed_score` + `evidence` (localhost) | `app.py` · `streamlit run` chạy được | 17/10 |

---

## 4. Quy định output chung

### Cấu trúc Repository
```text
UNMASK/
├── data/
│   ├── raw/
│   ├── packed/
│   ├── lowentropy/
│   └── wild/
├── dataset.csv
├── manifest.csv
├── src/
│   ├── detector.py
│   ├── eval_metrics.py
│   ├── f1_die.py
│   ├── f2_rule.py
│   └── check_data.py
├── unmask/ (module pip)
├── results/
├── figs/
├── app.py
└── config/
```

### Quy tắc Đặt tên & Báo cáo
- **Tên file:** Chữ thường, gạch dưới, không dấu — ví dụ: `results_e2.csv`, `fig_ftr_per_gate.png`.
- **File kết quả thí nghiệm:** `results_<e>_<seed>_<tilepack>.csv`.
- **Số liệu:** Mọi số FTR phải kèm tỉ lệ pack; FNR báo riêng cho G2 và G3.

### Tiêu chí Đạt ("Xong" một việc)
1. Merge vào `main` thành công qua Pull Request.
2. Chạy được trên **mock** rồi trên **dữ liệu thật** không phát sinh lỗi.
3. Có file output đúng **tên & định dạng** quy định.
4. Người nhận kế tiếp có thể sử dụng trực tiếp.

### Khóa Đề thi
Config ngưỡng/trọng số/seed + SHA-256 tập test phải được commit lên git **TRƯỚC** khi chạy E3–E5. **Không chỉnh ngưỡng sau khi nhìn đề thi.**

---

## 5. Hạn chót · Lịch họp · Quy trình Git

- **Hạn chót:** **18/10 (Chủ nhật)** — Module pip + demo Streamlit chạy hoàn hảo không lỗi. Sau 18/10 chỉ sửa lỗi phát sinh, sau đó mới tiến hành viết báo cáo & slide.
- **Họp nhanh hàng ngày:** Mỗi tối **21:00 (15 phút)** trên Discord (nội dung: *hôm qua xong gì / nay làm gì / kẹt gì*).
- **2 buổi họp cổng (Milestone Gate):**
  - **Thứ 5 (08/10):** Chốt VM + schema + script feature.
  - **Chủ nhật (18/10):** Nghiệm thu demo.
- **Quy trình Git:**
  - Repository GitHub, nhánh `main` luôn giữ sạch.
  - Mỗi thành viên làm việc trên nhánh riêng `feat/<tên>-<việc>`, merge vào `main` qua Pull Request, cần **≥1 người review**.
  - **KHÔNG commit file mẫu / file đã pack** lên git (chỉ commit feature, hash, script).
