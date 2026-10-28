# Dual-check — các ca cứu được (T2)

Dữ liệu: split `test` (n=404). Ngưỡng dual-check khóa: `13.2057`; đặc trưng lõi: `file_size, size_of_headers, compile_timestamp, is_dotnet`; số mẫu tham chiếu: 62.

**Ca cứu** = F3a (không dual-check) loại, F3 giữ lại (FLAGGED): **4** mẫu. Chiều ngược lại (F3a giữ, F3 loại): 0 mẫu.

## 1. Bảng các ca

| sha12 | group | family | packer | score | dist | dist/threshold | lech_nhat |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 050a583da770 | G3 | emotet | mpress | 0.864 | 14.670 | 1.111 | file_size |
| 8875d2ef9ad1 | G3 | emotet | mpress | 0.864 | 14.271 | 1.081 | file_size |
| 71e4cb8a40f9 | G3 | emotet | mpress | 0.780 | 14.854 | 1.125 | file_size |
| e2d9b73cbcd7 | G3 | azorult | mpress | 0.600 | 22.417 | 1.698 | file_size |

`dist` = khoảng cách Euclid chuẩn hóa tới mẫu tham chiếu gần nhất; `dist/threshold` > 1 nghĩa là 'novel'. `lech_nhat` = đặc trưng lõi lệch nhiều nhất so với mẫu tham chiếu gần nhất.

## 2. Dual-check trên mọi mẫu có packed_score >= ngưỡng

| group | packer | n_score>=thr | similar(FILTERED) | novel(FLAGGED) | dist_median |
|:---:|:---:|:---:|:---:|:---:|:---:|
| G1 | mpress | 14.000 | 14.000 | 0.000 | 2.203 |
| G1 | upx | 15.000 | 15.000 | 0.000 | 0.069 |
| G2 | none | 2.000 | 2.000 | 0.000 | 7.410 |
| G3 | mpress | 71.000 | 67.000 | 4.000 | 2.233 |

## 3. Giá trị đặc trưng lõi của các ca cứu

| sha12 | core_file_size | core_size_of_headers | core_compile_timestamp | core_is_dotnet |
|:---:|:---:|:---:|:---:|:---:|
| 050a583da770 | 7013888 | 512 | 1716979988 | 0 |
| 8875d2ef9ad1 | 6868480 | 512 | 1721308274 | 0 |
| 71e4cb8a40f9 | 7048192 | 512 | 1075356784 | 0 |
| e2d9b73cbcd7 | 9823232 | 512 | 1574160675 | 0 |

## 4. Nhận xét

1. **Cơ chế**: 4 ca cứu đều là G3 (drift thật đóng gói MPRESS): 3 emotet và 1 azorult. Cả 4 đều lệch nhiều nhất ở file_size so với mẫu tham chiếu gần nhất; dist/threshold từ 1.08 đến 1.70 (ngưỡng khóa 13.2057 = P95 khoảng cách của G0 val). F3a và F2 loại 4 mẫu này, F3 gắn cờ để chuông vẫn xét.
2. **Giới hạn**: trong 71 mẫu G3 có packed_score >= ngưỡng, chỉ 4 mẫu (5.6%) bị gắn novel; 67 mẫu (94.4%) vẫn 'similar' (khoảng cách trung vị 2.233, gần với G1-MPRESS là 2.203). Dual-check dựa trên 4 đặc trưng lõi (file_size, size_of_headers, compile_timestamp, is_dotnet) nên gần như không phân biệt được drift thật bị MPRESS với AgentTesla bị MPRESS.
3. **Thống kê**: McNemar F3 so với F3a có b=4, c=0, p=0.1336 (chưa có ý nghĩa thống kê). Chỉ nên nói dual-check cho xu hướng có lợi, không nói đã giải quyết giới hạn L1.
