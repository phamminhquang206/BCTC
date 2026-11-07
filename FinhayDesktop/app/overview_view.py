"""Readable company profile, listing facts and industry comparison."""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QFileDialog,
)

from .exporting import export_rows
from .finance import number
from .activity_log import source_summary

GROUPS = {'get_stock_profile': 'profile', 'get_stock_listing': 'listing', 'get_company_overview': 'metrics'}
FIELD_LABELS = {
    'symbol': 'Mã cổ phiếu', 'name_vn': 'Tên doanh nghiệp', 'name_en': 'Tên tiếng Anh',
    'sector': 'Ngành nghề', 'about': 'Hoạt động kinh doanh', 'exchange': 'Sàn niêm yết',
    'listing_date': 'Ngày niêm yết', 'listing_reference_price': 'Giá tham chiếu ngày niêm yết',
    'listed_shares': 'Cổ phiếu niêm yết', 'outstanding_shares': 'Cổ phiếu lưu hành',
    'treasury_shares': 'Cổ phiếu quỹ', 'free_float': 'Cổ phiếu tự do chuyển nhượng',
    'free_float_pct': 'Tỷ lệ cổ phiếu tự do chuyển nhượng',
}
RATIOS = [
    ('pe', 'P/E', 'lần', 'Giá cổ phiếu so với lợi nhuận trên mỗi cổ phiếu.'),
    ('pb', 'P/B', 'lần', 'Giá cổ phiếu so với giá trị sổ sách trên mỗi cổ phiếu.'),
    ('ev_ebitda', 'EV/EBITDA', 'lần', 'Giá trị doanh nghiệp so với lợi nhuận trước lãi vay, thuế và khấu hao.'),
    ('eps', 'Lợi nhuận trên mỗi cổ phiếu (EPS)', 'VND/cổ phiếu', 'Lợi nhuận trên mỗi cổ phiếu do nguồn cung cấp.'),
    ('dividend_yield', 'Tỷ suất cổ tức', 'Theo nguồn', 'Tỷ suất cổ tức; giữ nguyên thang số của Finhay.'),
    ('gross_margin', 'Biên lợi nhuận gộp', 'Theo nguồn', 'Biên lợi nhuận gộp; giữ nguyên thang số của Finhay.'),
    ('roe', 'Lợi nhuận trên vốn chủ sở hữu (ROE)', 'Theo nguồn', 'Chỉ số ROE do nguồn cung cấp.'),
    ('roa', 'Lợi nhuận trên tổng tài sản (ROA)', 'Theo nguồn', 'Chỉ số ROA do nguồn cung cấp.'),
    ('nim', 'Biên lãi ròng (NIM)', 'Theo nguồn', 'Chỉ tiêu thường áp dụng cho ngân hàng.'),
    ('margin_loan_to_equity_ratio', 'Dư nợ ký quỹ / vốn chủ sở hữu', 'Theo nguồn', 'Chỉ tiêu thường áp dụng cho công ty chứng khoán.'),
]
RATIO_INFO = {key: (label, unit, help_text) for key, label, unit, help_text in RATIOS}


def overview_from_rows(rows):
    data = {'profile': {}, 'listing': {}, 'metrics': {}}
    for row in rows:
        group = GROUPS.get(row.get('nhom'))
        if group and row.get('chi_tieu'):
            data[group][row['chi_tieu']] = row.get('gia_tri')
    return data


def display_number(value, unit=''):
    value = number(value)
    if value is None:
        return 'Chưa có dữ liệu'
    if unit in ('cổ phiếu', 'VND', 'VND/cổ phiếu'):
        text = f'{value:,}' if isinstance(value, int) else f'{value:,.2f}'.rstrip('0').rstrip('.')
    else:
        text = f'{value:,.2f}'.rstrip('0').rstrip('.')
    return text


def sector_text(value):
    if isinstance(value, list):
        return ' › '.join(str(r['name']) for r in value if isinstance(r, dict) and r.get('name')) or 'Chưa có thông tin ngành'
    return str(value) if value else 'Chưa có thông tin ngành'


def label(text=''):
    widget = QLabel(text)
    widget.setTextFormat(Qt.PlainText)
    widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
    widget.setWordWrap(True)
    return widget


class OverviewView(QWidget):
    def __init__(self):
        super().__init__()
        self.data = {'profile': {}, 'listing': {}, 'metrics': {}}
        self.symbol = ''
        self.stamp = ''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(4, 4, 12, 8)
        body.setSpacing(14)
        self.company_name = label('Tổng quan doanh nghiệp')
        self.company_name.setStyleSheet('font-size:20px; font-weight:700; color:#172b4d;')
        self.company_meta = label('Nhập mã cổ phiếu và bấm Lấy dữ liệu để xem hồ sơ doanh nghiệp.')
        self.company_meta.setStyleSheet('color:#475569;')
        self.sector = label()
        self.sector.setStyleSheet('color:#475569;')
        for widget in (self.company_name, self.company_meta, self.sector):
            body.addWidget(widget)
        cards = QGridLayout()
        self.card_values, self.card_units = {}, {}
        for i, (key, title, unit) in enumerate((('pe', 'P/E', 'lần'), ('pb', 'P/B', 'lần'), ('eps', 'EPS', 'VND/cổ phiếu'), ('outstanding_shares', 'Cổ phiếu lưu hành', 'cổ phiếu'))):
            card = QFrame()
            card.setStyleSheet('QFrame { background:#ffffff; border:1px solid #cbd5e1; border-radius:7px; } QLabel { border:0; background:transparent; }')
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            title_label = label(title)
            title_label.setStyleSheet('font-weight:600; color:#475569;')
            value = label('Chưa có dữ liệu')
            value.setStyleSheet('font-size:19px; font-weight:700; color:#172b4d;')
            unit_label = label(unit)
            unit_label.setStyleSheet('color:#475569; font-size:12px;')
            for widget in (title_label, value, unit_label):
                card_layout.addWidget(widget)
            self.card_values[key], self.card_units[key] = value, unit
            cards.addWidget(card, 0, i)
            cards.setColumnStretch(i, 1)
        body.addLayout(cards)
        business = QGroupBox('Hoạt động kinh doanh')
        business_layout = QVBoxLayout(business)
        self.about = label('Chưa có thông tin giới thiệu.')
        business_layout.addWidget(self.about)
        body.addWidget(business)
        listing = QGroupBox('Thông tin niêm yết')
        listing_layout = QGridLayout(listing)
        self.listing_values = {}
        fields = ['exchange', 'listing_date', 'listing_reference_price', 'listed_shares', 'outstanding_shares', 'treasury_shares', 'free_float', 'free_float_pct']
        for i, key in enumerate(fields):
            row, column = i // 2, (i % 2) * 2
            caption = label(FIELD_LABELS[key])
            caption.setStyleSheet('color:#475569;')
            value = label('Chưa có dữ liệu')
            value.setStyleSheet('font-weight:600; color:#172b4d;')
            listing_layout.addWidget(caption, row, column)
            listing_layout.addWidget(value, row, column + 1)
            self.listing_values[key] = value
        listing_layout.setColumnStretch(1, 1)
        listing_layout.setColumnStretch(3, 1)
        listing_layout.setHorizontalSpacing(20)
        listing_layout.setVerticalSpacing(10)
        body.addWidget(listing)
        metrics = QGroupBox('Chỉ số tài chính và so sánh ngành')
        metrics_layout = QVBoxLayout(metrics)
        self.ratios = QTableWidget(0, 4)
        self.ratios.setHorizontalHeaderLabels(['Chỉ số', 'Doanh nghiệp', 'Trung bình ngành', 'Đơn vị'])
        self.ratios.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ratios.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ratios.setAlternatingRowColors(True)
        self.ratios.verticalHeader().hide()
        self.ratios.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            self.ratios.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.ratios.setMinimumHeight(120)
        metrics_layout.addWidget(self.ratios)
        self.metrics_note = label('Finhay chưa cung cấp chỉ số cho lựa chọn này.')
        self.metrics_note.setStyleSheet('color:#475569;')
        metrics_layout.addWidget(self.metrics_note)
        body.addWidget(metrics)
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        bottom = QHBoxLayout()
        self.source = label('Nguồn: Finhay')
        self.source.setWordWrap(False)
        self.source.setStyleSheet('color:#475569; font-size:12px;')
        export = QPushButton('Xuất tổng quan Excel/CSV')
        export.clicked.connect(self.export)
        bottom.addWidget(self.source, 1)
        bottom.addWidget(export)
        layout.addLayout(bottom)

    def set_overview(self, data, symbol, stamp=''):
        self.data = {group: dict(data.get(group) or {}) for group in ('profile', 'listing', 'metrics')}
        self.symbol, self.stamp = symbol, stamp
        profile, listing, metrics = (self.data[key] for key in ('profile', 'listing', 'metrics'))
        self.company_name.setText(profile.get('name_vn') or symbol or 'Tổng quan doanh nghiệp')
        self.company_meta.setText(' · '.join(str(v) for v in (symbol, listing.get('exchange'), profile.get('name_en')) if v))
        self.sector.setText('Ngành: ' + sector_text(profile.get('sector')))
        self.about.setText(profile.get('about') or 'Finhay chưa cung cấp phần giới thiệu hoạt động kinh doanh.')
        for key, widget in self.card_values.items():
            widget.setText(display_number(listing.get(key) if key == 'outstanding_shares' else metrics.get(key), self.card_units[key]))
        for key, widget in self.listing_values.items():
            value = listing.get(key)
            if key == 'listing_date':
                try:
                    value = datetime.strptime(str(value), '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    value = str(value) if value else 'Chưa có dữ liệu'
            elif key == 'listing_reference_price':
                value = display_number(value, 'VND') + (' VND' if number(value) is not None else '')
            elif key not in ('exchange',):
                unit = '%' if key == 'free_float_pct' else 'cổ phiếu'
                value = display_number(value, unit) + (f' {unit}' if number(value) is not None else '')
            widget.setText(str(value) if value not in (None, '') else 'Chưa có dữ liệu')
        industry = metrics.get('industry') if isinstance(metrics.get('industry'), dict) else {}
        entries = [(key, title, unit, help_text) for key, title, unit, help_text in RATIOS if number(metrics.get(key)) is not None or number(industry.get(key)) is not None]
        self.ratios.setRowCount(len(entries))
        for row, (key, title, unit, help_text) in enumerate(entries):
            for column, text in enumerate((title, display_number(metrics.get(key), unit), display_number(industry.get(key), unit), unit)):
                item = QTableWidgetItem(text)
                item.setToolTip(help_text)
                item.setTextAlignment((Qt.AlignLeft if column in (0, 3) else Qt.AlignRight) | Qt.AlignVCenter)
                self.ratios.setItem(row, column, item)
        self.ratios.setFixedHeight(max(104, self.ratios.horizontalHeader().height() + len(entries) * 32 + 4))
        self.metrics_note.setText('“Chưa có dữ liệu” nghĩa là nguồn chưa trả giá trị; không được xem là 0. Các chỉ tiêu có đơn vị “Theo nguồn” giữ nguyên thang số, không tự nhân 100.' if entries else 'Finhay chưa cung cấp chỉ số cho mã này. Các thông tin hồ sơ và niêm yết vẫn được hiển thị phía trên.')
        self.source.setText(source_summary(stamp))
        self.source.setToolTip('Thời điểm lấy từng nhóm dữ liệu (dòng chính hiển thị thời điểm lấy mới nhất theo giờ Việt Nam):\n' + stamp)

    def export_data(self):
        rows = []
        for group, name in (('profile', 'Hồ sơ doanh nghiệp'), ('listing', 'Thông tin niêm yết'), ('metrics', 'Chỉ số tài chính')):
            for key, value in self.data[group].items():
                if key == 'industry' and isinstance(value, dict):
                    for field, val in value.items():
                        title, unit, _ = RATIO_INFO.get(field, (field, '', ''))
                        rows.append({'Nhóm': 'Trung bình ngành', 'Chỉ tiêu': title, 'Giá trị': val, 'Đơn vị': unit})
                    continue
                title, unit, _ = RATIO_INFO.get(key, (FIELD_LABELS.get(key, key), '', ''))
                if key == 'sector':
                    value = sector_text(value)
                rows.append({'Nhóm': name, 'Chỉ tiêu': title, 'Giá trị': value, 'Đơn vị': unit})
        return rows

    def export(self):
        rows = self.export_data()
        if not rows:
            QMessageBox.information(self, 'Xuất tổng quan', 'Chưa có dữ liệu để xuất.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Xuất tổng quan doanh nghiệp', f'{self.symbol or "doanh-nghiep"}-tong-quan.xlsx', 'Excel (*.xlsx);;CSV UTF-8 (*.csv)')
        if path:
            try:
                export_rows(path, rows, {'ma': self.symbol, 'nguon': 'Finhay MCP', 'lay_du_lieu_luc': self.stamp})
                QMessageBox.information(self, 'Đã xuất', 'Đã lưu tổng quan doanh nghiệp.')
            except Exception as exc:
                QMessageBox.warning(self, 'Không lưu được', f'Kiểm tra quyền ghi và đóng file đang mở. ({type(exc).__name__})')
