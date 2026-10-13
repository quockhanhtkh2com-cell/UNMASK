# UNMASK — Vỏ đổi hay lõi đổi?
Định lượng drift do packing và giới hạn của bộ lọc dựa trên đặc trưng tĩnh · IAM302t · Nhóm 1

> ⚠️ **Công cụ chỉ ĐỌC feature tĩnh của file PE, KHÔNG chạy file.** Đọc `docs/SAFETY.md` trước.

## Ý tưởng 1 dòng
Khi chuông báo drift kêu — là do **đổi vỏ** (đổi packer) hay **đổi lõi** (malware mới thật)?
Dựng cổng lọc **F3 (UNMASK)** đặt trước detector, so với **F0** (không lọc), **F1** (Detect It Easy),
**F2** (luật entropy cũ). 4 cổng dùng **chung một chuông D1**. Học bằng UPX, thi bằng mọi thứ còn lại.

## Cây thư mục
```
UNMASK/
├─ schema.md                 # HỢP ĐỒNG cột dataset.csv/manifest — đọc đầu tiên
├─ config/                   # config.example.yaml + thresholds.locked.json (khoá đề thi)
├─ data/{raw,packed,lowentropy,wild}/   # mẫu — KHÔNG lên git
├─ mock/                     # mock_dataset.csv để code song song ngay
├─ src/
│  ├─ extract_features.py    # [Tuấn] trích feature tĩnh (pefile/LIEF)
│  ├─ split_data.py          # [Trúc] chia tập theo mẫu gốc, chống rò rỉ
│  ├─ detector.py            # [Đức] D1: Mahalanobis / IsolationForest, P95
│  ├─ eval_metrics.py        # [Trúc] FTR, FNR, Wilson CI, McNemar
│  ├─ f1_die.py              # [Trúc] cổng F1 — Detect It Easy
│  ├─ f2_rule.py             # [Trúc] cổng F2 — entropy>7 AND section lạ
│  └─ check_data.py          # [Trúc] E0 kiểm tra dữ liệu
├─ unmask/                   # [Tuấn] module pip — cổng F3
│  ├─ packed_score.py        #   bước 1: điểm bị pack (logistic)
│  ├─ dual_check.py          #   bước 2: chống lỗi L1
│  ├─ filter.py              #   filter(file) -> {packed_score, decision, evidence}
│  └─ train.py               #   học trọng số + quét ngưỡng -> khoá
├─ experiments/
│  ├─ run_experiments.py     # [Đức] E0b, E1–E6 (3 seed × 3 tỉ lệ)
│  └─ build_main_table.py    # [Đức] bang_chinh.csv/.md
├─ app.py                    # [Trúc] demo Streamlit (localhost)
├─ results/  figs/           # output
└─ tests/                    # unit test (eval_metrics...)
```

## Cài & chạy thử trên mock (clone về làm ngay)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) sinh mock để code song song
python mock/make_mock_dataset.py

# 2) kiểm tra dữ liệu
python src/check_data.py --dataset mock/mock_dataset.csv

# 3) chạy thử cổng F3 trên mock
python -m unmask.filter --dataset mock/mock_dataset.csv --out results/demo_f3.csv

# 4) chạy thử 1 thí nghiệm
python experiments/run_experiments.py --exp e2 --dataset mock/mock_dataset.csv --seed 0 --pack-ratio 0.5

# 5) demo
streamlit run app.py

# test
pytest -q
```

## 4 cổng lọc & 3 quyết định của F3
- **F0** không lọc · **F1** DiE (packed→loại) · **F2** entropy_max>7.0 AND section lạ · **F3** UNMASK.
- F3 trả: **PASS** (không pack→vào chuông) · **FILTERED** (chỉ đổi vỏ→loại, ghi log) · **FLAGGED** (pack nhưng ruột lạ→vào chuông + cờ).

## Câu hỏi nghiên cứu → đo bằng
- **RQ1** bao nhiêu % báo drift là do đổi packer → **FTR** theo tỉ lệ pack
- **RQ2** bộ lọc có tổng quát sang packer chưa gặp / low-entropy / wild → tỉ lệ lọc đúng theo biến thể
- **RQ3** drift thật trùng đổi packer (L1), bỏ sót bao nhiêu, dual-check giảm bao nhiêu → **FNR** G2/G3
- **RQ4** UNMASK có hơn Detect It Easy không → so FTR, FNR F3 vs F1

## Luật vàng
1. Đề thi giấu kín đến lúc đánh giá. 2. Mọi cổng dùng CHUNG một chuông. 3. Đo ra sao báo vậy (kể cả khi UNMASK thua DiE).

## Trạng thái skeleton
Các file `src/`, `unmask/`, `experiments/`, `app.py` là **khung có hợp đồng hàm + chạy được trên mock**.
Chỗ cần điền ghi rõ `# TODO(<người>)`. `eval_metrics.py` và `check_data.py` đã implement đầy đủ.

## Cài đặt như module pip

```bash
pip install .              # trong thư mục repo, đã bật venv
pip install -e ".[dev]"    # nếu muốn sửa code và chạy test
```

Dùng trong Python (chỉ đọc tĩnh, KHÔNG chạy file):

```python
from unmask import filter_file, filter_row
filter_file("mau.exe")                       # F3 đầy đủ: PASS / FILTERED / FLAGGED
filter_file("mau.exe", use_dualcheck=False)  # F3a (ablation, không dual-check)
```

CLI trên dataset (mock hoặc thật):

```bash
unmask-filter --dataset mock/mock_dataset.csv                  # F3
unmask-filter --dataset mock/mock_dataset.csv --no-dualcheck   # F3a
```

Config khoá: trong repo, `unmask` đọc `config/thresholds.locked.json`. Khi cài bằng pip thì
đặt đường dẫn bằng biến môi trường `UNMASK_CONFIG` (file do `unmask/train.py` sinh ra).
Chưa có config khoá thì `filter_file` dùng trọng số mặc định CHƯA hiệu chỉnh nên kết quả không
có ý nghĩa, và F3 đầy đủ sẽ báo `ValueError` thay vì âm thầm chạy như F3a.

Ghi chú đóng gói: `schema_cols` và `extract_features` (nằm trong `src/`) được cài thành module
cùng cấp với `unmask` để import không lỗi; không di chuyển file nào. Nếu nhóm muốn gom vào
`unmask/` thì đổi sau.

An toàn: mẫu malware chỉ nằm trong VM cô lập; không commit mẫu hay file packed (xem SAFETY.md).

## Tiến độ phần F3 / đóng gói (Tuấn) — cập nhật 13/10/2026

**Đã xong (trên nhánh `feat/tuan-gd2-f3`, chờ PR vào `dev`):**
- `extract_features.py`, `packed_score.py`, `dual_check.py`, `filter.py` (F3/F3a), `train.py`: đã có trong `dev`, `pytest` 89 passed.
- Sửa baseline `import_table_shrink` theo `is_dotnet` (khớp bản vá của Khánh); thêm `load_filter()`.
- Runner `experiments/run_experiments.py` nạp config F3 đã khoá (`--f3-config`) thay vì scorer chưa train.
- Gói pip: cài từ repo trong venv sạch, import và chạy `filter_file` trên file PE được.
- `docs/vm_sop.md` (bản nháp) và `scripts/lock_f3.sh` (quy trình khoá ngưỡng).
- Chạy thử F3/F3a trên dataset pilot v0.1: chỉ là **bản nháp**, chưa tinh chỉnh, không dùng trong báo cáo.

**Còn lại, phụ thuộc người khác:**
- Khoá ngưỡng F3 trên dataset v1.0: `scripts/lock_f3.sh <dataset_v1.0.csv>`, rồi commit `config/thresholds.locked.json` trước khi chạy E3–E5. Cần Khánh freeze v1.0 (và báo Đức vì file khoá dùng chung).
- Điền các mục **[CHƯA KIỂM]** trong `docs/vm_sop.md` (ConfuserEx, MPRESS, ASPack, chuyển file giữa hai VM).
- Kiểm `pip install` từ `dev` trong venv sạch sau khi mọi PR đã gộp (T6).
