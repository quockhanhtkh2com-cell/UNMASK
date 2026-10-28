# F3 so với F2 — giải thích (T1)

Dữ liệu: dataset v1.1, split `test` (n=404). Config khóa: `packed_score.threshold = 0.475`. Script `experiments/explain_f3.py` chỉ đọc config, không train, không đổi ngưỡng.

## 1. Trọng số logistic của packed_score (feature đã chuẩn hóa nên so sánh được độ lớn)

| rank | feature | weight_std | abs_weight | mean_abs_contrib | mean_contrib_packed | mean_contrib_unpacked |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ep_section_writable | 1.965 | 1.965 | 1.755 | 1.306 | -0.849 |
| 2 | raw_virtual_ratio | -1.075 | 1.075 | 1.061 | -0.135 | -0.512 |
| 3 | section_class | 0.641 | 0.641 | 0.229 | 0.316 | 0.142 |
| 4 | import_table_shrink | -0.484 | 0.484 | 0.413 | 0.247 | -0.255 |
| 5 | entropy_max_section | 0.472 | 0.472 | 0.424 | 0.128 | -0.104 |
| 6 | overlay_size | 0.385 | 0.385 | 0.392 | 0.238 | -0.135 |
| 7 | high_entropy_byte_ratio | 0.342 | 0.342 | 0.310 | 0.025 | -0.098 |
| 8 | only_dynamic_loader_imports | 0.234 | 0.234 | 0.211 | 0.079 | -0.125 |
| 9 | entropy_file | -0.095 | 0.095 | 0.089 | -0.045 | 0.051 |

`mean_contrib_*` = đóng góp trung bình của feature vào điểm (trọng số x giá trị chuẩn hóa) trên nhóm bị pack (G1+G3) và không pack (G0+G2) của tập test. Dấu âm của trọng số nghĩa là feature đó kéo điểm xuống khi các feature khác cố định.

## 2. packed_score có thực chất là luật entropy không?

| chỉ số | giá trị |
|:---:|:---:|
| corr(packed_score, entropy_max_section) | 0.484 |
| AUC packed_score (pack G1+G3 vs G0+G2) | 0.765 |
| AUC entropy_max_section | 0.662 |
| AUC ep_section_writable | 0.726 |
| AUC section_name_class (0/0.7/1) | 0.663 |
| tỉ lệ F2 và F3 cùng quyết định FILTERED/không | 0.950 |
| tỉ lệ F2(FILTERED) và packed_score>=ngưỡng trùng nhau | 0.960 |

## 3. Quyết định F2 và F3 theo nhóm x packer (tập test)

| group | packer | n | F2_FILTERED | F3_FILTERED | F3_FLAGGED | F3_PASS | F3a_FILTERED | ca_khac_nhau(F2 vs F3 FILTERED) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| G0 | none | 36 | 2 | 0 | 0 | 36 | 0 | 2 |
| G1 | mpress | 35 | 14 | 14 | 0 | 21 | 14 | 0 |
| G1 | upx | 15 | 15 | 15 | 0 | 0 | 15 | 0 |
| G2 | none | 165 | 16 | 2 | 0 | 163 | 2 | 14 |
| G3 | mpress | 153 | 71 | 67 | 4 | 82 | 71 | 4 |

FILTERED = loại khỏi chuông D1. F3 chia điểm cao thành FILTERED (dual-check `similar`) và FLAGGED (`novel`, vẫn vào chuông). Danh sách từng ca khác nhau: `results/f3_vs_f2_disagree.csv`.

Tổng số mẫu F2 và F3 quyết định FILTERED khác nhau: **20/404**.

## 4. Nhận xét

1. **F3 khác F2 ở 20/404 mẫu (4.95%)**, trùng đúng với McNemar F3 so với F2 (b=20, c=0): F3 đúng hơn ở cả 20 mẫu.
   - 14 mẫu G2 (drift thật): F2 loại nhầm 16 mẫu, F3 chỉ loại 2 (FNR_G2 từ 0.097 xuống 0.012).
   - 2 mẫu G0 (sạch): F2 loại, F3 cho qua.
   - 4 mẫu G3: F2 loại, F3 gắn cờ FLAGGED nhờ dual-check.
2. **Ở nhóm G1, F3 và F2 giống hệt**: UPX 15/15, MPRESS 14/35. Vì vậy correct_Punseen của F2, F3 và F3a trùng nhau; giá trị trên đủ 404 mẫu test là 14/35 = 0.400 (n=35). F3 không hơn F2 ở packer chưa gặp.
3. **packed_score không chỉ là luật entropy**: tương quan với entropy_max_section là 0.484; AUC 0.765 so với 0.662 (entropy) và 0.726 (ep_section_writable). Tuy nhiên điểm bị chi phối bởi ep_section_writable (trọng số chuẩn hóa 1.965, lớn nhất; đóng góp trung bình +1.306 ở nhóm pack so với -0.849 ở nhóm không pack). Mô hình học trên G0 và G1-UPX nên đây là dấu hiệu đặc trưng của UPX, nên MPRESS bị bỏ sót tương tự F2.
4. Dấu âm của raw_virtual_ratio (-1.075) và import_table_shrink (-0.484) chưa được kiểm chứng ý nghĩa; không diễn giải nhân quả. import_table_shrink dùng baseline theo is_dotnet (trung vị .NET = 1 API) nên thông tin hạn chế.
5. AUC tính với nhãn pack là G1+G3 (gồm cả MPRESS), nên một phần AUC thấp là do bỏ sót MPRESS.
