# DiE thật cho cổng F1 — ghi chú (manifest v1.1)

Quét: Khánh (Kali). Rà số, bỏ mã màu, đưa lên repo: Tuấn.

## Công cụ và môi trường

- Detect It Easy dòng lệnh `diec` **phiên bản 3.21** (`die 3.21`), bản portable Linux, chạy qua `diec.sh`.
- Hệ điều hành: Kali Linux **2026.3** (Kali Rolling, máy của Khánh).
- SHA-256 của gói DiE portable đã dùng: file `die_3.21_portable_Ubuntu_20.04_amd64.tar.gz`, SHA-256 `4d85614dd169c0d23f52084f86e05a503c30429df5fb5ec14de50f23808bc2d4`. (Gói `.deb` Ubuntu 26.04 mà Tuấn cài thử có SHA-256 `ef4474d93e00f3644ea680518c43b3a65fe3fb739f6d7eac5d13b82235f339b5`, nhưng đó không phải bản dùng để quét.)
- Lệnh chạy cho từng mẫu: `diec.sh <đường_dẫn_mẫu>` (quét mặc định, chỉ phân tích tĩnh, không thực thi mẫu). Timeout 30 giây mỗi mẫu.
- Mạng khi quét: **không tắt** (máy quét vẫn nối mạng). DiE chỉ phân tích tĩnh, không thực thi mẫu.
- Script: `scripts/run_die_real.py` (bản của Khánh; Tuấn chỉ thêm đoạn bỏ mã màu ANSI khỏi output). Mẫu được khớp với manifest bằng cách **tự tính SHA-256 từng file** (tên file ở G1/G3 không phải SHA-256).
- Không sửa `manifest_v1.1.csv` và `dataset_v1.1.csv`.

## Cách quy đổi output của DiE sang nhãn `die_result_real`

- Có dòng `Protector: …` → **protected**
- Không có Protector nhưng có dòng `Packer: …` → **packed**
- Output rỗng, hoặc dòng đầu có chữ "unknown" → **unknown**
- Còn lại → **clean** (DiE không thấy packer/protector)
- Trong 596 mẫu không có mẫu nào vừa có Packer vừa có Protector, nên thứ tự ưu tiên trên không ảnh hưởng kết quả.
- `die_detect`: dòng Packer/Protector đầu tiên (đã bỏ mã màu). `die_raw`: toàn bộ output, các dòng nối bằng " | " (đã bỏ mã màu ANSI, nội dung giữ nguyên).

## Số lượng theo nhóm (596/596 mẫu, thiếu 0)

| group | clean | packed | protected | unknown |
|---|---|---|---|---|
| G0 | 110 | 0 | 12 | 0 |
| G1 | 0 | 156 | 0 | 0 |
| G2 | 158 | 2 | 5 | 0 |
| G3 | 0 | 153 | 0 | 0 |

Tổng theo nhóm: G0 122, G1 156, G2 165, G3 153.

## DiE phát hiện gì

| group | DiE phát hiện | số mẫu |
|---|---|---|
| G0 | Protector: .NET Reactor(6.X)[Control Flow, Anti-ILDASM] | 11 |
| G0 | Protector: .NET Reactor(6.X)[Control Flow] | 1 |
| G1 | Packer: MPRESS(2.19) | 117 |
| G1 | Packer: UPX(4.24)[NRV, brute] | 39 |
| G2 | Packer: UPX(3.95)[NRV, brute] | 1 |
| G2 | Packer: UPX(4.24)[NRV, brute] | 1 |
| G2 | Protector: .NET Reactor(6.X)[Control Flow, Anti-ILDASM] | 4 |
| G2 | Protector: PELock(2.X) | 1 |
| G3 | Packer: MPRESS(2.01-2.12)[modified] | 1 |
| G3 | Packer: MPRESS(2.19) | 152 |

## Quan sát

- **G1 và G3 (đã đóng gói bằng UPX/MPRESS): DiE nhận ra 309/309 mẫu là `packed`** (G1: UPX 39/39, MPRESS 117/117; G3: MPRESS 153/153, trong đó 1 mẫu DiE ghi "MPRESS(2.01-2.12)[modified]").
- **G0 (AgentTesla sạch): 0 mẫu `packed`, nhưng 12/122 mẫu `protected`** (cả 12 đều là .NET Reactor 6.X, một công cụ làm rối .NET, không phải packer). Nếu F1-DiE tính cả `protected` là "đã đóng gói" thì 12 mẫu G0 này bị báo nhầm.
- **Bonus G2 (họ khác, chưa đóng gói thêm): DiE nhận 2/165 là `packed`** (đều UPX: 3.95 và 4.24) **và 5/165 là `protected`** (4 .NET Reactor, 1 PELock).
- 4 mẫu G2 có output "Unknown: Unknown" (DiE không khớp chữ ký nào) đang được gán `clean` theo quy tắc trên. Gán `unknown` hay `clean` không đổi kết quả cổng, vì cả hai đều không bị F1 chặn.
- Cột `die_result` đã gán sẵn trong manifest chưa được so sánh trong file này (không có manifest ở máy rà số). Đức hoặc Khánh đối chiếu khi chạy lưới.

## Cách dùng trong lưới F1-DiE

- Đọc cột `die_result_real`, nối theo `sha256`.
- Gợi ý chạy hai biến thể: **F1-DiE = chỉ `packed`** (chính) và **F1-DiE+protected = `packed` hoặc `protected`** (độ nhạy).

## Toàn vẹn file

- File Khánh gửi (còn mã màu): SHA-256 `87b0b7a4480c73b0914bacb26ec50f5c5878ab98a8985c467563e576370084d1`
- `results/die_real_v1.1.csv` trong repo (đã bỏ mã màu): SHA-256 `27f8ec36553dd2994f1d55d2400d86f6be390025a7f85d73ca9771d59d101481`
- Cột `sha256`, `group` và `die_result_real` giống hệt file gốc.
