# Bảng chính F0–F3 — v1.1 (MẪU RỖNG, chờ số thật)

> ⚠️ Đây là **template** đúng định dạng theo `SPEC_ketqua_chi_so.md`. Đức chạy E1–E6 trên `dataset_v1.1.csv` xong thì **thay `__` bằng số thật** (mean ± std qua 3 seed, kèm Wilson 95% CI).
> Dataset test = 404 mẫu · F3 khóa 0.475 · P-low/P-wild = "—" (không có ở v1.1).

## Bảng chính (FTR kèm tỉ lệ pack; FNR tách G2/G3)

| gate | FTR@30 | FTR@50 | FTR@70 | FNR_G2 | FNR_G3 | correct_Pseen | correct_Punseen | correct_Plow | correct_Pwild | flagged_rate |
|:----:|:------:|:------:|:------:|:------:|:------:|:-------------:|:---------------:|:------------:|:-------------:|:------------:|
| F0  | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__` | `__` | — | — | `0` |
| F1  | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__` | `__` | — | — | `__` |
| F2  | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__` | `__` | — | — | `__` |
| F3  | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__` | `__` | — | — | `__` |
| F3a | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__ ±__` | `__` | `__` | — | — | `__` |

*`±` = Wilson 95% CI (nửa độ rộng) hoặc std qua seed — ghi rõ chú thích chọn kiểu nào.*

## Bảng kiểm định McNemar (ghép cặp trên cùng 404 mẫu test)

| So sánh | b (F3 đúng, kia sai) | c (F3 sai, kia đúng) | p-value | Kết luận |
|:---|:---:|:---:|:---:|:---|
| F3 vs F1 (DiE) | `__` | `__` | `__` | `__ (hơn/kém có ý nghĩa?)` |
| F3 vs F2 (entropy) | `__` | `__` | `__` | `__` |
| F3 vs F3a (ablation) | `__` | `__` | `__` | `__ (dual-check có đóng góp?)` |

> Điền xong nhớ: **không chỉnh ngưỡng F3 dù số xấu** — đo sao báo vậy.
