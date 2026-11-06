# Kết quả kiểm tra — 06/11/2026

- `run.bat` đã chạy từ đầu: tải Python portable, cài dependencies và mở GUI thành công trên Windows. Không đóng gói ứng dụng `.exe`.
- OAuth thực tế: discovery và đăng ký client thành công; người dùng cấp quyền qua trình duyệt; ứng dụng liệt kê được 82 công cụ và lấy 4 quý báo cáo FPT năm 2025 bằng phiên riêng của app.
- Đọc dữ liệu thật: hồ sơ, thông tin niêm yết, chỉ số tổng quan, giá hiện tại, 20 dòng lịch sử giá FPT trong khoảng thử, 14 sự kiện quyền; bảng cân đối và lưu chuyển tiền tệ có 4 kỳ năm 2025.
- Quét thử FPT, VCB, SSI quý IV/2025: có doanh thu theo đúng mẫu và cả hai chỉ tiêu LNST. Cơ sở quý giữ `unknown`, không tính tăng trưởng từ số chưa xác minh. Tiếp tục lượt đã hoàn tất không tạo bản ghi trùng.
- Phân trang toàn thị trường: 1.516 mã do Finhay trả tại thời điểm thử, gồm HOSE 408, HNX 299, UPCoM 809. Chưa chạy tải báo cáo tài chính cho toàn bộ 1.516 mã.
- 28 kiểm thử tự động đạt: chuẩn hóa 3 mẫu báo cáo, kỳ thiếu, quý I/quý IV, lũy kế, tăng trưởng âm/0, SQLite và tiếp tục sau gián đoạn, xuất file/giữ chính xác số nguyên lớn, callback state/issuer, OAuth PKCE/đăng ký/refresh giả lập, retry, SSE không khóa yêu cầu công cụ, lọc/sắp xếp và mở lại GUI.
- Đã sửa lỗi chờ lâu do khóa OAuth của SDK với luồng SSE nền; kiểm tra lại kết nối thật sau sửa lấy báo cáo trong vài giây.

## Cập nhật cách trình bày báo cáo tài chính

- Bảng chuyển sang chỉ tiêu × kỳ, thứ tự thời gian từ cũ đến mới; các mẫu KQKD doanh nghiệp thường, ngân hàng và chứng khoán có thứ tự chỉ tiêu riêng. Nhãn tiếng Việt bao phủ các trường đã kiểm tra trên FPT, VCB, SSI và bảng cân đối/lưu chuyển tiền tệ FPT.
- Cột tên cố định; mặc định 8 kỳ gần nhất, có chuyển cửa sổ kỳ; tìm kiếm, chỉ tiêu chính, đơn vị tỷ/triệu/VND và xu hướng nhỏ. EPS giữ đơn vị riêng; số thiếu, số 0 và số âm được phân biệt. Xuất cùng bố cục và giữ giá trị gốc.
- Tổng cộng **36 kiểm thử đạt**, có kiểm tra thứ tự kỳ, quý thiếu, EPS, đơn vị, sắp thứ tự chỉ tiêu theo ngành, xuất bảng đang xem và cột cố định khi cuộn ngang/dọc thực tế.
- Đã mở lại GUI qua run.bat và kiểm tra ảnh chụp bảng mới bằng dữ liệu FPT đã lấy từ Finhay. Ảnh: `financial-preview.png`.

Giới hạn: nguồn báo cáo chưa khai báo cơ sở quý riêng/lũy kế hoặc hợp nhất/riêng lẻ. App giữ trạng thái chưa xác minh và cho người dùng chọn cơ sở quý khi đã kiểm chứng. Làm mới token và các tình huống lỗi được kiểm thử với HTTP giả lập; tài khoản thật đã được thử đăng nhập và mở phiên mới.
