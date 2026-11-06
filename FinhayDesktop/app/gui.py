import json
import math
import re
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QDate, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QCompleter, QDateEdit, QFileDialog,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QSplitter, QTabWidget,
    QTableView, QTextEdit, QVBoxLayout, QWidget, QTabBar,
)

from .auth import REDIRECT, Vault
from .engine import Worker
from .exporting import export_rows
from .storage import Store
from .financial_view import FinancialView

LABELS = {
    'symbol': 'Mã', 'name': 'Doanh nghiệp', 'exchange': 'Sàn', 'year': 'Năm', 'quarter': 'Quý',
    'revenue_label': 'Chỉ tiêu doanh thu', 'revenue': 'Doanh thu', 'profit': 'LNST',
    'parent_profit': 'LNST công ty mẹ', 'status': 'Trạng thái', 'message': 'Ghi chú',
    'period_basis': 'Cơ sở kỳ', 'report_scope': 'Loại báo cáo', 'fetched_at': 'Thời điểm lấy',
    'source': 'Nguồn', 'currency': 'Tiền tệ', 'kind': 'Mẫu báo cáo', 'cache_policy': 'Chế độ dữ liệu',
    'nhom': 'Nhóm', 'chi_tieu': 'Chỉ tiêu', 'gia_tri': 'Giá trị',
    't': 'Thời điểm (Unix giây)', 'o': 'Mở cửa', 'h': 'Cao nhất', 'l': 'Thấp nhất', 'c': 'Đóng cửa', 'v': 'Khối lượng',
    '_symbol': 'Mã', '_fetched_at': 'Thời điểm lấy từ Finhay', '_source': 'Nguồn', '_cached': 'Dùng dữ liệu đã lưu',
    'processed_at': 'Thời điểm xử lý',
    'doanhthuthuanvebanhangvacungcapdichvu': 'Doanh thu thuần',
    'doanhthubanhangvacungcapdichvu': 'Doanh thu bán hàng và cung cấp dịch vụ',
    'giavonhangban': 'Giá vốn hàng bán', 'loinhuangopvebanhangvacungcapdichvu': 'Lợi nhuận gộp',
    'doanhthuhoatdongtaichinh': 'Doanh thu tài chính', 'chiphitaichinh': 'Chi phí tài chính',
    'chiphibanhang': 'Chi phí bán hàng', 'chiphiquanlydoanhnghiep': 'Chi phí quản lý',
    'loinhuanthuantuhoatdongkinhdoanh': 'Lợi nhuận thuần hoạt động kinh doanh',
    'tongloinhuanketoantruocthue': 'Lợi nhuận trước thuế',
    'loinhuansauthuethunhapdoanhnghiep': 'LNST', 'loinhuansauthuecuacongtyme': 'LNST công ty mẹ',
    'tongthunhaphoatdong': 'Tổng thu nhập hoạt động', 'thunhaplaithuan': 'Thu nhập lãi thuần',
    'loinhuansauthue': 'LNST', 'codongcuacongtyme': 'LNST công ty mẹ',
    'doanhthuhoatdong': 'Doanh thu hoạt động', 'lnsauthue': 'LNST', 'lnsauthuecuachusohuu': 'LNST chủ sở hữu',
}
for metric, label in [('revenue', 'DT'), ('profit', 'LNST'), ('parent_profit', 'LNST mẹ')]:
    for basis, blabel in [('yoy', 'cùng kỳ'), ('qoq', 'quý trước')]:
        for field, flabel in [('delta', 'Chênh lệch'), ('percent', '%'), ('state', 'Diễn giải')]:
            LABELS[f'{metric}_{basis}_{field}'] = f'{flabel} {label} / {blabel}'

STATUS = {'ok': 'Thành công', 'missing': 'Thiếu / cần xác minh', 'error': 'Lỗi', 'pending': 'Chưa chạy'}


class TableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.rows, self.keys, self.money = [], [], set()

    def set_rows(self, rows, money=None):
        self.beginResetModel()
        self.rows = rows
        priority = ['symbol', 'name', 'exchange', 'year', 'quarter', 'status', 'revenue_label', 'revenue', 'profit', 'parent_profit']
        keys = list(dict.fromkeys(k for row in rows for k in row))
        self.keys = [k for k in priority if k in keys] + [k for k in keys if k not in priority]
        self.money = set(money or [])
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.keys)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                key = self.keys[section]
                return LABELS.get(key, key) + (' (tỷ VND)' if key in self.money else '')
            return section + 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        key = self.keys[index.column()]
        value = self.rows[index.row()].get(key)
        if role == Qt.UserRole:
            return value if isinstance(value, (int, float, str)) else ''
        if role == Qt.DisplayRole:
            if value is None:
                return '—'
            if key == 'status':
                return STATUS.get(value, value)
            if key == 'period_basis':
                return {'unknown': 'Chưa xác minh', 'standalone': 'Quý riêng (đã chọn)', 'cumulative': 'Lũy kế (đã chọn)', 'annual': 'Cả năm'}.get(value, value)
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            if isinstance(value, (int, float)):
                if key in ('year', 'quarter'):
                    return str(value)
                if key in self.money:
                    return f'{value / 1_000_000_000:,.3f}'
                if key.endswith('_percent'):
                    return f'{value:,.2f}%'
                return f'{value:,}'
            return str(value)
        if role == Qt.ToolTipRole:
            return f'{key}: {value}'
        if role == Qt.TextAlignmentRole and isinstance(value, (int, float)):
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ForegroundRole and key == 'status':
            return QColor({'ok': '#15803d', 'missing': '#a16207', 'error': '#dc2626'}.get(value, '#475569'))


class FilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.query, self.status = '', ''
        self.setSortRole(Qt.UserRole)

    def filterAcceptsRow(self, source_row, parent):
        row = self.sourceModel().rows[source_row]
        return (not self.status or row.get('status') == self.status) and self.query.casefold() in json.dumps(row, ensure_ascii=False).casefold()

    def lessThan(self, left, right):
        a = self.sourceModel().data(left, Qt.UserRole)
        b = self.sourceModel().data(right, Qt.UserRole)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a < b
        return str(a).casefold() < str(b).casefold()


class DataTable(QWidget):
    def __init__(self, scan=False):
        super().__init__()
        self.model = TableModel()
        self.proxy = FilterProxy()
        self.proxy.setSourceModel(self.model)
        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.proxy.sort(0, Qt.AscendingOrder)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.view.horizontalHeader().setDefaultSectionSize(160)
        self.view.verticalHeader().setDefaultSectionSize(30)
        self.query = QLineEdit()
        self.query.setPlaceholderText('Lọc bảng theo mã, tên hoặc nội dung…')
        self.query.textChanged.connect(self.filter_changed)
        self.status = QComboBox()
        self.status.addItem('Mọi trạng thái', '')
        if scan:
            for key, value in STATUS.items():
                self.status.addItem(value, key)
        self.status.currentIndexChanged.connect(self.filter_changed)
        self.status.setVisible(scan)
        export = QPushButton('Xuất bảng đang lọc')
        export.clicked.connect(lambda: self.export(True))
        export_all = QPushButton('Xuất toàn bộ')
        export_all.clicked.connect(lambda: self.export(False))
        bar = QHBoxLayout()
        for w in (self.query, self.status, export, export_all):
            bar.addWidget(w)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self.view)

    def filter_changed(self):
        self.proxy.beginFilterChange()
        self.proxy.query = self.query.text().strip()
        self.proxy.status = self.status.currentData()
        self.proxy.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def rows(self, filtered):
        if not filtered:
            return self.model.rows
        return [self.model.rows[self.proxy.mapToSource(self.proxy.index(i, 0)).row()] for i in range(self.proxy.rowCount())]

    def export(self, filtered):
        rows = self.rows(filtered)
        if not rows:
            QMessageBox.information(self, 'Xuất dữ liệu', 'Chưa có dữ liệu để xuất.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Lưu dữ liệu — giá trị tiền ở đơn vị gốc VND', 'finhay.xlsx', 'Excel (*.xlsx);;CSV UTF-8 (*.csv)')
        if path:
            try:
                export_rows(path, rows, {'thoi_diem_xuat': datetime.now().astimezone().isoformat(), 'bang': 'đang lọc' if filtered else 'toàn bộ'})
                QMessageBox.information(self, 'Đã xuất', 'Đã lưu file. Các giá trị tiền giữ đơn vị gốc; xem currency/unit nếu nguồn cung cấp.')
            except Exception as exc:
                QMessageBox.warning(self, 'Không lưu được', f'Kiểm tra quyền ghi và đóng file Excel đang mở. ({type(exc).__name__})')


class PriceChart(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.setMinimumHeight(190)

    def set_rows(self, rows):
        self.points = sorted([(r['t'], r['c']) for r in rows if isinstance(r.get('t'), (int, float)) and isinstance(r.get('c'), (int, float)) and math.isfinite(r['c'])])
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#f0f9ff'))
        p.setPen(QColor('#475569'))
        if len(self.points) < 2:
            p.drawText(self.rect(), Qt.AlignCenter, 'Biểu đồ giá đóng cửa • chưa có đủ dữ liệu')
            return
        left, top, width, height = 85, 26, self.width() - 110, self.height() - 60
        low, high = min(v for _, v in self.points), max(v for _, v in self.points)
        p.drawText(8, top + 8, f'{high:,.0f}')
        p.drawText(8, top + height, f'{low:,.0f}')
        p.drawText(left, self.height() - 10, datetime.fromtimestamp(self.points[0][0], timezone(timedelta(hours=7))).strftime('%d/%m/%Y'))
        p.drawText(max(left, self.width() - 110), self.height() - 10, datetime.fromtimestamp(self.points[-1][0], timezone(timedelta(hours=7))).strftime('%d/%m/%Y'))
        p.setPen(QPen(QColor('#0284c7'), 2))
        coords = [(left + i * width / (len(self.points) - 1), top + height - (v - low) / (high - low or 1) * height) for i, (_, v) in enumerate(self.points)]
        for a, b in zip(coords, coords[1:]):
            p.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))


def spin(low, high, value):
    widget = QSpinBox()
    widget.setRange(low, high)
    widget.setValue(value)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, data_dir):
        super().__init__()
        self.setWindowTitle('Finhay Desktop • Dữ liệu chứng khoán')
        self.resize(1360, 900)
        self.store = Store(Path(data_dir) / 'finhay.sqlite3')
        self.worker = None
        self.current_run = None
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 16)
        header = QHBoxLayout()
        title = QLabel('FINHAY  /  DATA DESK')
        title.setStyleSheet('font-size:22px; font-weight:700; color:#0c4a6e;')
        self.connection = QLabel('Chưa kiểm tra kết nối')
        self.connect_btn = QPushButton('Kết nối Finhay')
        self.connect_btn.clicked.connect(lambda: self.launch('connect'))
        self.disconnect_btn = QPushButton('Ngắt kết nối')
        self.disconnect_btn.clicked.connect(self.disconnect)
        header.addWidget(title)
        header.addStretch()
        for widget in (self.connection, self.connect_btn, self.disconnect_btn):
            header.addWidget(widget)
        layout.addLayout(header)
        subtitle = QLabel('Tra cứu cổ phiếu và quét kết quả kinh doanh • Dữ liệu Finhay MCP • Chỉ đọc')
        subtitle.setStyleSheet('color:#64748b; margin-bottom:8px;')
        layout.addWidget(subtitle)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.make_lookup()
        self.make_scan()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(90)
        self.log.setPlaceholderText('Trạng thái xử lý sẽ xuất hiện tại đây…')
        layout.addWidget(self.log)
        self.statusBar().showMessage(f'Dữ liệu: {data_dir} | Callback: {REDIRECT}')
        self.reload_runs()

    def make_lookup(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        bar = QHBoxLayout()
        self.symbol = QLineEdit('FPT')
        self.symbol.setMaximumWidth(350)
        self.symbol.setPlaceholderText('Nhập mã hoặc tìm tên doanh nghiệp')
        catalog_btn = QPushButton('Tải danh sách mã')
        catalog_btn.clicked.connect(lambda: self.launch('catalog'))
        self.refresh_lookup = QCheckBox('Lấy mới từ Finhay')
        self.refresh_lookup.setChecked(True)
        for w in (QLabel('Cổ phiếu'), self.symbol, catalog_btn, self.refresh_lookup):
            bar.addWidget(w)
        bar.addStretch()
        layout.addLayout(bar)
        self.sections = QTabWidget()
        self.lookup_tables = {}
        self.lookup_buttons = []
        for key, title in [('overview', 'Tổng quan'), ('financial', 'Báo cáo tài chính'), ('price', 'Giá cổ phiếu'), ('events', 'Cổ tức và quyền')]:
            page = QWidget()
            box = QVBoxLayout(page)
            options = QHBoxLayout()
            if key == 'financial':
                self.report = QComboBox(page)
                self.report.hide()
                self.report_tabs = QTabBar()
                self.report_tabs.setExpanding(False)
                self.report_tabs.setDrawBase(False)
                for label, val in [('Kết quả kinh doanh', 'income-statement'), ('Cân đối kế toán', 'balance-sheet'), ('Lưu chuyển tiền tệ', 'cash-flow')]:
                    self.report.addItem(label, val)
                    self.report_tabs.addTab(label)
                self.report_tabs.currentChanged.connect(self.report.setCurrentIndex)
                self.report.currentIndexChanged.connect(self.report_tabs.setCurrentIndex)
                box.addWidget(self.report_tabs)
                self.period = QComboBox()
                self.period.addItem('Theo quý', 'quarterly')
                self.period.addItem('Theo năm', 'annual')
                year = datetime.now().year
                self.from_year, self.to_year = spin(1990, 2100, year - 2), spin(1990, 2100, year)
                for w in (self.period, QLabel('Từ năm'), self.from_year, QLabel('Đến năm'), self.to_year):
                    options.addWidget(w)
                self.lookup_buttons.extend((self.report_tabs, self.period, self.from_year, self.to_year))
            if key == 'price':
                self.from_date, self.to_date = QDateEdit(QDate.currentDate().addMonths(-6)), QDateEdit(QDate.currentDate())
                for w in (self.from_date, self.to_date):
                    w.setCalendarPopup(True)
                    w.setDisplayFormat('dd/MM/yyyy')
                for w in (QLabel('Từ'), self.from_date, QLabel('Đến'), self.to_date):
                    options.addWidget(w)
            button = QPushButton('Lấy dữ liệu')
            button.clicked.connect(lambda checked=False, section=key: self.lookup(section))
            self.lookup_buttons.append(button)
            options.addWidget(button)
            options.addStretch()
            box.addLayout(options)
            if key == 'price':
                self.quote_label = QLabel('Giá hiện tại và biểu đồ lịch sử đóng cửa (VND)')
                self.quote_label.setWordWrap(True)
                box.addWidget(self.quote_label)
                self.chart = PriceChart()
                box.addWidget(self.chart)
            table = FinancialView() if key == 'financial' else DataTable()
            if key == 'financial':
                self.report.currentIndexChanged.connect(lambda: self.lookup_tables['financial'].set_records([]))
                self.period.currentIndexChanged.connect(lambda: self.lookup_tables['financial'].set_records([]))
            self.lookup_tables[key] = table
            box.addWidget(table)
            self.sections.addTab(page, title)
        layout.addWidget(self.sections)
        self.tabs.addTab(tab, 'Tra cứu cổ phiếu')

    def make_scan(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        grid = QGridLayout()
        self.scan_symbols = QLineEdit()
        self.scan_symbols.setPlaceholderText('Để trống = toàn thị trường; hoặc nhập FPT, VCB, SSI…')
        self.exchange = QComboBox()
        for label, val in [('HOSE + HNX + UPCoM', ''), ('HOSE', 'HOSE'), ('HNX', 'HNX'), ('UPCoM', 'UPCOM')]:
            self.exchange.addItem(label, val)
        self.scan_period = QComboBox()
        self.scan_period.addItem('Theo quý', 'quarterly')
        self.scan_period.addItem('Theo năm', 'annual')
        self.scan_year = spin(1990, 2100, datetime.now().year)
        self.scan_quarter = spin(1, 4, max(1, (datetime.now().month - 1) // 3))
        self.scan_period.currentIndexChanged.connect(lambda: self.scan_quarter.setEnabled(self.scan_period.currentData() == 'quarterly'))
        self.basis = QComboBox()
        self.basis.addItem('Chưa xác minh quý riêng / lũy kế', 'unknown')
        self.basis.addItem('Đã kiểm chứng: số liệu quý riêng', 'standalone')
        self.basis.addItem('Đã kiểm chứng: số liệu lũy kế từ đầu năm', 'cumulative')
        self.basis.setToolTip('Chỉ chọn đã kiểm chứng khi bạn có bằng chứng cho các mã/kỳ trong lượt quét. App không tự suy ra cơ sở kỳ từ tên quý.')
        self.refresh_scan = QCheckBox('Lấy mới (cập nhật cả kỳ so sánh)')
        self.refresh_scan.setChecked(True)
        grid.addWidget(QLabel('Danh sách mã'), 0, 0)
        grid.addWidget(self.scan_symbols, 0, 1, 1, 5)
        for col, w in enumerate((self.exchange, self.scan_period, QLabel('Năm'), self.scan_year, QLabel('Quý'), self.scan_quarter)):
            grid.addWidget(w, 1, col)
        grid.addWidget(self.basis, 2, 0, 1, 4)
        grid.addWidget(self.refresh_scan, 2, 4, 1, 2)
        layout.addLayout(grid)
        note = QLabel('Quý: so cùng kỳ và quý trước. Năm: so năm trước. Chưa xác minh cơ sở quý → chỉ hiển thị số nguồn, không tính tăng trưởng. Xuất file giữ VND gốc.')
        note.setWordWrap(True)
        layout.addWidget(note)
        bar = QHBoxLayout()
        self.start_scan = QPushButton('Chạy lượt quét mới')
        self.start_scan.clicked.connect(self.new_scan)
        self.pause_btn = QPushButton('Tạm dừng / Hủy chờ')
        self.pause_btn.clicked.connect(self.pause)
        self.pause_btn.setEnabled(False)
        self.runs_box = QComboBox()
        self.runs_box.setMinimumWidth(240)
        self.runs_box.currentIndexChanged.connect(self.load_run)
        self.resume_btn = QPushButton('Tiếp tục')
        self.resume_btn.clicked.connect(self.resume)
        self.retry_btn = QPushButton('Chạy lại mã lỗi')
        self.retry_btn.clicked.connect(self.retry)
        for w in (self.start_scan, self.pause_btn, self.runs_box, self.resume_btn, self.retry_btn):
            bar.addWidget(w)
        layout.addLayout(bar)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.counts = QLabel('Chưa có lượt quét')
        layout.addWidget(self.counts)
        self.scan_table = DataTable(scan=True)
        layout.addWidget(self.scan_table)
        self.tabs.addTab(tab, 'Quét kết quả kinh doanh')

    def busy(self, value):
        for w in (self.connect_btn, self.disconnect_btn, self.start_scan, self.resume_btn, self.retry_btn, self.runs_box, *self.lookup_buttons):
            w.setEnabled(not value)
        self.pause_btn.setEnabled(value)

    def launch(self, action, config=None):
        if self.worker is not None:
            self.log.append('Đang có tác vụ chạy. Chờ hoàn tất hoặc bấm tạm dừng.')
            return
        self.busy(True)
        self.worker = Worker(self.store, action, config)
        self.worker.message.connect(self.log.append)
        self.worker.failed.connect(self.on_error)
        self.worker.result.connect(lambda result: self.on_result(action, result))
        self.worker.row_ready.connect(lambda row: self.load_run())
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.worker_finished)
        self.log.append('Bắt đầu: ' + {'connect': 'kết nối Finhay', 'lookup': 'tra cứu', 'catalog': 'tải danh sách mã', 'scan': 'quét kết quả kinh doanh'}[action])
        self.worker.start()

    def worker_finished(self):
        worker = self.worker
        self.worker = None
        self.busy(False)
        if worker:
            worker.deleteLater()
        self.log.append('Tác vụ đã dừng/kết thúc. Dữ liệu nhận được đã lưu trên máy.')

    def on_error(self, message):
        self.connection.setText('Cần kiểm tra kết nối nếu lỗi xác thực')
        self.log.append(message)
        QMessageBox.warning(self, 'Không hoàn tất tác vụ', message + '\n\nNếu lỗi đăng ký OAuth: Finhay cần cho phép public desktop client, scope read:market, redirect ' + REDIRECT + '. Không dán token/mật khẩu vào app.')

    def on_result(self, action, result):
        if action == 'connect':
            self.connection.setText('Đã kết nối Finhay')
            self.log.append(f'Kết nối thành công: {len(result["tools"])} công cụ; báo cáo thử FPT: {result["probe_rows"]} kỳ.')
        elif action == 'catalog':
            names = [f'{r["symbol"]} — {r.get("name", "")}' for r in result['rows'] if r.get('symbol')]
            completer = QCompleter(names, self.symbol)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            self.symbol.setCompleter(completer)
            self.log.append(f'Đã nạp {len(names)} mã để tìm kiếm.')
        elif action == 'lookup':
            section, rows = result['section'], result['rows']
            # Exported rows carry provenance and original units.
            rows = [dict(r, _symbol=result['symbol'], _fetched_at=r.get('_fetched_at') or result['stamp'], _source='Finhay MCP') for r in rows]
            if section == 'financial':
                config = result.get('config', {})
                self.lookup_tables[section].set_records(rows, {'symbol': result['symbol'],
                    'report': config.get('report', self.report.currentData()), 'period': config.get('period', self.period.currentData()),
                    'from_year': config.get('from_year'), 'to_year': config.get('to_year'), 'source': 'Finhay MCP'})
            else:
                self.lookup_tables[section].model.set_rows(rows)
                self.lookup_tables[section].view.resizeColumnsToContents()
            if section == 'price':
                quote = result.get('quote', {})
                self.quote_label.setText(f'{result["symbol"]} • Giá: {quote.get("price", "—")} VND • Thay đổi: {quote.get("change_percent", "—")}% • Nguồn cập nhật: {quote.get("updated_at", "không rõ")}')
                self.chart.set_rows(rows)
            self.log.append(f'{result["symbol"]}: {len(rows)} dòng. {result["stamp"]}')
        elif action == 'scan':
            self.current_run = result['run_id']
            self.reload_runs(self.current_run)
            if result.get('finished'):
                self.log.append('Lượt quét đã tạm dừng.' if result.get('paused') else 'Đã xử lý hết các mã đang chờ.')

    def lookup(self, section):
        symbol = self.symbol.text().split('—')[0].strip().upper()
        if not re.fullmatch('[A-Z0-9]{3,10}', symbol):
            QMessageBox.warning(self, 'Mã cổ phiếu', 'Nhập mã hợp lệ, ví dụ FPT hoặc VCB.')
            return
        if self.from_year.value() > self.to_year.value() or self.from_date.date() > self.to_date.date():
            QMessageBox.warning(self, 'Khoảng thời gian', 'Thời điểm bắt đầu phải trước hoặc bằng thời điểm kết thúc.')
            return
        vn = timezone(timedelta(hours=7))
        config = dict(symbol=symbol, section=section, refresh=self.refresh_lookup.isChecked(),
            report=self.report.currentData(), period=self.period.currentData(), from_year=self.from_year.value(), to_year=self.to_year.value(),
            from_ts=int(datetime.combine(self.from_date.date().toPython(), time.min, vn).timestamp()),
            to_ts=int(datetime.combine(self.to_date.date().toPython(), time.max, vn).timestamp()))
        self.launch('lookup', config)

    def new_scan(self):
        symbols = [s for s in re.split(r'[\s,;]+', self.scan_symbols.text().strip().upper()) if s]
        if any(not re.fullmatch('[A-Z0-9]{3,10}', s) for s in symbols):
            QMessageBox.warning(self, 'Danh sách mã', 'Các mã cần cách nhau bằng dấu phẩy, dấu chấm phẩy hoặc khoảng trắng.')
            return
        self.launch('scan', dict(symbols=list(dict.fromkeys(symbols)), exchange=self.exchange.currentData(),
            period=self.scan_period.currentData(), year=self.scan_year.value(),
            quarter=self.scan_quarter.value() if self.scan_period.currentData() == 'quarterly' else None,
            basis=self.basis.currentData(), refresh=self.refresh_scan.isChecked()))

    def reload_runs(self, select=None):
        selected = select or self.runs_box.currentData()
        self.runs_box.blockSignals(True)
        self.runs_box.clear()
        for row in self.store.runs():
            c = json.loads(row['config'])
            label = f'#{row["id"]} • {c["year"]}' + (f' Q{c["quarter"]}' if c.get('quarter') else ' năm')
            self.runs_box.addItem(label, row['id'])
        index = self.runs_box.findData(selected)
        if index >= 0:
            self.runs_box.setCurrentIndex(index)
        self.runs_box.blockSignals(False)
        self.load_run()

    def load_run(self, *_):
        self.current_run = self.runs_box.currentData()
        if not self.current_run:
            return
        jobs = self.store.jobs(self.current_run)
        rows = [json.loads(j['result']) if j['result'] else {'symbol': j['symbol'], 'status': j['status']} for j in jobs]
        money = {'revenue', 'profit', 'parent_profit'} | {k for row in rows for k in row if k.endswith('_delta')}
        self.scan_table.model.set_rows(rows, money)
        widths = {'symbol': 65, 'name': 215, 'exchange': 65, 'year': 55, 'quarter': 45,
                  'status': 165, 'revenue_label': 180, 'revenue': 135, 'profit': 130, 'parent_profit': 155}
        for key, width in widths.items():
            if key in self.scan_table.model.keys:
                self.scan_table.view.setColumnWidth(self.scan_table.model.keys.index(key), width)
        counts = {key: sum(j['status'] == key for j in jobs) for key in STATUS}
        config = self.store.config(self.current_run)
        basis_label = {'unknown': 'chưa xác minh', 'standalone': 'quý riêng', 'cumulative': 'lũy kế'}.get(config['basis'], config['basis'])
        self.counts.setText(' | '.join(f'{STATUS[key]}: {val}' for key, val in counts.items()) + f' • Cơ sở quý: {basis_label}')
        self.update_progress(len(jobs) - counts['pending'], len(jobs))

    def update_progress(self, done, total):
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(done)
        self.progress.setFormat(f'{done}/{total} mã')

    def resume(self):
        if self.current_run:
            self.launch('scan', {'run_id': self.current_run})

    def retry(self):
        if self.current_run:
            self.store.retry_errors(self.current_run)
            self.load_run()
            self.resume()

    def pause(self):
        if self.worker:
            self.worker.pause()
            self.log.append('Đã yêu cầu tạm dừng; đang chờ yêu cầu hiện tại hoàn tất.')

    def disconnect(self):
        try:
            Vault().clear()
            self.connection.setText('Đã xóa kết nối trên máy')
            self.log.append('Đã xóa thông tin xác thực của app trong Windows Credential Manager. Có thể thu hồi quyền ứng dụng tại Finhay; dữ liệu đã lưu được giữ lại.')
        except Exception:
            QMessageBox.warning(self, 'Không xóa được', 'Không truy cập được Windows Credential Manager.')

    def closeEvent(self, event):
        if self.worker is not None:
            self.pause()
            event.ignore()
            self.log.append('Đợi tác vụ dừng rồi đóng lại cửa sổ; tiến độ quét đã lưu sau từng mã.')
            return
        self.store.close()
        event.accept()


STYLE = '''
QWidget { font-family: "Segoe UI"; font-size: 10pt; color: #1e293b; }
QMainWindow, QTabWidget::pane { background: #f8fafc; }
QTabWidget::pane { border: 1px solid #dbe4ed; border-radius: 6px; }
QTabBar::tab { padding: 10px 20px; background: #e2e8f0; }
QTabBar::tab:selected { background: #ffffff; color: #0369a1; }
QPushButton { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 5px; padding: 7px 12px; }
QPushButton:hover { background: #e0f2fe; border-color: #0284c7; }
QPushButton:disabled { color: #94a3b8; background: #f1f5f9; }
QLineEdit, QComboBox, QSpinBox, QDateEdit { background: white; padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px; }
QTableView { background: white; alternate-background-color: #f1f5f9; gridline-color: #e2e8f0; border: 1px solid #e2e8f0; }
QHeaderView::section { background: #e0f2fe; color: #0c4a6e; padding: 7px; border: 1px solid #dbeafe; font-weight: 600; }
QProgressBar { border: 1px solid #cbd5e1; border-radius: 4px; text-align: center; min-height: 22px; }
QProgressBar::chunk { background: #7dd3fc; }
QTextEdit { background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 4px; }
'''
