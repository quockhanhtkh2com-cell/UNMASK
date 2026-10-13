# SOP máy ảo (VM) — pack mẫu, trích feature, xuất kết quả

Người viết: Tuấn · 13/10/2026 · BẢN NHÁP — các mục đánh dấu **[CHƯA KIỂM]** chưa được chạy thử thật, cần Khánh/Đức xác nhận trước khi coi là chuẩn.

Đọc `docs/SAFETY.md` trước. File này chỉ nói CÁCH LÀM; luật an toàn nằm ở SAFETY.md.

## 0. Nguyên tắc (tóm tắt)

- Mẫu là malware thật. Chỉ thao tác trong VM cô lập. Script chỉ ĐỌC file (pefile), không chạy mẫu.
- Không có thư mục chia sẻ ghi được với máy thật. Chỉ CSV/biểu đồ/báo cáo được đưa ra.
- Mẫu và file đã pack không lên git, không gửi qua chat. `.gitignore` chặn `data/**`.

## 1. Hai VM, hai việc

| VM | Dùng cho | Công cụ |
|---|---|---|
| Linux | UPX, trích feature, chạy thí nghiệm | `upx`, Python venv (`.venv`), `pefile`, `lief`, `pandas` |
| Windows | Packer chỉ chạy trên Windows | MPRESS, ASPack, ConfuserEx (.NET) **[CHƯA KIỂM]** |

Quy tắc antivirus: chỉ tắt TRONG VM Windows; không tắt trên máy thật.
Trước khi làm: chụp snapshot "sạch" của VM; làm xong thì khôi phục snapshot nếu đã chạm mẫu lạ.

## 2. Chuẩn bị Linux VM

~~~
cd ~/IAM/UNMASK && git fetch origin && git switch dev && git pull
source .venv/bin/activate
python -m pytest -q          # phải xanh trước khi làm tiếp
which upx                    # phải có
~~~

Thư mục dữ liệu (ví dụ, nằm NGOÀI repo):

~~~
~/IAM302t/Datasets/g0_unpacked/   # G0 gốc, đã giải nén
~/IAM302t/Datasets/g1_packed/     # G1 sinh ra (đặt tên <origin_sha256>_<packer>.exe)
~~~

## 3. Pack G0 -> G1 bằng UPX (đã dùng ở pilot)

~~~
python3 src/pack_extract_g1.py \
    --in  ~/IAM302t/Datasets/g0_unpacked \
    --packed-out ~/IAM302t/Datasets/g1_packed \
    --out part_g1.csv --packer upx --variant P-seen
~~~

- Script gọi `upx --best --force`, rồi trích feature và ghi `origin_sha256` (sha256 của file G0 gốc) để chia train/test không rò rỉ.
- Giới hạn đã biết: UPX KHÔNG pack được file .NET (khoảng 68% G0). Với .NET dùng mục 4.

## 4. Pack bằng packer khác (Windows VM) **[CHƯA KIỂM]**

| Mục tiêu | Packer | Biến thể |
|---|---|---|
| G1 cho .NET | ConfuserEx | P-seen |
| G1 native, packer chưa thấy khi train | MPRESS, ASPack | P-unseen |
| .NET, packer chưa thấy | .NET Reactor / Eazfuscator | P-unseen |

Quy trình chung (chi tiết lệnh/GUI của từng packer: **[ĐIỀN — Khánh/Đức]**):
1. Chép MỘT file G0 vào VM Windows (qua kênh một chiều, không thư mục chia sẻ ghi được).
2. Pack bằng packer, đặt tên `<origin_sha256>_<packer>.exe`.
3. Lập bảng ánh xạ `map.csv` hai cột `filename,origin_sha256`.
4. Chuyển file đã pack về Linux VM bằng kênh một chiều, trích feature (mục 5).
5. Ghi lại phiên bản packer + tuỳ chọn pack vào manifest (để tái tạo).

## 5. Trích feature

~~~
python src/extract_features.py --in ~/IAM302t/Datasets/g1_packed --group G1 \
    --family agenttesla --variant P-unseen --packer mpress \
    --origin-map map.csv --out part_g1_mpress.csv
~~~

Gộp các phần rồi chuẩn hoá bằng `--finalize` (xem `docs/huong_dan_pilot_khanh.md`, mục 4). Nếu có file `extract_errors.csv` thì đọc: đó là các mẫu bị bỏ qua.
Kiểm tra dataset trước khi giao: `python src/check_data.py <dataset.csv>` **[CHƯA KIỂM: xác nhận cú pháp trong file]**.

## 6. Cái gì được đưa ra khỏi VM

| Ra được | KHÔNG ra |
|---|---|
| `dataset.csv`, manifest (hash, nguồn), biểu đồ, báo cáo | file `.exe`, thư mục g0/g1, zip mẫu |

## 7. Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| UPX báo lỗi trên file .NET | Bình thường; dùng ConfuserEx (mục 4) |
| Dòng `[skip]` khi trích feature | Xem `extract_errors.csv`; thường do thiếu `origin_sha256` trong bản đồ |
| `ModuleNotFoundError` | Chưa bật `.venv` hoặc sai thư mục; chạy từ gốc repo |
| VM nghi nhiễm / hành vi lạ | Tắt VM, KHÔNG cho mạng, khôi phục snapshot sạch, báo leader |

## 8. Việc còn thiếu trước khi chốt SOP

- Lệnh/tuỳ chọn cụ thể của ConfuserEx, MPRESS, ASPack (mục 4).
- Cách chuyển file Windows VM -> Linux VM (kênh một chiều nào).
- Xác nhận `check_data.py` dùng thế nào.
