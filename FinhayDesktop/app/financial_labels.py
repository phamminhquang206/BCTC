"""Presentation labels and statement order; never calculate accounting values."""

_LABELS = '''
doanhthubanhangvacungcapdichvu|Doanh thu bán hàng và cung cấp dịch vụ
cackhoangiamtrudoanhthu|Các khoản giảm trừ doanh thu
doanhthuthuanvebanhangvacungcapdichvu|Doanh thu thuần
giavonhangban|Giá vốn hàng bán
loinhuangopvebanhangvacungcapdichvu|Lợi nhuận gộp
doanhthuhoatdongtaichinh|Doanh thu hoạt động tài chính
chiphitaichinh|Chi phí tài chính
trongdochiphilaivay|Trong đó: Chi phí lãi vay
phanlailohoaclotrongcongtyliendoanhlienket|Phần lãi/lỗ trong công ty liên doanh, liên kết
chiphibanhang|Chi phí bán hàng
chiphiquanlydoanhnghiep|Chi phí quản lý doanh nghiệp
loinhuanthuantuhoatdongkinhdoanh|Lợi nhuận thuần từ hoạt động kinh doanh
thunhapkhac|Thu nhập khác
chiphikhac|Chi phí khác
loinhuankhac|Lợi nhuận khác
tongloinhuanketoantruocthue|Tổng lợi nhuận kế toán trước thuế
chiphithuetndnhienhanh|Chi phí thuế TNDN hiện hành
chiphithuetndnhoanlai|Chi phí thuế TNDN hoãn lại
loinhuansauthuethunhapdoanhnghiep|Lợi nhuận sau thuế thu nhập doanh nghiệp
loiichcuacodongthieuso_bctn|Lợi nhuận sau thuế của cổ đông không kiểm soát
loinhuansauthuecuacongtyme|Lợi nhuận sau thuế của cổ đông công ty mẹ
laicobantrencophieu|Lãi cơ bản trên cổ phiếu (EPS)
laisuygiamtrencophieu|Lãi suy giảm trên cổ phiếu
thunhaplaivacackhoanthunhaptuongtu|Thu nhập lãi và các khoản thu nhập tương tự
chiphilaivacacchiphituongtu|Chi phí lãi và các chi phí tương tự
thunhaplaithuan|Thu nhập lãi thuần
thunhaptuhoatdongdichvu|Thu nhập từ hoạt động dịch vụ
chiphihoatdongdichvu|Chi phí hoạt động dịch vụ
laithuantuhoatdongdichvu|Lãi thuần từ hoạt động dịch vụ
lailothuantuhoaydongkinhdoanhngoaihoivavang|Lãi/lỗ thuần từ kinh doanh ngoại hối và vàng
lailothuantumuabanchungkhoankinhdoanh|Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh
lailothuantumuabanchungkhoandautu|Lãi/lỗ thuần từ mua bán chứng khoán đầu tư
thunhaptuhoatdongkhac|Thu nhập từ hoạt động khác
chiphihoatdongkhac|Chi phí hoạt động khác
lailothuantuhoatdongkhac|Lãi/lỗ thuần từ hoạt động khác
thunhaptugopvonmuacophan|Thu nhập từ góp vốn, mua cổ phần
tongthunhaphoatdong|Tổng thu nhập hoạt động
chiphihoatdong|Chi phí hoạt động
loinhuanthuantuhdkdtruocchiphiduphongruirotindung|Lợi nhuận thuần trước chi phí dự phòng rủi ro tín dụng
chiphiduphongruirotindung|Chi phí dự phòng rủi ro tín dụng
tongloinhuantruocthue|Tổng lợi nhuận trước thuế
chiphithuethunhapdoanhnghiep|Chi phí thuế thu nhập doanh nghiệp
loinhuansauthue|Lợi nhuận sau thuế
loiichcuacodongthieuso_pl|Lợi nhuận của cổ đông không kiểm soát
codongcuacongtyme|Lợi nhuận của cổ đông công ty mẹ
doanhthuhoatdong|Doanh thu hoạt động
laitucactaisantcfvtpl|Lãi từ tài sản tài chính ghi nhận qua lãi/lỗ (FVTPL)
laibantaisantcfvtpl|Lãi bán tài sản tài chính FVTPL
chenhlechtangvedglcacfvtpl|Chênh lệch tăng đánh giá lại tài sản FVTPL
cotuctienlaiphatsinhtutaisantcfvtpl|Cổ tức, tiền lãi phát sinh từ tài sản FVTPL
chenhlechgiamdglchungquyen|Chênh lệch giảm đánh giá lại chứng quyền
laitucackhoandautunamgiudenngaydaohanhtm|Lãi từ đầu tư nắm giữ đến ngày đáo hạn (HTM)
laitucackhoanchovayvaphaithu|Lãi từ các khoản cho vay và phải thu
laitutaisantcsansangdebanafs|Lãi từ tài sản tài chính sẵn sàng để bán (AFS)
laitucaccongcuphatsinhphongnguaruiro|Lãi từ công cụ phái sinh phòng ngừa rủi ro
doanhthuhoatdongmoigioick|Doanh thu môi giới chứng khoán
doanhthubaolanhdailyphathanhck|Doanh thu bảo lãnh, đại lý phát hành chứng khoán
doanhthutuvandautuck|Doanh thu tư vấn đầu tư chứng khoán
doanhthuhoatdonguythacdaugia|Doanh thu ủy thác, đấu giá
doanhthuhoatdongluukyck|Doanh thu lưu ký chứng khoán
doanhthuhoatdongtuvantc|Doanh thu tư vấn tài chính
doanhthuhoatdongkhac|Doanh thu hoạt động khác
cphoatdong|Chi phí hoạt động
lotucactaisantcfvtpl|Lỗ từ tài sản tài chính FVTPL
lotubancactaisantcfvtpl|Lỗ bán tài sản tài chính FVTPL
chenhlechgiamdglcacfvtpl|Chênh lệch giảm đánh giá lại tài sản FVTPL
cpgdmuacactaisantcfvtpl|Chi phí giao dịch mua tài sản FVTPL
chenhlechtangdglchungquyen|Chênh lệch tăng đánh giá lại chứng quyền
locackhoandautunamgiudenngaydaohanhtm|Lỗ đầu tư nắm giữ đến ngày đáo hạn
cplaivaylotucackhoanchovayvaphaithu|Chi phí lãi vay, lỗ từ cho vay và phải thu
lovachenhlechdgltaisanafskhiphanloailai|Lỗ và chênh lệch đánh giá lại tài sản AFS khi phân loại lại
lotucactaisantcphaisinhphongnguaruiro|Lỗ từ tài sản phái sinh phòng ngừa rủi ro
cpdphoannhaptstc|Chi phí dự phòng/hoàn nhập tài sản tài chính
cphoatdongtudoanh|Chi phí hoạt động tự doanh
cphoatdongmoigioick|Chi phí môi giới chứng khoán
cphoatdongbaolanhdailyphathanhck|Chi phí bảo lãnh, đại lý phát hành
cphoatdongtuvandautuck|Chi phí tư vấn đầu tư chứng khoán
cphoatdongdaugiauythac|Chi phí đấu giá, ủy thác
cpnghiepvuluukyck|Chi phí nghiệp vụ lưu ký chứng khoán
cphoatdongtuvantc|Chi phí tư vấn tài chính
cphoatdongkhac|Chi phí hoạt động khác
lngop|Lợi nhuận gộp
doanhthuhoatdongtc|Doanh thu hoạt động tài chính
chenhlechlaitygiahoidoaidavachuathuchien|Chênh lệch lãi tỷ giá đã và chưa thực hiện
doanhthuduthucotuclaitienguikhongcodinh|Doanh thu dự thu cổ tức, lãi tiền gửi không cố định
laibanthanhlycackhoandautulkld|Lãi bán, thanh lý đầu tư liên kết, liên doanh
doanhthukhacvedautu|Doanh thu khác về đầu tư
cptc|Chi phí tài chính
chenhlechlotygiahoidoaidavachuathuchien|Chênh lệch lỗ tỷ giá đã và chưa thực hiện
cplaivay_pl|Chi phí lãi vay
cpdpcackhoandaututcdaihan|Chi phí dự phòng đầu tư tài chính dài hạn
cptckhac|Chi phí tài chính khác
lailotucongtyliendoanhlienket|Lãi/lỗ từ công ty liên doanh, liên kết
cpbanhang|Chi phí bán hàng
cpql|Chi phí quản lý
ketquahoatdongkd|Kết quả hoạt động kinh doanh
lnkhac|Lợi nhuận khác
cpkhac|Chi phí khác
tonglnketoantruocthue|Tổng lợi nhuận kế toán trước thuế
lndathuchien_pl|Lợi nhuận đã thực hiện
lnchuathuchien_pl|Lợi nhuận chưa thực hiện
cpthuetndn|Chi phí thuế TNDN
cpthuetndnhienhanh|Chi phí thuế TNDN hiện hành
cpthuetndnhoanlai|Chi phí thuế TNDN hoãn lại
lnsauthue|Lợi nhuận sau thuế
lnsauthuecuachusohuu|Lợi nhuận sau thuế của chủ sở hữu
loiichcuacodongthieuso|Lợi ích của cổ đông không kiểm soát
lnsauthuephanbokhac|Lợi nhuận sau thuế phân bổ khác
thunhaptoandienkhacsauthuetndn|Thu nhập toàn diện khác sau thuế TNDN
lailotudanhgialaicackhoandautugiudenngaydaohan|Lãi/lỗ đánh giá lại đầu tư giữ đến ngày đáo hạn
lailotudanhgialaicactaisantcsansangdeban|Lãi/lỗ đánh giá lại tài sản sẵn sàng để bán
lailotoandienkhacduocchiatuhoatdongdautuvaocongtycon|Lãi/lỗ toàn diện khác từ đầu tư vào công ty con
lailochenhlechtygiacuahoatdongtainuocngoai|Lãi/lỗ chênh lệch tỷ giá hoạt động ở nước ngoài
lailotucackhoandautuvaocongtyconcongtylienketliendoanh|Lãi/lỗ từ đầu tư vào công ty con, liên kết, liên doanh
lailodanhgiacongcuphaisinh|Lãi/lỗ đánh giá công cụ phái sinh
lailotudanhgialaicaccongcutcphaisinh|Lãi/lỗ đánh giá lại công cụ tài chính phái sinh
lailodanhgialaitaisancodinhtheomohinhgiatrihoply|Lãi/lỗ đánh giá lại TSCĐ theo giá trị hợp lý
lailokhac|Lãi/lỗ khác
tongthunhaptoandien|Tổng thu nhập toàn diện
tongthunhaptoandienphanbochocodongthieuso|Thu nhập toàn diện phân bổ cho cổ đông không kiểm soát
tongthunhaptoandienphanbochovonchusohuu|Thu nhập toàn diện phân bổ cho chủ sở hữu
thunhapphaloangtrencophieu|Thu nhập pha loãng trên cổ phiếu
taisannganhan|Tài sản ngắn hạn
tienvacackhoantuongduongtien|Tiền và các khoản tương đương tiền
tien|Tiền
cackhoantuongduongtien|Các khoản tương đương tiền
cackhoandaututaichinhnganhan|Đầu tư tài chính ngắn hạn
chungkhoankinhdoanh|Chứng khoán kinh doanh
duphonggiamgiachungkhoankinhdoanh|Dự phòng giảm giá chứng khoán kinh doanh
dautunamgiudenngaydaohan_dttcnh|Đầu tư nắm giữ đến ngày đáo hạn — ngắn hạn
cackhoanphaithunganhan|Các khoản phải thu ngắn hạn
phaithukhachhang|Phải thu khách hàng
tratruocchonguoiban|Trả trước cho người bán
phaithunoibonganhan|Phải thu nội bộ ngắn hạn
phaithutheotiendokehoachhopdongxaydung|Phải thu theo tiến độ hợp đồng xây dựng
phaithuvechovaynganhan|Phải thu cho vay ngắn hạn
cackhoanphaithukhac|Các khoản phải thu khác
duphongphaithunganhankhodoi|Dự phòng phải thu ngắn hạn khó đòi
taisanthieuchoxuly|Tài sản thiếu chờ xử lý
hangtonkho_tong|Hàng tồn kho (tổng)
hangtonkho|Hàng tồn kho
duphonggiamgiahangtonkho|Dự phòng giảm giá hàng tồn kho
taisannganhankhac_tong|Tài sản ngắn hạn khác (tổng)
chiphitratruocnganhan|Chi phí trả trước ngắn hạn
thuegtgtduockhautru|Thuế GTGT được khấu trừ
thuevacackhoankhacphaithunhanuoc|Thuế và các khoản phải thu Nhà nước
giaodichmuabanlaitraiphieuchinhphu_tsnh|Giao dịch mua bán lại trái phiếu Chính phủ (tài sản)
taisannganhankhac|Tài sản ngắn hạn khác
taisandaihan|Tài sản dài hạn
cackhoanphaithudaihan|Các khoản phải thu dài hạn
phaithudaihancuakhachhang|Phải thu dài hạn của khách hàng
tratruocchonguoibandaihan|Trả trước cho người bán dài hạn
vonkinhdoanhodonvitructhuoc|Vốn kinh doanh ở đơn vị trực thuộc
phaithunoibodaihan|Phải thu nội bộ dài hạn
phaithuvechovaydaihan|Phải thu cho vay dài hạn
phaithudaihankhac|Phải thu dài hạn khác
duphongphaithukhodoi|Dự phòng phải thu khó đòi
taisancodinh|Tài sản cố định
taisancodinhhuuhinh|Tài sản cố định hữu hình
nguyengia_tscdhh|Nguyên giá TSCĐ hữu hình
giatrihaomonluyke_tscdhh|Hao mòn lũy kế TSCĐ hữu hình
taisancodinhthuetaichinh|Tài sản cố định thuê tài chính
nguyengia_tscdttc|Nguyên giá TSCĐ thuê tài chính
giatrihaomonluyke_tscdttc|Hao mòn lũy kế TSCĐ thuê tài chính
taisancodinhvohinh|Tài sản cố định vô hình
nguyengia_tscdvh|Nguyên giá TSCĐ vô hình
giatrihaomonluyke_tscdvh|Hao mòn lũy kế TSCĐ vô hình
batdongsandautu|Bất động sản đầu tư
nguyengia|Nguyên giá bất động sản đầu tư
giatrihaomonluyke|Hao mòn lũy kế bất động sản đầu tư
taisandodangdaihan|Tài sản dở dang dài hạn
chiphisanxuatkinhdoanhdodangdaihan|Chi phí sản xuất, kinh doanh dở dang dài hạn
chiphixaydungcobandodang|Chi phí xây dựng cơ bản dở dang
daututaichinhdaihan|Đầu tư tài chính dài hạn
dautuvaocongtycon|Đầu tư vào công ty con
dautuvaocongtylienketliendoanh|Đầu tư vào công ty liên kết, liên doanh
dautugopvonvaodonvikhac|Đầu tư góp vốn vào đơn vị khác
duphonggiamgiadautudaihan|Dự phòng giảm giá đầu tư dài hạn
dautunamgiudenngaydaohan_dttcdh|Đầu tư nắm giữ đến ngày đáo hạn — dài hạn
taisandaihankhac_tong|Tài sản dài hạn khác (tổng)
chiphitratruocdaihan|Chi phí trả trước dài hạn
taisanthuethunhaphoanlai|Tài sản thuế thu nhập hoãn lại
thietbivattuphutungthaythedaihan|Thiết bị, vật tư, phụ tùng thay thế dài hạn
loithethuongmai|Lợi thế thương mại
taisandaihankhac|Tài sản dài hạn khác
tongcongtaisan|Tổng cộng tài sản
nophaitra|Nợ phải trả
nonganhan|Nợ ngắn hạn
phaitranguoibannganhan|Phải trả người bán ngắn hạn
nguoimuatratientruocnganhan|Người mua trả tiền trước ngắn hạn
thuevacackhoanphainopnhanuoc|Thuế và các khoản phải nộp Nhà nước
phaitranguoilaodong|Phải trả người lao động
chiphiphaitranganhan|Chi phí phải trả ngắn hạn
phaitranoibonganhan|Phải trả nội bộ ngắn hạn
phaitratheotiendokehoachhopdongxaydung|Phải trả theo tiến độ hợp đồng xây dựng
doanhthuchuathuchiennganhan|Doanh thu chưa thực hiện ngắn hạn
phaitranganhankhac|Phải trả ngắn hạn khác
vayvanothuetaichinhnganhan|Vay và nợ thuê tài chính ngắn hạn
duphongphaitranganhan|Dự phòng phải trả ngắn hạn
quykhenthuongphucloi|Quỹ khen thưởng, phúc lợi
quybinhongia|Quỹ bình ổn giá
giaodichmuabanlaitraiphieuchinhphu_nnh|Giao dịch mua bán lại trái phiếu Chính phủ (nợ)
nodaihan|Nợ dài hạn
phaitradaihannguoiban|Phải trả người bán dài hạn
nguoimuatratientruocdaihan|Người mua trả tiền trước dài hạn
chiphiphaitradaihan|Chi phí phải trả dài hạn
phaitranoibovevonkinhdoanh|Phải trả nội bộ về vốn kinh doanh
phaitradaihannoibodaihan|Phải trả nội bộ dài hạn
doanhthuchuathuchiendaihan|Doanh thu chưa thực hiện dài hạn
phaitradaihankhac|Phải trả dài hạn khác
vayvanothuetaichinhdaihan|Vay và nợ thuê tài chính dài hạn
traiphieuchuyendoi|Trái phiếu chuyển đổi
cophieuuudai_no|Cổ phiếu ưu đãi (nợ phải trả)
thuethunhaphoanlaiphaitra|Thuế thu nhập hoãn lại phải trả
duphongphaitradaihan|Dự phòng phải trả dài hạn
quyphattrienkhoahocvacongnghe|Quỹ phát triển khoa học và công nghệ
vonchusohuu_tong|Vốn chủ sở hữu (tổng)
vonchusohuu|Vốn chủ sở hữu
vongopcuachusohuu|Vốn góp của chủ sở hữu
cophieuphothongcoquyenbieuquyet|Vốn cổ phiếu phổ thông có quyền biểu quyết
cophieuuudai|Vốn cổ phiếu ưu đãi
thangduvoncophan|Thặng dư vốn cổ phần
quyenchonchuyendoitraiphieu|Quyền chọn chuyển đổi trái phiếu
vonkhaccuachusohuu|Vốn khác của chủ sở hữu
cophieuquy|Cổ phiếu quỹ
chenhlechdanhgialaitaisan|Chênh lệch đánh giá lại tài sản
chenhlechtygiahoidoai|Chênh lệch tỷ giá hối đoái
quydautuphattrien|Quỹ đầu tư phát triển
quyhotrosapxepdoanhnghiep|Quỹ hỗ trợ sắp xếp doanh nghiệp
quykhacthuocvonchusohuu|Quỹ khác thuộc vốn chủ sở hữu
loinhuansauthuechuaphanphoi|Lợi nhuận sau thuế chưa phân phối
lnstchuaphanphoiluykedencuoikytruoc|LNST chưa phân phối lũy kế đến cuối kỳ trước
lnstchuaphanphoikynay|LNST chưa phân phối kỳ này
nguonvondautuxdcb|Nguồn vốn đầu tư xây dựng cơ bản
loiichcodongkhongkiemsoat|Lợi ích cổ đông không kiểm soát
nguonkinhphivacacquykhac|Nguồn kinh phí và các quỹ khác
nguonkinhphi|Nguồn kinh phí
nguonkinhphidahinhthanhtscd|Nguồn kinh phí đã hình thành TSCĐ
tongcongnguonvon|Tổng cộng nguồn vốn
luuchuyentientuhoatdongkinhdoanh|Lưu chuyển tiền từ hoạt động kinh doanh
loinhuanlotruocthue|Lợi nhuận/lỗ trước thuế
dieuchinhchocackhoan|Điều chỉnh cho các khoản
khauhaotaisancodinh|Khấu hao tài sản cố định
phanboloithethuongmai|Phân bổ lợi thế thương mại
cackhoanduphong|Các khoản dự phòng
lailochenhlechtygiahoidoaichuathuchien|Lãi/lỗ chênh lệch tỷ giá chưa thực hiện
lailothanhlytaisancodinh|Lãi/lỗ thanh lý tài sản cố định
lailotuhoatdongdaututhanhlytaisancodinh|Lãi/lỗ từ đầu tư, thanh lý tài sản cố định
lailotudautuvaocongtylienket|Lãi/lỗ đầu tư vào công ty liên kết
chiphilaivay|Chi phí lãi vay
thunhaptulaitiengui|Thu nhập từ lãi tiền gửi
loinhuanlotuhoatdongkinhdoanhtruocthaydoivonluudong|Lợi nhuận/lỗ kinh doanh trước thay đổi vốn lưu động
tanggiamcackhoanphaithu|Tăng/giảm các khoản phải thu
tanggiamhangtonkho|Tăng/giảm hàng tồn kho
tanggiamcackhoanphaitrakhonggomlaivaythuetndnphaitra|Tăng/giảm phải trả (không gồm lãi vay, thuế TNDN)
tanggiamchiphitratruoc|Tăng/giảm chi phí trả trước
tanggiamchungkhoantudoanh|Tăng/giảm chứng khoán tự doanh
tienlaivaydatra|Tiền lãi vay đã trả
thuethunhapdoanhnghiepdanop|Thuế thu nhập doanh nghiệp đã nộp
tienthukhactuhoatdongkinhdoanh|Tiền thu khác từ hoạt động kinh doanh
tienchikhacchohoatdongkinhdoanh|Tiền chi khác cho hoạt động kinh doanh
cackhoangiamtrukhac|Các khoản giảm trừ khác
luuchuyentienthuantuhoatdongkinhdoanh|Lưu chuyển tiền thuần từ hoạt động kinh doanh
luuchuyentientuhoatdongdautu|Lưu chuyển tiền từ hoạt động đầu tư
tienchidemuasamxaydungtaisancodinh|Tiền chi mua sắm, xây dựng TSCĐ
tienthudothanhlynhuongbantscdvacactaisandaihankhac|Tiền thu thanh lý, nhượng bán TSCĐ và tài sản dài hạn
tienchichovaymuacaccongcunocuadonvikhac|Tiền chi cho vay, mua công cụ nợ của đơn vị khác
tienthuhoichovaybanlaicongcunocuadonvikhac|Tiền thu hồi cho vay, bán lại công cụ nợ
tienchidautugopvonvaodonvikhac|Tiền chi đầu tư góp vốn vào đơn vị khác
tienthudobancackhoandautugopvonvaodonvikhac|Tiền thu bán các khoản đầu tư góp vốn
tienthulaichovaycotucvaloinhuanduocchia|Tiền thu lãi cho vay, cổ tức và lợi nhuận được chia
tienthu_chikhactuhddt|Tiền thu/chi khác từ hoạt động đầu tư
luuchuyentienthuantuhoatdongdautu|Lưu chuyển tiền thuần từ hoạt động đầu tư
luuchuyentientuhoatdongtaichinh|Lưu chuyển tiền từ hoạt động tài chính
tienthutuphathanhcophieunhangopvoncuachusohuu|Tiền thu phát hành cổ phiếu, nhận vốn góp
tienchitravongopchocshmualaicp|Tiền chi trả vốn góp, mua lại cổ phiếu
tienvaynganhandaihannhanduoc|Tiền thu từ đi vay ngắn hạn, dài hạn
tienchitranogocvay|Tiền chi trả nợ gốc vay
tienchitranothuetaichinh|Tiền chi trả nợ thuê tài chính
cotucloinhuandatrachochusohuu|Cổ tức, lợi nhuận đã trả cho chủ sở hữu
tienthu_chikhactuhdtc|Tiền thu/chi khác từ hoạt động tài chính
luuchuyentienthuantusudungvaohoatdongtaichinh|Lưu chuyển tiền thuần từ hoạt động tài chính
luuchuyentienthuantrongnam|Lưu chuyển tiền thuần trong kỳ
tienvatuongduongtiendaunam|Tiền và tương đương tiền đầu kỳ
anhhuongcuathaydoitygiahoidoaiquydoingoaite|Ảnh hưởng thay đổi tỷ giá khi quy đổi ngoại tệ
tienvatuongduongtiencuoinam|Tiền và tương đương tiền cuối kỳ
'''

LABELS = dict(line.split('|', 1) for line in _LABELS.strip().splitlines())

ORDER = list(LABELS)
BANK_ORDER = '''thunhaplaivacackhoanthunhaptuongtu chiphilaivacacchiphituongtu thunhaplaithuan
thunhaptuhoatdongdichvu chiphihoatdongdichvu laithuantuhoatdongdichvu
lailothuantuhoaydongkinhdoanhngoaihoivavang lailothuantumuabanchungkhoankinhdoanh
lailothuantumuabanchungkhoandautu thunhaptuhoatdongkhac chiphihoatdongkhac
lailothuantuhoatdongkhac thunhaptugopvonmuacophan tongthunhaphoatdong chiphihoatdong
loinhuanthuantuhdkdtruocchiphiduphongruirotindung chiphiduphongruirotindung tongloinhuantruocthue
chiphithuetndnhienhanh chiphithuetndnhoanlai chiphithuethunhapdoanhnghiep
loinhuansauthue loiichcuacodongthieuso_pl codongcuacongtyme'''.split()
SECURITIES_ORDER = ORDER[ORDER.index('doanhthuhoatdong'):ORDER.index('taisannganhan')]
SECURITIES_ORDER.insert(SECURITIES_ORDER.index('cphoatdong'), 'cackhoangiamtrudoanhthu')
SECURITIES_ORDER.remove('cpkhac')
SECURITIES_ORDER[SECURITIES_ORDER.index('lnkhac'):SECURITIES_ORDER.index('lnkhac')] = ['thunhapkhac', 'cpkhac']
SECURITIES_ORDER.insert(SECURITIES_ORDER.index('thunhapphaloangtrencophieu'), 'laicobantrencophieu')


def ordered_metrics(keys):
    preferred = BANK_ORDER if 'tongthunhaphoatdong' in keys else (SECURITIES_ORDER if 'lnsauthue' in keys else ORDER)
    return list(dict.fromkeys(k for k in [*preferred, *ORDER, *keys] if k in keys))


TOTALS = set('''doanhthuthuanvebanhangvacungcapdichvu loinhuangopvebanhangvacungcapdichvu
loinhuanthuantuhoatdongkinhdoanh tongloinhuanketoantruocthue loinhuansauthuethunhapdoanhnghiep
loinhuansauthuecuacongtyme tongthunhaphoatdong thunhaplaithuan tongloinhuantruocthue
loinhuansauthue codongcuacongtyme doanhthuhoatdong lngop ketquahoatdongkd tonglnketoantruocthue
lnsauthue lnsauthuecuachusohuu tongthunhaptoandien taisannganhan taisandaihan tongcongtaisan
nophaitra nonganhan nodaihan vonchusohuu_tong tongcongnguonvon
luuchuyentienthuantuhoatdongkinhdoanh luuchuyentienthuantuhoatdongdautu
luuchuyentienthuantusudungvaohoatdongtaichinh luuchuyentienthuantrongnam tienvatuongduongtiencuoinam'''.split())


def unit_for(key):
    if key in ('laicobantrencophieu', 'laisuygiamtrencophieu', 'thunhapphaloangtrencophieu'):
        return 'VND/cổ phiếu'
    if key.startswith(('soluongcophieu', 'khoiluongcophieu')):
        return 'cổ phiếu'
    if key.startswith(('tyle', 'tysuat')) or key.endswith('_ratio'):
        return '%'
    return 'VND'
