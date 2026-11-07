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
- **Giá cổ phiếu:** biểu đồ nến và khối lượng chiếm vùng chính. Chọn **Ngày (1D)** hoặc **Tuần (1W)** tại Khung nến. Nến xanh khi đóng cửa cao hơn mở cửa, đỏ khi thấp hơn, xám khi bằng nhau. Rê chuột xem OHLC/khối lượng, cuộn để phóng/thu, kéo ngang để xem phiên khác, bấm Toàn bộ để xem hết khoảng đã tải. Với chuỗi dài, mặc định xem tối đa 150 nến gần nhất để dễ đọc.
- Bảng giá mặc định ẩn; bật **Hiện bảng dữ liệu** để mở bảng gọn phía dưới và kéo thanh phân cách nếu cần. Ngày hiển thị theo lịch Việt Nam, không còn dạng Unix hoặc các cột metadata lặp lại. Bảng và file xuất theo khung ngày/tuần đang chọn.
- Nến tuần được gộp trên máy từ dữ liệu ngày đã tải: mở của phiên đầu, cao nhất, thấp nhất, đóng của phiên cuối và tổng khối lượng. Đổi khung không gọi thêm API. Tuần bắt đầu thứ Hai theo giờ Việt Nam; tuần đầu/cuối có thể chỉ gồm các phiên trong khoảng ngày đã chọn. Thiếu OHLC không được tự điền để tạo nến; thiếu khối lượng không đổi thành 0.
- **Quét kết quả kinh doanh:** để danh sách mã trống để quét toàn thị trường do Finhay cung cấp, hoặc nhập `FPT, VCB, SSI`. Chọn sàn, quý/năm, kỳ cụ thể, rồi Chạy lượt quét mới.
- Mỗi mã trong bảng quét có **doanh thu và LNST toàn doanh nghiệp** của kỳ được chọn, kỳ liền trước và cùng kỳ năm trước, cùng % thay đổi so hai mốc. Nhóm ngành lấy từ hồ sơ Finhay (ưu tiên cấp nhóm ngành), được giữ riêng với loại chỉ tiêu doanh thu. Với ngân hàng dùng tổng thu nhập hoạt động; chứng khoán dùng doanh thu hoạt động; bảo hiểm dùng doanh thu thuần theo mẫu nguồn.
- Các cột chính ưu tiên số liệu so sánh và nhóm ngành. Bật **Cột chi tiết** để xem LNST công ty mẹ, chênh lệch tuyệt đối, cơ sở kỳ, thời điểm lấy và thông tin kỹ thuật. Excel/CSV xuất các cột đang hiển thị với nhãn tiếng Việt, giữ số tiền VND gốc.
- Finhay giới hạn truy vấn theo trọng số và có thể báo giới hạn trong kết quả MCP dù HTTP thành công. App tự chờ đúng thời gian Retry after rồi thử lại, tối đa 4 lần mỗi yêu cầu; khi vẫn bị giới hạn sẽ tạm dừng và giữ mã trong hàng chờ, không gán lỗi dữ liệu hàng loạt. Có thể tạm dừng trong lúc chờ. Ba lỗi chưa xác định liên tiếp cũng làm lượt quét tạm dừng để kiểm tra nguồn.
- Khi tiếp tục lượt quét tạo bằng bản cũ, các kết quả chưa có cấu trúc so sánh mới được đưa lại vào hàng chờ để bổ sung các trường; dữ liệu cũ được giữ đến khi có kết quả thay thế. Các kết quả đã hoàn tất bằng cấu trúc mới không bị chạy lại khi tiếp tục bình thường. Nhóm ngành đã lưu được tái sử dụng giữa các lượt để giảm lượt gọi.
- Với bảng quét và các bảng tra cứu thông thường: bấm tiêu đề cột để sắp xếp, nhập ô lọc và chọn trạng thái để lọc. Xuất bảng đang lọc giữ thứ tự đang xem; Xuất toàn bộ giữ toàn bộ dữ liệu của lượt quét.
- **Bảng tài chính:** mỗi hàng là một chỉ tiêu tiếng Việt, mỗi cột là một quý/năm, từ cũ đến mới. Cột tên chỉ tiêu cố định khi cuộn ngang; kỳ mới nhất và các chỉ tiêu tổng hợp được in đậm, số âm màu đỏ. Mặc định xem 8 kỳ gần nhất, dùng ‹/› để lùi/tiến hoặc chọn 12 kỳ/Tất cả kỳ. Có tìm chỉ tiêu, lọc Chỉ tiêu chính và biểu đồ xu hướng nhỏ cho khung kỳ đang xem.
- **Một lần lấy đủ báo cáo:** nút Lấy dữ liệu trong phần tài chính tải cả 3 báo cáo (kết quả kinh doanh, cân đối kế toán, lưu chuyển tiền tệ), mỗi loại có cả quý và năm, cho mã và khoảng năm đã chọn. Ưu tiên lựa chọn đang xem trước, sau đó tải các bộ còn lại trong cùng một kết nối. Có tiến độ 0/6 đến 6/6; có thể đổi tab hoặc quý/năm trong lúc tải để xem bộ đã hoàn tất. Các mục khác như Tổng quan/Giá/Cổ tức vẫn dùng nút lấy dữ liệu riêng.
- Nếu một bộ báo cáo bị lỗi nguồn, những bộ thành công vẫn được giữ và app báo số bộ chưa tải được. Nếu mất kết nối hoặc hết phiên đăng nhập, tác vụ dừng để kết nối lại. Dừng giữa chừng không đánh dấu một bộ mới lấy được vài năm là đã tải đầy đủ.
- Khi chuyển giữa Kết quả kinh doanh / Cân đối kế toán / Lưu chuyển tiền tệ, app giữ kết quả đã tải cùng bộ lọc, đơn vị và khung kỳ cho từng mã, loại báo cáo, quý/năm và khoảng năm. Trong một phiên, bộ nhớ đệm giao diện giữ tối đa 12 tổ hợp gần nhất; phản hồi nguồn vẫn lưu trong SQLite. Lựa chọn chưa tải sẽ có thông báo rõ ràng, không hiển thị nhầm dữ liệu của lựa chọn trước.
- Các ô chọn năm/quý có nút **− / +** luôn hiển thị; có thể gõ trực tiếp giá trị. Nút **Lấy dữ liệu** màu xanh là thao tác chính và chuyển thành **Đang tải…** trong lúc chạy.
- **Tổng quan** hiển thị tên doanh nghiệp, ngành, mô tả hoạt động, thông tin niêm yết và các chỉ số tài chính bằng nhãn tiếng Việt. Trung bình ngành nằm ở cột riêng; trường thiếu ghi **Chưa có dữ liệu**, khác với số 0. Không hiển thị JSON hoặc tên công cụ MCP trong nội dung tổng quan.
- Nhật ký chi tiết mặc định ẩn. Bấm **Nhật ký** ở thanh trạng thái để mở/đóng; trạng thái gần nhất vẫn hiển thị một dòng khi nhật ký đóng. Nhật ký giữ tối đa 300 dòng trong bộ nhớ. Dòng nguồn ở Tổng quan chỉ hiện thời điểm lấy mới nhất theo giờ Việt Nam; rê chuột để xem chi tiết từng nhóm dữ liệu.
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

Biểu đồ giá ưu tiên vùng vẽ; bộ chọn ngày, lấy dữ liệu, giá hiện tại và chi tiết nến đặt bên phải. Nút Thông tin ẩn/hiện cột này. Rê chuột lên nến xem % so mở cửa và % so đóng cửa nến trước, theo khung ngày/tuần đang chọn; thiếu giá gốc hiển thị —.

### Chỉ báo trên biểu đồ giá

Bấm **Chỉ báo** cạnh nút Toàn bộ để bật/tắt từng đường: hai MA đơn giản (mặc định 20 và 50 nến), Bollinger Bands (20 nến, 2 độ lệch chuẩn) và RSI Wilder (14 nến, mốc 30/70). Có thể chỉnh chu kỳ từ 2–500 nến và hệ số BB từ 0,1–5; cập nhật ngay, giữ mức zoom. MA/BB trên vùng giá, RSI ở vùng riêng bên dưới khối lượng. Giá trị chỉ báo của nến đang rê chuột hiển thị trong cột thông tin (cuộn xuống nếu cần).

Chỉ báo tính trên toàn bộ dữ liệu đã tải của khung đang chọn, trước khi giới hạn khung nhìn. Đổi ngày/tuần sẽ tính lại; không gọi thêm Finhay. MA/BB cần đủ N giá đóng cửa, RSI cần N+1 giá đóng cửa liên tiếp. Giá đóng cửa thiếu/không hợp lệ làm khởi động lại chuỗi tính. Nếu cần thêm lịch sử cho chỉ báo, chọn khoảng ngày rộng hơn và tải lại. Các tùy chọn giữ trong phiên làm việc hiện tại.
