# Hướng dẫn chạy pilot trích xuất feature (cho Khánh)

Người viết: Tuấn · 07/10/2026 · Áp dụng cho nhánh `feat/tuan-extract-features` (PR #1).

Mục tiêu: (1) xem mẫu AgentTesla thật có phải .NET và hai feature import có vô nghĩa không (câu 1 trong file câu hỏi); (2) xem feature lõi nào giữ nguyên giữa bản gốc và bản pack UPX (câu 5, để chốt `CORE_FEATURE_COLS`).

**Chưa chạy trên mẫu thật.** Lệnh trích xuất và `--finalize` đã chạy trên 8 PE lành tính (Phần B); `core_survival.py` đã chạy trên dữ liệu mock và có test. Bước gộp bằng `head`/`tail` ở mục 4 chưa được chạy thử. Nếu gặp lỗi, gửi Tuấn nguyên văn dòng lỗi.

## 1. An toàn

- Chỉ chạy trong VM cô lập của Khánh. Script chỉ ĐỌC file bằng `pefile`, không bao giờ chạy mẫu.
- Mẫu ở lại trong VM. Không gửi mẫu hay file đã pack qua chat hay lên git (xem `SAFETY.md`).
- Chỉ gửi lại các file CSV/văn bản feature (mục 5): chỉ chứa feature và hash.

## 2. Chuẩn bị

| Cần có | Ví dụ | Ghi chú |
|---|---|---|
| Mẫu G0 | `~/pilot/g0/` | AgentTesla gốc, chưa pack |
| Mẫu G1 | `~/pilot/g1_upx/` | Bản pack UPX của đúng các mẫu trên |
| Bảng ánh xạ | `~/pilot/map_g1.csv` | Hai cột `filename,origin_sha256` |

Ví dụ nội dung `map_g1.csv` (dòng đầu là tiêu đề; `filename` là tên file trong thư mục g1_upx, `origin_sha256` là sha256 của file GỐC đã sinh ra nó; chỉ người pack mới biết ánh xạ này):

~~~
filename,origin_sha256
mau01_upx.exe,<sha256 cua mau01 goc>
mau02_upx.exe,<sha256 cua mau02 goc>
~~~

Lấy code mới và kiểm tra:

~~~
cd ~/IAM/UNMASK && source .venv/bin/activate
git fetch origin && git switch feat/tuan-extract-features
python -m pytest -q
~~~

Kết quả mong đợi: `30 passed`. (Sau khi PR #1 được gộp thì dùng `main` thay cho nhánh này.)

## 3. Trích xuất feature

~~~
python src/extract_features.py --in ~/pilot/g0 --group G0 --family agenttesla --out ~/pilot/pilot_g0.csv
python src/extract_features.py --in ~/pilot/g1_upx --group G1 --family agenttesla --variant P-seen \
    --packer upx --origin-map ~/pilot/map_g1.csv --out ~/pilot/pilot_g1.csv
cat ~/pilot/extract_errors.csv
~~~

Dòng cuối chỉ có nội dung nếu có mẫu bị bỏ qua (ví dụ mẫu G1 thiếu trong bảng ánh xạ); file này được ghi nối, xoá đi nếu muốn chạy lại cho sạch.

## 4. Gộp, chuẩn hoá và kiểm lõi

~~~
head -1 ~/pilot/pilot_g0.csv > ~/pilot/pilot_raw.csv
tail -n +2 ~/pilot/pilot_g0.csv >> ~/pilot/pilot_raw.csv
tail -n +2 ~/pilot/pilot_g1.csv >> ~/pilot/pilot_raw.csv
python src/extract_features.py --finalize ~/pilot/pilot_raw.csv --out ~/pilot/pilot_dataset.csv
python src/core_survival.py ~/pilot/pilot_dataset.csv | tee ~/pilot/core_survival_out.txt
~~~

Đầu ra của `core_survival.py` gồm hai phần:

- **Kiểm giả thuyết .NET (câu 1):** nếu gần như mọi dòng có `is_dotnet=1` và `num_api` trung vị khoảng 1 ở cả G0 lẫn G1 thì giả thuyết đúng: `import_table_shrink` khoảng 0 và `only_dynamic_loader_imports` bằng 0 với mọi mẫu .NET. Nếu `num_api` khác nhiều giữa G0 và G1 thì giả thuyết sai và hai feature vẫn dùng được.
- **Feature nào sống sót khi pack (câu 5):** với mỗi packer và mỗi feature lõi: số cặp, tỉ lệ cặp "giống hệt", độ lệch tương đối trung vị. Tiêu chí đề xuất (nhóm quyết, không phải kết luận): giống hệt từ 90% trở lên hoặc độ lệch trung vị từ 0,05 trở xuống thì giữ; giống hệt thấp và lệch lớn (ví dụ `file_size` khi UPX nén) thì loại; ít hơn 20 cặp thì không kết luận chắc.

## 5. Gửi lại cho Tuấn

| File | Có gửi? |
|---|---|
| `~/pilot/pilot_dataset.csv` | Có (chỉ feature và hash) |
| `~/pilot/core_survival_out.txt` | Có |
| `~/pilot/extract_errors.csv` | Có, nếu file tồn tại |
| Mẫu `.exe`, thư mục `g0/` và `g1_upx/` | **KHÔNG** |

## 6. Lỗi thường gặp

| Hiện tượng | Nguyên nhân và cách xử lý |
|---|---|
| Dòng `[skip]` báo thiếu `origin_sha256`, kết thúc bằng “0 file hợp lệ”, mã thoát 1, không ghi file | G1 thiếu `--origin-map`, hoặc tên trong cột `filename` không khớp tên file thật (so khớp đúng tên file, không kèm thư mục). |
| `Khong co cap G0-G1 nao khop origin_sha256` | `origin_sha256` trong bảng ánh xạ không trùng sha256 của file gốc trong G0. Kiểm lại ánh xạ. |
| `ModuleNotFoundError` khi chạy script | Chưa bật venv hoặc đang đứng sai thư mục; chạy từ thư mục gốc repo `~/IAM/UNMASK` sau `source .venv/bin/activate`. |
| Số cặp ít (dưới 20) | Chưa đủ để kết luận feature lõi; ghi rõ cỡ mẫu nhỏ. |
