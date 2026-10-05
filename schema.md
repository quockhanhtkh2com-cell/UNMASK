# SCHEMA — dataset.csv & manifest (chốt GĐ0: Khánh + Tuấn)

> Đây là **hợp đồng** giữa tất cả mọi người. Mọi file (mock & thật) phải đúng
> tên cột + kiểu dưới đây. Đổi cột = báo cả nhóm trước, sửa file này trước.

## 1. `dataset.csv` — mỗi dòng = 1 file (mẫu gốc hoặc biến thể)
Gồm **phần định danh + phần feature tĩnh + phần nhãn/split**.

### 1.1 Định danh
| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `sha256` | str | Hash SHA-256 (khoá chính) |
| `family` | str | Họ malware: `agenttesla` / `njrat` / `formbook` ... |
| `group` | str | Nhóm ground-truth: `G0` / `G1` / `G2` / `G3` |
| `variant` | str | Biến thể packer: `none` / `P-seen` / `P-unseen` / `P-low` / `P-wild` |
| `packer` | str | `none` / `upx` / `mpress` / `aspack` / `wild` |
| `origin_sha256` | str | Hash của **mẫu gốc** (để chia tập chống rò rỉ). Mẫu gốc tự trỏ về chính nó. |

### 1.2 Feature tĩnh (Tuấn trích bằng pefile/LIEF)
| Cột | Kiểu | Nhóm |
|---|---|---|
| `entropy_file` | float | Entropy |
| `entropy_max_section` | float | Entropy |
| `entropy_mean_section` | float | Entropy |
| `high_entropy_byte_ratio` | float | Tỉ lệ byte trong cửa sổ entropy > ngưỡng |
| `num_sections` | int | Section |
| `section_name_class` | str | `standard` / `known_packer` / `weird` |
| `raw_virtual_ratio` | float | raw size / virtual size (bất thường) |
| `ep_section_writable` | int (0/1) | Section chứa entry point có quyền ghi (W+X) |
| `num_dll` | int | Import |
| `num_api` | int | Import |
| `import_table_shrink` | float | Độ "teo" import so trung vị cùng họ |
| `only_dynamic_loader_imports` | int (0/1) | Chỉ có API nạp động cơ bản |
| `file_size` | int | Header |
| `size_of_headers` | int | Header |
| `checksum_valid` | int (0/1) | Header |
| `compile_timestamp` | int | Header (epoch) |
| `has_overlay` | int (0/1) | Header |
| `overlay_size` | int | Header |
| `is_dotnet` | int (0/1) | .NET metadata (quan trọng với AgentTesla) |

### 1.3 Nhãn & split
| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `is_drift_truth` | int (0/1) | Nhãn đúng: G0,G1=0 (không drift) · G2,G3=1 (drift thật) |
| `split` | str | `train` / `val` / `test` — chia theo `origin_sha256` |

## 2. `manifest.csv` — siêu dữ liệu + truy vết (dataset.csv là tập con feature)
Gồm **mọi cột định danh ở 1.1**, cộng thêm:
| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `die_result` | str | Kết quả Detect It Easy: `clean` / `packed` / `protected` / `unknown` |
| `removed_prepacked` | int (0/1) | 1 nếu bị loại khỏi G0/G2 vì đã pack sẵn |
| `pack_failed` | int (0/1) | 1 nếu pack thất bại (ghi theo packer — .NET hay lỗi) |
| `source` | str | `malwarebazaar` / `derived` |
| `timestamp_collected` | str | ISO time thu mẫu |
| `note` | str | Ghi chú tự do |

## 3. Quy ước đặt tên file output
- chữ thường, gạch dưới, **không dấu**.
- `results_<e>_<seed>_<tilepack>.csv` — ví dụ `results_e2_1_50.csv`
- `fig_ftr_per_gate.png`, `bang_chinh.csv`
- Mọi số **FTR phải kèm tỉ lệ pack**; **FNR báo riêng G2 và G3**.
