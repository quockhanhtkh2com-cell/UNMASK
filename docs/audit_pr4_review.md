# Audit PR #4 — Commit "runner E"
- **Trạng thái:** **APPROVED**

- **Pull Request:** [PR #4: F3: sửa baseline import-shrink theo is_dotnet, runner nạp config khoá, SOP VM, script khoá ngưỡng](https://github.com/quockhanhtkh2com-cell/UNMASK/pull/4)
- **Nhánh nguồn (Source branch):** `feat/tuan-gd2-f3`
- **Nhánh đích (Target branch):** `dev`
- **Commit được yêu cầu review:** `eadd223fc5952e3d16d8d79218de7d1d06b58763`
- **Commit message:** `runner E: F3 nap config khoa (--f3-config) thay PackedScorer() chua train + dual-check nguong 0`
- **File bị chỉnh sửa:** `experiments/run_experiments.py` (+27 dòng, -16 dòng)

---

## 2. Chi tiết thay đổi mã nguồn (Diff Analysis)

| Hạng mục | Trước thay đổi (Cũ) | Sau thay đổi (Commit `eadd223`) | Đánh giá |
|---|---|---|---|
| **Cổng F3** | Khởi tạo `PackedScorer()` chưa train và `DualCheck` cục bộ | Dùng hàm `_build_f3(dataset, f3_config, seed)` nạp `load_filter(f3_config)` | Tốt, đúng chuẩn kiến trúc |
| **Fallback chạy thử** | Không có fallback | Tự động huấn luyện tạm ra `/tmp/.../f3_tmp.json` kèm cảnh báo nếu chưa khoá config | Tránh crash khi chạy test |
| **Quyết định gate** | `_gate_decisions(gate, df, scorer, dual)` | `_gate_decisions(gate, df, f3_filter)` | Gọn hơn, giảm phụ thuộc |
| **CLI Argument** | Chưa có cờ config F3 | Bổ sung `--f3-config` vào `main()` | Hỗ trợ nạp `thresholds.locked.json` |
| **Drift Detector D1** | Fit G0 `train`, lock P95 G0 `val` | **Giữ nguyên không đổi** | **Ổn** |

## 3. Chạy test

### 3.1. Toàn bộ test suite (`pytest -q`)
- **Lệnh thực thi trên nhánh PR #4:**
  ```bash
  pytest -q
  ```
- **Kết quả:**
  ```
  ........................................................................ [ 80%]
  .................                                                        [100%]
  89 passed in 3.71s
  ```
  *(100% test pass, khớp với message)*

### 3.2. Chạy thí nghiệm thực tế (`run_experiments.py`)
- **Lệnh:**
  ```bash
  python experiments/run_experiments.py --exp e2 --dataset mock/mock_dataset.csv --seed 0 --pack-ratio 0.5
  ```
- **Terminal Output:**
  ```
  [CẢNH BÁO] chưa có config F3 khoá -> train TẠM từ dataset (số liệu chỉ để chạy thử, KHÔNG đưa vào báo cáo). Khoá thật: python unmask/train.py --dataset ... --out config/thresholds.locked.json
  [train] threshold=0.100  weights={'entropy_max_section': 0.53, 'entropy_file': 0.34, 'high_entropy_byte_ratio': 0.62, 'raw_virtual_ratio': 0.41, 'ep_section_writable': 0.65, 'import_table_shrink': 0.62, 'only_dynamic_loader_imports': 0.21, 'overlay_size': 0.33, 'section_class': 0.33, 'bias': -0.06}
  [train] ĐÃ KHOÁ -> /tmp/.../f3_tmp.json
  ⚠️  Commit file này TRƯỚC khi chạy E3–E5. Không sửa sau khi nhìn đề thi.
  exp gate  seed  pack_ratio_set  pack_ratio_real      FTR  FNR_G2  FNR_G3  correct_filter_Pseen  correct_filter_Punseen  correct_filter_Plow  correct_filter_Pwild  flagged_rate
   e2   F0     0             0.5              0.7 0.538462     0.0 0.00000                   0.0                0.000000                0.000              0.000000        0.0000
   e2   F1     0             0.5              0.7 0.538462     0.0 0.00000                   0.0                0.000000                0.000              0.000000        0.0000
   e2   F2     0             0.5              0.7 0.470588     0.0 1.00000                   1.0                1.000000                0.000              1.000000        0.0000
   e2   F3     0             0.5              0.7 0.269231     0.0 0.52381                   0.7                0.857143                0.875              0.666667        0.2125
  [e2] -> results/results_e2_0_50.csv
  ```
- **Kết quả file:** `results/results_e2_0_50.csv`

### 3.3. Kiểm thử thuật toán Isolation Forest
- **Lệnh:**
  ```bash
  python experiments/run_experiments.py --exp e2 --dataset mock/mock_dataset.csv --seed 0 --pack-ratio 0.5 --detector isolation_forest
  ```
- **Kết quả:** Chạy thành công, tính toán các chỉ số FTR/FNR bình thường.

## 4. Kết luận & Quyết định Review

1. **Tính tương thích:** Mã nguồn trong commit `eadd223` không ảnh hưởng đến luồng Drift Detector D1.
2. **Quyết định:** **APPROVED**.

---

## 5. Việc 2: Chốt thứ tự commit `config/thresholds.locked.json`

### 5.1. Phân chia trách nhiệm trong file
- **Tuấn:** `packed_score` (weights, threshold) và `dual_check` (similarity_threshold) qua `scripts/lock_f3.sh`.
- **Đức:** `detector_D1` (`threshold_value` tính P95 trên `G0 val` của dataset v1.0).
- **Khánh + Đức:** `test_set_sha256_manifest` (mã băm SHA-256 của tập test).
- **Chung:** `locked: true`, `locked_at`, `locked_by`.

### 5.2. Thứ tự thực hiện (tránh conflict JSON)
1. **Bước 1 (Khánh - T4 14/10):** Freeze `dataset_v1.0.csv` và cung cấp mã SHA-256 tập test.
2. **Bước 2 (Tuấn - T5 15/10):** Chạy `scripts/lock_f3.sh dataset_v1.0.csv` để khoá phần F3, sau đó commit lên git trước.
3. **Bước 3 (Đức):** 
   - Pull commit của Tuấn về máy.
   - Chạy tính ngưỡng P95 cho D1 trên `G0 val`, điền vào `detector_D1.threshold_value`.
   - Điền chuỗi SHA-256 tập test vào `test_set_sha256_manifest`.
   - Đổi `"locked": true`.
4. **Bước 4:** Commit file `config/thresholds.locked.json` hoàn chỉnh lên `dev` -> Khoá đề thi chính thức, bắt đầu chạy thí nghiệm E3–E5.

### 5.3. Kế hoạch thực hiện theo đề xuất của Tuấn
- Tuấn đã nạp dataset v1.0 và khoá tạm F3 ở commit `b50a0af`.
- Đức kéo trực tiếp `origin/feat/tuan-gd2-f3` về để điền D1 và SHA-256 vào config mà không cần chờ PR #4 merge.
- Khi Khánh merge PR #4 vào `dev`, Đức chỉ cần `git rebase origin/dev`.

### 5.4. Kết quả thực hiện thực tế (Đã hoàn thành)
1. **Merge code:** Đã merge `origin/feat/tuan-gd2-f3` (Fast-forward tới commit `b50a0af`).
2. **Tính toán ngưỡng D1:**
   - Dữ liệu: `dataset_v1.0.csv` (G0 train: 28 mẫu, G0 val: 10 mẫu).
   - Ngưỡng Mahalanobis P95 trên G0 val: `4.74531`.
3. **Cập nhật config & hash manifest:**
   - Điền `"detector_D1.threshold_value": 4.74531`.
   - Điền `"test_set_sha256_manifest": "b1af5270f0f198f5f922b867bc06562f01fe030fd3ac3280fceac4b3945a5919"` (từ `DATASET_VERSION.txt`).
4. **Kiểm thử & Commit:**
   - Chạy `pytest -q` đạt **90/90 passed**.
   - Commit: `2eaa45e` (`config: khoa nguong D1 (P95 G0 val) va chot SHA-256 test manifest v1.0`).


