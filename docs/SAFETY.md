# AN TOÀN & ĐẠO ĐỨC — đọc trước khi đụng vào mẫu

> Mẫu trong đề tài là **malware THẬT**. Dù đề tài không chạy mẫu (chỉ trích feature tĩnh),
> file vẫn nguy hiểm. Mọi thao tác tuân thủ các luật dưới đây — không ngoại lệ.

## Luật bắt buộc
1. **VM cô lập**: mọi thao tác pack/trích feature chỉ làm trong VM riêng
   (Linux cho UPX/pefile/LIEF; Windows cho MPRESS/ASPack). Không có thư mục
   chia sẻ **ghi được** với máy thật.
2. **Không mở / double-click / giải nén mẫu trên máy cá nhân.**
3. **Chỉ tắt antivirus TRONG VM**, không bao giờ trên máy thật.
4. Mẫu & biến thể luôn nằm trong **zip có mật khẩu**. Chỉ `dataset.csv`,
   biểu đồ và báo cáo được đưa ra khỏi VM.
5. **Không phát hành file đã pack.** Dataset công bố chỉ gồm feature, hash, script tái tạo.
6. **Demo Streamlit chỉ chạy localhost**, không public. README có cảnh báo
   rõ: công cụ chỉ đọc file tĩnh, **không chạy file**.

## Git
- **KHÔNG commit** file mẫu / đã pack (`.gitignore` đã chặn `data/**`).
- Chỉ commit: feature (`dataset.csv` thật nếu nhóm đồng ý), hash, script.
- Mock data thì commit thoải mái để code song song.

## Dual-use
- Ghi một mục ngắn về đạo đức & dual-use trong báo cáo cuối.
