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

## Cải thiện giao diện và giữ báo cáo khi chuyển tab

- Sửa nguyên nhân xóa bảng mỗi lần đổi báo cáo: giữ cache giao diện theo mã, loại báo cáo, quý/năm và khoảng năm, có giới hạn 12 tổ hợp gần nhất. Quay lại khôi phục cả bộ lọc, đơn vị và khung kỳ; kết quả trả chậm không ghi đè lựa chọn khác.
- Bảng màu sáng được xác định rõ để tránh phụ thuộc màu hệ thống Windows; nút lấy dữ liệu có màu chính và trạng thái đang tải. Các ô chọn năm/quý dùng nút +/− trực tiếp, có tính độ rộng theo font và tỷ lệ hiển thị.
- Tổng quan chuyển sang hồ sơ doanh nghiệp, thẻ chỉ số, thông tin niêm yết và bảng so sánh ngành. Giữ rõ số 0, dữ liệu thiếu, đơn vị gốc; không suy diễn thang phần trăm khi schema nguồn chưa mô tả.
- 44 kiểm thử đạt trong bản sửa, bao gồm chuyển tab, đổi mã/kỳ/năm, kết quả đến muộn, giới hạn cache, thao tác nút tăng/giảm, trình bày tổng quan và dữ liệu ngành. Kiểm tra ảnh GUI sử dụng dữ liệu công khai đã lấy từ Finhay.

## Thu gọn nhật ký và thông tin nguồn

- Nhật ký chuyển thành khung đóng/mở, mặc định ẩn; thanh trạng thái chỉ hiện dòng thông tin gần nhất. Không dành sẵn vùng nhật ký trong nội dung dữ liệu.
- Dòng nguồn Tổng quan hiển thị một dòng thời điểm lấy mới nhất theo giờ Việt Nam; timestamp đầy đủ của từng nhóm được giữ trong tooltip và file xuất.
- Nhật ký giới hạn 300 dòng, nhận thông tin từ worker qua Qt slot trên luồng giao diện. Bộ kiểm thử giữ một QApplication xuyên suốt và giải phóng cửa sổ sau mỗi test để tránh lỗi hủy đối tượng Qt khi thoát.
- 48 kiểm thử đạt, gồm mở/ẩn log không mất nội dung, giới hạn số dòng, cập nhật từ worker và chuyển thời điểm qua ngày theo giờ Việt Nam. GUI mở và thoát thành công.

## Tải đủ sáu bộ báo cáo trong một lần bấm

- Nút lấy dữ liệu tài chính tải 3 loại báo cáo × 2 chế độ quý/năm cho mã và khoảng năm đã chọn, dùng một phiên MCP và ưu tiên bộ đang xem.
- Mỗi bộ hoàn tất được chuyển ngay sang cache giao diện đúng ngữ cảnh; người dùng có thể chuyển loại báo cáo/chế độ trong lúc tải. Kết quả không bị trộn giữa quý và năm.
- Lỗi công cụ ở một bộ không hủy những bộ khác; mất kết nối/xác thực dừng tác vụ và giữ bộ đã hoàn tất. Bộ tải dở không được đánh dấu đầy đủ. Tôn trọng lựa chọn Lấy mới/dùng cache.
- 55 kiểm thử đạt: bổ sung kiểm tra đủ 6 bộ, thứ tự ưu tiên, số lần gọi, lỗi một phần, dừng giữa chừng, lỗi mạng/xác thực và thao tác GUI bấm một lần rồi đổi qua cả 6 lựa chọn mà không gọi tải thêm.

## Sửa lỗi quét hàng loạt và bổ sung ba kỳ so sánh

- Đã đọc trạng thái lượt quét cũ ở chế độ chỉ đọc: 33 lỗi RuntimeError sau các mã đầu tiên. Đã tái hiện thông báo nguồn `Rate limit exceeded. Current weight used: 129/130. Retry after 22 seconds.` trong CallToolResult.isError, không phải HTTP 429. Bản cũ đã bỏ qua loại giới hạn này.
- Phân loại và thử lại theo Retry after của lỗi MCP, không lưu lỗi giới hạn làm lỗi dữ liệu của mã. Hết số lần thử sẽ dừng với mã còn pending. Bổ sung phân biệt thiếu dữ liệu/xác thực; giữ metadata trên lỗi thật và tạm dừng sau 3 lỗi không xác định liên tiếp.
- Bảng mới có doanh thu/LNST của kỳ hiện tại, kỳ trước, cùng kỳ; % QoQ/YoY và nhóm ngành. Kỳ thiếu giữ trống, không tự thế kỳ khác. Mẫu bảo hiểm được bổ sung từ trường ABI thực tế: doanhthuthuan, lnstthunhapdn, lnstcuacongtyme.
- Đã quét nhỏ bằng kết nối app riêng với dữ liệu thật AAA, AAS, AAT, ABB, ABI, FPT quý III/2026; cả 6 có ba kỳ doanh thu/LNST và nhóm ngành. Đối chiếu lại dữ liệu đã lưu sau khi thêm mẫu bảo hiểm. Với kỳ gốc LNST âm (AAT QoQ), % để trống theo quy tắc hiện tại, vẫn giữ cả hai số và chênh lệch.
- Cập nhật dòng GUI theo từng mã thay vì đọc lại toàn bộ lượt quét sau mỗi mã. Cột kỹ thuật mặc định ẩn, có thể mở; xuất file ưu tiên nhãn và cột đang xem, đơn vị tiền gốc VND. Lượt cũ được bổ sung khi người dùng chọn tiếp tục; không tự chạy toàn thị trường trong kiểm thử.
- 69 kiểm thử đạt, bổ sung kiểm tra giới hạn MCP thực tế, chờ có thể hủy, không ghi sai quota thành lỗi mã, ba kỳ và lũy kế, phân ngành, metadata, circuit breaker, giữ dữ liệu khi thiếu ngành, nâng cấu trúc lượt cũ và các cột/xuất file mới.

## Biểu đồ nến ngày và tuần

- Biểu đồ giá chuyển sang nến OHLC xanh/đỏ (đóng > mở / đóng < mở), nến bằng giá xám, kèm khối lượng. Biểu đồ chiếm vùng chính; bảng dữ liệu mặc định ẩn, có thể mở gọn và đổi tỷ lệ bằng thanh phân cách.
- Có khung Ngày/Tuần; tuần được tổng hợp từ các phiên ngày theo tuần thứ Hai giờ Việt Nam, không gọi thêm Finhay. Bảng và xuất file theo khung đang xem. OHLC không đủ/sai không được dùng để bịa nến; khối lượng thiếu vẫn thiếu.
- Có hover OHLC, zoom bằng cuộn chuột, kéo ngang và đặt lại Toàn bộ. Chuỗi dài mặc định xem tối đa 150 nến để giữ độ rõ.
- Kiểm tra ảnh từ cache MWG thật: 130 phiên ngày, gộp thành 27 tuần. Không phát sinh tải giá mới trong kiểm tra ảnh. Đã kiểm tra cả bảng ẩn/mở trên kích thước màn hình thực tế.
- 76 kiểm thử đạt, có kiểm tra gộp OHLC/khối lượng, mốc tuần theo giờ Việt Nam và qua năm, dữ liệu trùng/thiếu, màu nến, đổi khung không gọi mạng, bảng/xuất file đúng khung và zoom/chuỗi rỗng/một nến.

## Bố cục chart và tỷ lệ từng nến

- Chuyển bộ chọn ngày/nút tải/chi tiết nến sang sidebar có thể ẩn; biểu đồ chỉ giữ một thanh công cụ gọn. Sidebar cuộn độc lập khi cửa sổ thấp.
- Hai tỷ lệ được ghi rõ: đóng so mở và đóng so đóng nến trước, đổi đúng cơ sở khi chuyển ngày/tuần. Không dùng giá cũ hơn thay cho giá đóng cửa bị thiếu của nến liền trước.
- 78 kiểm thử đạt; bổ sung kiểm tra phần trăm âm/dương/0, cơ sở thiếu/không hợp lệ, đổi khung và ẩn sidebar mở rộng chart. Kiểm tra ảnh từ cache giá MWG ở chế độ chỉ đọc, không gọi Finhay.

## MA / Bollinger Bands / RSI

- Công thức thuần Python, không thêm thư viện: SMA trung bình đơn giản; BB dùng độ lệch chuẩn tổng thể; RSI dùng Wilder với seed trung bình N biến động rồi làm mượt (N−1)/N. RSI chuỗi phẳng quy ước 50, chỉ tăng 100, chỉ giảm 0.
- 89 kiểm thử: đối chiếu RSI chuỗi giá đã biết ở seed và bước làm mượt, BB/SMA tính tay, warm-up, thiếu/0/âm/NaN, tham số không hợp lệ, giữ zoom khi đổi chỉ báo, tính lại từ đóng cửa tuần, giá trị hover và không phát sinh mạng.
- Đã kiểm tra ảnh ngày/tuần, khi mở bảng và hộp tùy chọn với cache MWG chỉ đọc; sidebar cuộn độc lập, nút chu kỳ dùng dấu +/− rõ ràng. Chưa đủ lịch sử thì bỏ trống giá trị, không tự tải thêm.
