# data/ — KHÔNG commit mẫu lên git

Thư mục này chỉ tồn tại để chứa mẫu **trong VM**. `.gitignore` đã chặn toàn bộ.

```
raw/         G0 (AgentTesla chưa pack) + G2 (njRAT/Formbook/AgentTesla khác thời kỳ)
packed/      G1 = G0 × {upx,mpress,aspack} ; G3 = G2 × {upx,mpress,aspack}
lowentropy/  P-low: pack rồi chèn dữ liệu entropy thấp
wild/        P-wild: mẫu bị crypter/packer bọc sẵn ngoài đời
```

## SOP pack thủ công trong VM (GĐ1 — Khánh làm tay, KHÔNG tự động hoá trong repo)
Theo phân công & SAFETY.md, bước pack malware thật là thao tác **thủ công có kiểm soát trong VM cô lập**, không viết script tự động trong repo công khai. Quy trình:

1. Pilot 10–20 mẫu .NET với 3 packer → ghi tỉ lệ lỗi vào `pilot_pack.csv`
   (cột: `packer,total,failed,fail_rate`). .NET rất hay pack lỗi — biết sớm.
2. Lọc mẫu đã pack sẵn bằng **Detect It Easy** trước khi đưa vào G0/G2;
   ghi `die_result` + số bị loại theo họ vào manifest.
3. Pack G1/G3, tạo P-low, thu P-wild → ghi `pack_failed` theo packer.
4. Chạy `src/extract_features.py` **trong VM** trên các thư mục trên → sinh
   `dataset.csv` + `manifest.csv` THẬT (thay mock).
5. Chỉ mang `dataset.csv` + `manifest.csv` (feature + hash) ra khỏi VM.

> Lý do không để script pack trong repo: (1) an toàn/đạo đức — tránh phát tán
> công cụ tạo malware đã pack; (2) đề tài chỉ cần feature, không cần tái tạo file.
