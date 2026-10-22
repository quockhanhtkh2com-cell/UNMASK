# SOP máy ảo (VM) — pack mẫu, trích feature, xuất kết quả

Người viết: Tuấn · Bản cuối (v3), 22/10/2026 · Khớp dataset v1.1 và thông tin Khánh xác nhận ngày 18/10.

Đọc `docs/SAFETY.md` trước. File này chỉ nói CÁCH LÀM; luật an toàn nằm ở SAFETY.md.

## 0. Nguyên tắc (tóm tắt)

- Mẫu là malware thật. Chỉ thao tác trong VM cô lập. Script chỉ ĐỌC file (pefile), không chạy mẫu.
- KHÔNG dùng thư mục chia sẻ ghi được với máy thật. Chiều máy thật -> VM: mount chỉ đọc hoặc ISO. Chiều giữa các VM: SFTP qua mạng host-only (mục 4.1).
- VM luôn tắt mạng ngoài (chỉ host-only) khi có mẫu sống.
- Chỉ CSV/biểu đồ/báo cáo được đưa ra khỏi VM; không mang file binary ra.
- Mẫu và file đã pack không lên git, không gửi qua chat. `.gitignore` chặn `data/**`.

## 1. Hai VM, hai việc

| VM | Dùng cho | Công cụ |
|---|---|---|
| Linux (Kali) | UPX, trích feature, chạy thí nghiệm | `upx`, Python venv (`.venv`), `pefile`, `lief`, `pandas` |
| Windows (Win2008) | MPRESS | `mpress.exe` v2.19 |

Quy tắc antivirus: chỉ tắt TRONG VM Windows; không tắt trên máy thật.
Trước khi làm: chụp snapshot "sạch" của VM; làm xong thì khôi phục snapshot nếu đã chạm mẫu lạ.

## 2. Chuẩn bị Linux VM

~~~
cd ~/IAM/UNMASK && git fetch origin && git switch dev && git pull
source .venv/bin/activate
python -m pytest -q          # phải xanh (90 passed)
which upx                    # phải có
sha256sum dataset_v1.1.csv   # phải bắt đầu bằng caed7ef9
~~~

Thư mục dữ liệu (nằm NGOÀI repo):

~~~
~/IAM302t/Datasets/g0_unpacked/   # G0 gốc, đã giải nén
~/IAM302t/Datasets/g1_packed/     # G1 sinh ra (đặt tên <origin_sha256>_<packer>.exe)
~~~

## 3. Pack bằng UPX (Kali, native, nhóm P-seen)

~~~
python3 src/pack_extract_g1.py \
    --in  ~/IAM302t/Datasets/g0_unpacked \
    --packed-out ~/IAM302t/Datasets/g1_packed \
    --out part_g1.csv --packer upx --variant P-seen
~~~

- Lệnh UPX tương đương: `upx --best --force -o <out>.exe <in>.exe`.
- Script ghi `origin_sha256` (sha256 của file G0 gốc) để chia train/val/test không rò rỉ.
- UPX KHÔNG pack được file .NET. File .NET dùng MPRESS (mục 4).

## 4. Pack bằng MPRESS (Windows VM, native và .NET, nhóm P-unseen)

| Packer | Nền | Biến thể | Số mẫu trong v1.1 |
|---|---|---|---|
| UPX | native | P-seen | 39 (G1) |
| MPRESS v2.19 | native và .NET | P-unseen | 117 (G1) + 153 (G3) = 270 |

Lệnh, chạy trong CMD của Windows VM (pack tại chỗ):

~~~
mpress.exe "<đường dẫn file>.exe"
~~~

Nguồn gốc MPRESS (để tái lập): bản lấy từ Wayback Machine, SHA-256 bắt đầu bằng 19ffee9 và kết thúc bằng 736c5.

Ngoài phạm vi v1.1: ASPack đã bỏ; ConfuserEx (.NET) để làm hướng phát triển sau (future work), không có mẫu nào trong v1.1.

Quy trình chung:
1. Chép file G0 hoặc G2 sống vào VM Windows.
2. Pack bằng MPRESS, đặt tên `<origin_sha256>_mpress.exe`.
3. Lập bảng ánh xạ `map.csv` hai cột `filename,origin_sha256`.
4. Chuyển file đã pack sang Kali (mục 4.1), trích feature (mục 5).
5. Ghi phiên bản packer và tuỳ chọn pack vào manifest để tái tạo.

### 4.1. Chuyển file (đúng SAFETY.md)

- Windows VM -> Kali: SFTP qua mạng host-only (WinSCP tới Kali chạy openssh).
- Máy thật -> VM: mount chỉ đọc hoặc ISO.
- VM -> ngoài: chỉ file feature CSV. Không mang binary ra.
- Không dùng thư mục chia sẻ ghi được.

Ghi chú trung thực: khi dựng dataset v1.1, khâu pack đã dùng thư mục chia sẻ ghi được. Mẫu không bị thực thi và mạng đã tắt nên dữ liệu không bị ảnh hưởng. Từ nay chỉ dùng cách ở trên.

## 5. Trích feature và kiểm dataset

~~~
python src/extract_features.py --in ~/IAM302t/Datasets/g1_packed --group G1 \
    --family agenttesla --variant P-unseen --packer mpress \
    --origin-map map.csv --out part_g1_mpress.csv
~~~

Gộp các phần rồi chuẩn hoá bằng `--finalize` (xem `docs/huong_dan_pilot_khanh.md`, mục 4). Nếu có `extract_errors.csv` thì đọc: đó là các mẫu bị bỏ qua.

Kiểm dataset trước khi giao (phải PASS cả dataset và manifest):

~~~
python src/check_data.py --dataset dataset_v1.1.csv --manifest manifest_v1.1.csv
~~~

## 6. Cái gì được đưa ra khỏi VM

| Ra được | KHÔNG ra |
|---|---|
| `dataset.csv`, manifest (hash, nguồn), biểu đồ, báo cáo | file `.exe`, thư mục g0/g1, zip mẫu |

## 7. Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| UPX báo lỗi trên file .NET | Bình thường; dùng MPRESS (mục 4) |
| Dòng `[skip]` khi trích feature | Xem `extract_errors.csv`; thường do thiếu `origin_sha256` trong bản đồ |
| `ModuleNotFoundError` | Chưa bật `.venv` hoặc sai thư mục; chạy từ gốc repo |
| VM nghi nhiễm / hành vi lạ | Tắt VM, KHÔNG cho mạng, khôi phục snapshot sạch, báo leader |

## 8. Tham chiếu dataset v1.1 (đã freeze)

- `dataset_v1.1.csv` SHA-256: `caed7ef9feff39621a4146e84f3b803bd87de94ae283addc6e0e580e02bdeb82`
- `manifest_v1.1.csv` SHA-256: `cad95fbff82a3e8940ba6a064b691e439b9d4e07e5c9fd9087d9e6f5993cf214`
- Tập test (404 mẫu) SHA-256: `50ee5320e0305fd1b47eb74a0fb60d72467fb904821a156d2891a814c5107a68`
  Cách tính: lấy sha256 các dòng `split == test`, viết thường, sắp tăng dần, mỗi hash một dòng kèm newline cuối, rồi băm toàn bộ bằng SHA-256.
- 596 dòng: G0 122, G1 156 (UPX 39 + MPRESS 117), G2 165, G3 153; split train 140 / val 52 / test 404.
