# Finhay Desktop

Ứng dụng Python GUI tiếng Việt để đọc dữ liệu Finhay MCP. Không cần API key OpenAI hoặc mô hình AI.

## Chạy trên Windows

1. Giữ nguyên thư mục ứng dụng và bấm đúp **run.bat**.
2. Lần đầu cần Internet: script tải Python 3.12.10 x64 từ python.org vào `.runtime`, sau đó cài thư viện từ PyPI. Không cần Python cài sẵn hoặc quyền Administrator. Những lần sau dùng lại môi trường này.
3. Bấm **Kết nối Finhay**. App tự đăng ký OAuth client nếu Finhay cho phép, mở trình duyệt để bạn đăng nhập và cấp scope `read:market`.
4. Sau khi trình duyệt báo nhận callback, quay lại app và chờ thông báo kết nối thành công. App sẽ liệt kê công cụ và thử lấy báo cáo FPT bằng kết nối riêng.

Nếu Windows chặn script tải xuống, kiểm tra nguồn file và chọn Unblock trong Properties nếu cần. Script và mã nguồn có thể đọc trước khi chạy.

## Sử dụng

- **Tra cứu cổ phiếu:** nhập mã, hoặc bấm Tải danh sách mã rồi tìm theo mã/tên. Chọn tab và bấm Lấy dữ liệu. Báo cáo cho chọn loại, quý/năm và khoảng năm; giá có khoảng ngày và biểu đồ; sự kiện có cổ tức cùng các quyền khác.
- **Quét kết quả kinh doanh:** để danh sách mã trống để quét toàn thị trường do Finhay cung cấp, hoặc nhập `FPT, VCB, SSI`. Chọn sàn, quý/năm, kỳ cụ thể, rồi Chạy lượt quét mới.
- Với bảng quét và các bảng tra cứu thông thường: bấm tiêu đề cột để sắp xếp, nhập ô lọc và chọn trạng thái để lọc. Xuất bảng đang lọc giữ thứ tự đang xem; Xuất toàn bộ giữ toàn bộ dữ liệu của lượt quét.
- **Bảng tài chính:** mỗi hàng là một chỉ tiêu tiếng Việt, mỗi cột là một quý/năm, từ cũ đến mới. Cột tên chỉ tiêu cố định khi cuộn ngang; kỳ mới nhất và các chỉ tiêu tổng hợp được in đậm, số âm màu đỏ. Mặc định xem 8 kỳ gần nhất, dùng ‹/› để lùi/tiến hoặc chọn 12 kỳ/Tất cả kỳ. Có tìm chỉ tiêu, lọc Chỉ tiêu chính và biểu đồ xu hướng nhỏ cho khung kỳ đang xem.
- Bảng tài chính cho đổi Tỷ VND / Triệu VND / VND; EPS giữ VND/cổ phiếu. Di chuột vào ô để xem số gốc và thời điểm lấy từ Finhay. Các kỳ bị thiếu ở giữa khoảng báo cáo được giữ thành cột “—”. Xuất đang xem giữ các chỉ tiêu/kỳ đang lọc; Xuất tất cả giữ toàn bộ chỉ tiêu/kỳ đã tải, theo cùng bố cục chỉ tiêu × kỳ, với đơn vị gốc ghi riêng từng hàng.
- Danh sách toàn thị trường lấy thành phần VNINDEX/HNXINDEX/UPCOMINDEX, phân trang theo mã để giữ thứ tự ổn định; không tính mã quốc tế hoặc mã đã hủy niêm yết ngoài danh sách sàn của nguồn.
- Tạm dừng có hiệu lực giữa các mã; yêu cầu mạng đang chạy có thể cần đợi timeout. Mở lại app, chọn lượt quét cũ và bấm Tiếp tục. Chạy lại mã lỗi chỉ đưa mã lỗi trở về hàng chờ. Muốn kiểm tra lại các mã thiếu dữ liệu, tạo lượt quét mới với Lấy mới được bật.
- Bỏ chọn Lấy mới để ưu tiên dữ liệu đã lưu. Lượt quét cũ giữ nguyên kỳ, phạm vi, cơ sở quý và chế độ cache khi tiếp tục. Muốn thay đổi cấu hình, tạo lượt mới.

## Ý nghĩa số liệu

- Bảng quét hiển thị tiền theo tỷ VND; dữ liệu SQLite và file xuất giữ giá trị tiền gốc. Giá cổ phiếu giữ VND. Các trường đơn vị của nguồn được giữ trong dữ liệu nếu có.
- Số nguyên từ 16 chữ số trở lên được ghi dạng văn bản trong Excel để tránh giới hạn chính xác 15 chữ số của Excel. CSV giữ toàn bộ chữ số.
- Doanh nghiệp thường: doanh thu thuần. Ngân hàng: tổng thu nhập hoạt động. Công ty chứng khoán: doanh thu hoạt động. Không gộp ba loại này thành một định nghĩa mà không ghi nhãn.
- Có cả LNST toàn doanh nghiệp và LNST thuộc cổ đông công ty mẹ; trường thiếu là trống, không phải 0. Mẫu chưa nhận diện được được đánh dấu để kiểm tra.
- Nguồn hiện chưa có trường xác định quý riêng/lũy kế trong schema báo cáo. Mặc định app **chưa tính tăng trưởng quý**. Chỉ chọn “Đã kiểm chứng” nếu đã đối chiếu cơ sở kỳ cho các mã/kỳ trong lượt quét. Đây là xác nhận của người dùng, không phải xác minh tự động của app.
- Với lũy kế, app lấy quý hiện tại trừ quý liền trước trong cùng năm; quý I giữ nguyên. Kỳ so sánh cũng được chuyển đổi tương tự. Thiếu kỳ để trừ thì không tính.
- Khi cơ sở quý chưa xác định, số doanh thu/LNST là số nguyên trạng nguồn trả về và có ghi chú. Không so sánh những số này bằng %.
- Quý so cùng quý năm trước và quý liền trước; quý I lấy quý IV năm trước. Năm so năm trước. App không dùng kỳ gần nhất để thế vào kỳ thiếu.
- Công thức % là `(hiện tại - kỳ gốc) / kỳ gốc × 100`, chỉ khi kỳ gốc dương. Nếu kỳ gốc không dương, chỉ có chênh lệch và diễn giải chuyển lãi/lỗ. Không tự kết luận báo cáo hợp nhất, riêng lẻ hoặc đã kiểm toán.
- Báo cáo chi tiết dùng tên tiếng Việt cho các mẫu đã nhận diện; mã chỉ tiêu Finhay được giữ trong tooltip và file xuất để truy vết. Chỉ tiêu mới chưa có nhãn vẫn giữ mã nguồn, không tự đổi nghĩa.

## Dữ liệu và đăng nhập

- Dữ liệu, phản hồi JSON gốc đã giải mã và tiến độ: `%LOCALAPPDATA%\FinhayDesktop\finhay.sqlite3`.
- Token và thông tin đăng ký client: Windows Credential Manager, service `FinhayDesktop-v1`. Không ghi token vào SQLite, file xuất hay log.
- Ngắt kết nối xóa credential riêng của app trên máy; không xóa dữ liệu đã lấy. Có thể thu hồi quyền ứng dụng trên Finhay để vô hiệu hóa quyền ở phía máy chủ.
- App dùng endpoint chỉ đọc `https://mcp.fhsc.com.vn/mcp`, allowlist công cụ dữ liệu thị trường, scope `read:market`. Không gọi công cụ tài khoản hoặc giao dịch.
- Nếu Finhay không cho đăng ký tự động, cung cấp cho bộ phận hỗ trợ: public desktop OAuth client, Authorization Code + PKCE S256, token endpoint auth `none`, scope `read:market`, callback **http://127.0.0.1:8769/callback**. Không nhập mật khẩu vào app hoặc sao chép token từ plugin.
- Cổng 8769 cần trống. Nếu chưa thấy trình duyệt, kiểm tra trình duyệt mặc định; nếu hết 5 phút, kết nối lại.

## Phát triển và kiểm thử

Python 3.12 x64. Cài `requirements.txt`, chạy `python main.py`. Cài thêm pytest để chạy `python -m pytest tests -q`.

Các module: `auth` quản lý OAuth/vault; `client` gọi MCP và cache; `finance` chuẩn hóa; `storage` lưu SQLite; `engine` chạy nền/quét; `gui` giao diện; `exporting` xuất file.

Kiểm thử giao diện không cần kết nối: `python main.py --data-dir ./test-data --smoke ./preview.png`.

Tài liệu nhà cung cấp: https://fhsc.com.vn/finhay-mcp?installationTab=mcp
