# SOP máy ảo (VM) — pack mẫu, trích feature, xuất kết quả

Người viết: Tuấn · 13/10/2026 · BẢN NHÁP v2 (cập nhật 14/10 theo thông tin Khánh cung cấp). Mục **[KHÁNH XÁC NHẬN]** là Khánh đã làm thật; mục **[CHƯA KIỂM]** chưa ai chạy thử, cần xác nhận trước khi coi là chuẩn.

Đọc `docs/SAFETY.md` trước. File này chỉ nói CÁCH LÀM; luật an toàn nằm ở SAFETY.md.

## 0. Nguyên tắc (tóm tắt)

- Mẫu là malware thật. Chỉ thao tác trong VM cô lập. Script chỉ ĐỌC file (pefile), không chạy mẫu.
- Không có thư mục chia sẻ ghi được với máy thật. Chỉ CSV/biểu đồ/báo cáo được đưa ra.
- Mẫu và file đã pack không lên git, không gửi qua chat. `.gitignore` chặn `data/**`.

## 1. Hai VM, hai việc

| VM | Dùng cho | Công cụ |
|---|---|---|
| Linux | UPX, trích feature, chạy thí nghiệm | `upx`, Python venv (`.venv`), `pefile`, `lief`, `pandas` |
| Windows | Packer chỉ chạy trên Windows | MPRESS **[KHÁNH XÁC NHẬN]**; ASPack, ConfuserEx (.NET) **[CHƯA KIỂM]**, Khánh bổ sung sau |

Linux VM của nhóm là Kali.

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

## 4. Pack bằng packer khác (Windows VM)

| Mục tiêu | Packer | Biến thể |
|---|---|---|
| G1 cho .NET | ConfuserEx | P-seen |
| G1/G3 cho cả .NET và native, packer chưa thấy khi train | MPRESS (dataset v1.0: 50 mẫu, gồm 36 .NET) | P-unseen |
| Native, packer chưa thấy, bổ sung ở v1.1 | ASPack **[CHƯA KIỂM]** | P-unseen |
| .NET, future work | ConfuserEx / .NET Reactor / Eazfuscator **[CHƯA KIỂM]** | ngoài phạm vi v1.0 (nhóm chốt P-seen chỉ gồm native/UPX) |

Lệnh MPRESS **[KHÁNH XÁC NHẬN]**, chạy trong CMD của Windows VM:

~~~
mpress.exe "<đường dẫn file>"
~~~

Lệnh của ASPack/ConfuserEx: **[ĐIỀN — Khánh, bổ sung sau]**.

Quy trình chung:
1. Chép file G0 vào VM Windows.
2. Pack bằng packer, đặt tên `<origin_sha256>_<packer>.exe`.
3. Lập bảng ánh xạ `map.csv` hai cột `filename,origin_sha256`.
4. Chuyển file đã pack về Kali (xem mục 4.1), trích feature (mục 5).
5. Ghi lại phiên bản packer + tuỳ chọn pack vào manifest (để tái tạo).

### 4.1. Đường chuyển file Windows VM -> Kali **[KHÁNH XÁC NHẬN]**

~~~
Windows VM -> thư mục chia sẻ -> máy thật (host) -> WinSCP -> Kali
~~~

Lưu ý an toàn: luật 1 trong `docs/SAFETY.md` cấm thư mục chia sẻ GHI ĐƯỢC với máy thật. Đường chuyển trên có đi qua thư mục chia sẻ và máy thật nên cần nhóm thống nhất cách giảm rủi ro, ví dụ: thư mục chia sẻ chỉ chứa file zip có mật khẩu, không bao giờ mở/giải nén trên máy thật, xoá ngay sau khi chuyển. **[NHÓM CHỐT: chọn cách nào và ghi lại ở đây]**

## 5. Trích feature

~~~
python src/extract_features.py --in ~/IAM302t/Datasets/g1_packed --group G1 \
    --family agenttesla --variant P-unseen --packer mpress \
    --origin-map map.csv --out part_g1_mpress.csv
~~~

Gộp các phần rồi chuẩn hoá bằng `--finalize` (xem `docs/huong_dan_pilot_khanh.md`, mục 4). Nếu có file `extract_errors.csv` thì đọc: đó là các mẫu bị bỏ qua.
Kiểm tra dataset trước khi giao (đã chạy thật trên v1.0, 13/10):

~~~
python src/check_data.py --dataset dataset_v1.0.csv --manifest manifest_v1.0.csv
~~~

Kết quả v1.0: dataset 16/16 PASS; manifest FAIL vì thiếu cột die_result, removed_prepacked, pack_failed, source, timestamp_collected, note (Khánh đang bổ sung).

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

- Lệnh ASPack và ConfuserEx (Khánh bổ sung sau).
- Nhóm chốt cách giảm rủi ro cho đường chuyển file qua thư mục chia sẻ (mục 4.1) so với SAFETY.md.
- Mốc dataset chính thức (v1.1) và SHA-256 của nó.
