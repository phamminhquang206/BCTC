import json
import re
from collections import OrderedDict
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QDate, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QCompleter, QDateEdit, QFileDialog,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QSplitter, QTabWidget,
    QTableView, QTextEdit, QVBoxLayout, QWidget, QTabBar, QDockWidget, QToolButton,
)

from .auth import REDIRECT, Vault
from .engine import Worker
from .exporting import export_rows
from .storage import Store
from .financial_view import FinancialView
from .overview_view import OverviewView, overview_from_rows
from .ui_controls import StepSpinBox, set_light_palette
from .activity_log import ActivityLog
from .finance import build_result, previous_period, sector_info
from .price_view import PriceView

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
    'sector_group': 'Nhóm ngành', 'sector_name': 'Ngành', 'sector_slug': 'Mã ngành',
    'sector_level': 'Cấp ngành', 'period_label': 'Kỳ',
    'revenue_previous': 'Doanh thu quý trước', 'revenue_year_ago': 'Doanh thu cùng kỳ năm trước',
    'profit_previous': 'LNST quý trước', 'profit_year_ago': 'LNST cùng kỳ năm trước',
    'parent_profit_previous': 'LNST mẹ quý trước', 'parent_profit_year_ago': 'LNST mẹ cùng kỳ năm trước',
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
        self.column_order, self.column_labels = [], {}
        self.datetime_values = False

    def set_rows(self, rows, money=None):
        self.beginResetModel()
        self.rows = rows
        priority = ['symbol', 'name', 'exchange', 'year', 'quarter', 'status', 'revenue_label', 'revenue', 'profit', 'parent_profit']
        keys = list(dict.fromkeys(k for row in rows for k in row))
        priority = self.column_order or priority
        self.keys = (list(priority) if self.column_order else [k for k in priority if k in keys]) + [k for k in keys if k not in priority]
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
                return self.column_labels.get(key, LABELS.get(key, key)) + (' (tỷ VND)' if key in self.money else '')
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
                if key == 't' and self.datetime_values:
                    return datetime.fromtimestamp(value, timezone(timedelta(hours=7))).strftime('%d/%m/%Y')
                if key in ('year', 'quarter'):
                    return str(value)
                if key in self.money:
                    return f'{value / 1_000_000_000:,.3f}'
                if key.endswith('_percent'):
                    return f'{value:,.2f}%'
                return f'{value:,}'
            return str(value)
        if role == Qt.ToolTipRole:
            if key == 'status':
                return STATUS.get(value, str(value)) + (': ' + self.rows[index.row()]['message'] if self.rows[index.row()].get('message') else '')
            if key.endswith('_percent') and value is None:
                state = self.rows[index.row()].get(key.removesuffix('_percent') + '_state', '')
                if state:
                    return f'{LABELS.get(key, key)}: {state}. Không quy đổi dữ liệu thiếu hoặc kỳ gốc không dương thành 0%.'
            return f'{key}: {value}'
        if role == Qt.TextAlignmentRole and isinstance(value, (int, float)):
            return int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.ForegroundRole and key == 'status':
            return QColor({'ok': '#15803d', 'missing': '#a16207', 'error': '#dc2626'}.get(value, '#475569'))
        if role == Qt.ForegroundRole and key.endswith('_percent') and isinstance(value, (int, float)):
            return QColor('#b91c1c' if value < 0 else ('#166534' if value > 0 else '#475569'))
        if role == Qt.ForegroundRole and key in self.money and isinstance(value, (int, float)) and value < 0:
            return QColor('#b91c1c')


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
        self.is_scan = scan
        self.price_mode = False
        self.export_metadata = {}
        self.core_columns = []
        self.details = QCheckBox('Cột chi tiết')
        self.details.setVisible(scan)
        self.details.toggled.connect(self.apply_scan_columns)
        export = QPushButton('Xuất bảng đang lọc')
        export.clicked.connect(lambda: self.export(True))
        export_all = QPushButton('Xuất toàn bộ')
        export_all.clicked.connect(lambda: self.export(False))
        bar = QHBoxLayout()
        for w in (self.query, self.status, self.details, export, export_all):
            bar.addWidget(w)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self.view)

    def set_scan_rows(self, rows, config):
        annual = config['period'] == 'annual'
        self.core_columns = ['symbol', 'name', 'sector_group', 'status', 'period_label']
        for metric in ('revenue', 'profit'):
            self.core_columns += [metric]
            if not annual:
                self.core_columns += [metric + '_previous']
            self.core_columns += [metric + '_year_ago']
            if not annual:
                self.core_columns += [metric + '_qoq_percent']
            self.core_columns += [metric + '_yoy_percent']
        self.core_columns += ['message']
        self.model.column_order = self.core_columns
        year, quarter = config['year'], config['quarter']
        def period(y, q):
            return f'Q{q}/{y}' if q else str(y)
        py, pq = previous_period(year, quarter) if quarter else (year - 1, None)
        self.model.column_labels = {}
        for metric, label in (('revenue', 'Doanh thu'), ('profit', 'LNST')):
            self.model.column_labels.update({metric: f'{label}\n{period(year, quarter)}',
                metric + '_previous': f'{label}\n{period(py, pq)}',
                metric + '_year_ago': f'{label}\n{period(year - 1, quarter)}',
                metric + '_qoq_percent': f'{label} %\nso quý trước',
                metric + '_yoy_percent': f'{label} %\nso cùng kỳ'})
        money = {key for key in self.core_columns if key.startswith(('revenue', 'profit')) and not key.endswith('_percent')}
        money |= {'parent_profit', 'parent_profit_previous', 'parent_profit_year_ago'}
        money |= {key for row in rows for key in row if key.endswith('_delta')}
        self.model.set_rows(rows, money)
        self.query.setPlaceholderText('Lọc theo mã, doanh nghiệp, nhóm ngành hoặc ghi chú…')
        widths = {'symbol': 65, 'name': 190, 'sector_group': 170, 'status': 150, 'period_label': 90, 'message': 280}
        for key in self.core_columns:
            self.view.setColumnWidth(self.model.keys.index(key), widths.get(key, 140))
        self.apply_scan_columns()

    def apply_scan_columns(self, *_):
        if self.is_scan and self.core_columns:
            for col, key in enumerate(self.model.keys):
                self.view.setColumnHidden(col, not self.details.isChecked() and key not in self.core_columns)

    def update_scan_row(self, row):
        index = next((i for i, existing in enumerate(self.model.rows) if existing.get('symbol') == row['symbol']), None)
        if index is None:
            return
        new_keys = [key for key in row if key not in self.model.keys]
        if new_keys:
            start = len(self.model.keys)
            self.model.beginInsertColumns(QModelIndex(), start, start + len(new_keys) - 1)
            self.model.keys.extend(new_keys)
            self.model.money.update(key for key in new_keys if key.endswith('_delta'))
            self.model.endInsertColumns()
        self.model.rows[index] = {**self.model.rows[index], **row}
        self.model.dataChanged.emit(self.model.index(index, 0), self.model.index(index, len(self.model.keys) - 1))
        self.apply_scan_columns()

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
                export_rows(path, self.export_data(rows), {'thoi_diem_xuat': datetime.now().astimezone().isoformat(), 'bang': 'đang lọc' if filtered else 'toàn bộ', **self.export_metadata})
                QMessageBox.information(self, 'Đã xuất', 'Đã lưu file. Các giá trị tiền giữ đơn vị gốc; xem currency/unit nếu nguồn cung cấp.')
            except Exception as exc:
                QMessageBox.warning(self, 'Không lưu được', f'Kiểm tra quyền ghi và đóng file Excel đang mở. ({type(exc).__name__})')

    def export_data(self, rows):
        if self.price_mode:
            names = {key: self.model.column_labels.get(key, LABELS.get(key, key)) for key in ('t', 'o', 'h', 'l', 'c', 'v')}
            return [{names[key]: datetime.fromtimestamp(row['t'], timezone(timedelta(hours=7))).strftime('%d/%m/%Y') if key == 't' else row.get(key) for key in names} for row in rows]
        if not self.is_scan or not self.core_columns:
            return rows
        keys = [key for col, key in enumerate(self.model.keys) if not self.view.isColumnHidden(col)]
        def title(key):
            text = self.model.column_labels.get(key, LABELS.get(key, key)).replace('\n', ' ')
            return text + (' (VND)' if key in self.model.money else '')
        return [{title(key): STATUS.get(row.get(key), row.get(key)) if key == 'status' else row.get(key) for key in keys} for row in rows]



def spin(low, high, value):
    widget = StepSpinBox()
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
        self.financial_cache = OrderedDict()
        self.financial_states = {}
        self._financial_key = None
        self._task_summary = None
        self._scan_statuses = {}
        self._scan_config = {}
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
        self.log = ActivityLog()
        self.log_dock = QDockWidget('Nhật ký hoạt động', self)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.log_dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.log_dock.setWidget(self.log)
        self.log_dock.setMaximumHeight(170)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.log_dock.hide()
        self.log_toggle = QToolButton()
        self.log_toggle.setDefaultAction(self.log_dock.toggleViewAction())
        self.log_toggle.setText('Nhật ký')
        self.log_toggle.setToolTip('Hiện / ẩn nhật ký xử lý chi tiết')
        self.statusBar().addPermanentWidget(self.log_toggle)
        self.statusBar().setToolTip(f'Dữ liệu: {data_dir} | Callback: {REDIRECT}')
        self.statusBar().showMessage('Sẵn sàng')
        self.log.message_added.connect(self.statusBar().showMessage)
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
        self.fetch_buttons = {}
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
            button = QPushButton('Lấy dữ liệu')
            button.setProperty('primary', True)
            button.setMinimumHeight(38)
            button.setCursor(Qt.PointingHandCursor)
            self.fetch_buttons[key] = button
            if key == 'financial':
                button.setToolTip('Tải cả 3 báo cáo tài chính, mỗi loại theo quý và theo năm, trong khoảng năm đã chọn.')
            button.clicked.connect(lambda checked=False, section=key: self.lookup(section))
            self.lookup_buttons.append(button)
            if key != 'price':
                options.addWidget(button)
            if key == 'financial':
                hint = QLabel('Tải cả 3 báo cáo · Quý và năm')
                hint.setStyleSheet('color:#475569; font-size:12px;')
                options.addWidget(hint)
            options.addStretch()
            if key != 'price':
                box.addLayout(options)
            if key == 'price':
                self.price_panel = PriceView(DataTable)
                self.price_panel.set_query_controls(self.from_date, self.to_date, button)
                self.quote_label = self.price_panel.quote
                self.chart = self.price_panel.chart
                table = self.price_panel.table
                box.addWidget(self.price_panel, 1)
            else:
                table = FinancialView() if key == 'financial' else (OverviewView() if key == 'overview' else DataTable())
                box.addWidget(table)
            self.lookup_tables[key] = table
            self.sections.addTab(page, title)
        layout.addWidget(self.sections)
        self.tabs.addTab(tab, 'Tra cứu cổ phiếu')
        for signal in (self.report.currentIndexChanged, self.period.currentIndexChanged,
                       self.from_year.valueChanged, self.to_year.valueChanged, self.symbol.textChanged):
            signal.connect(self.financial_selection_changed)
        self.financial_selection_changed()

    def financial_context(self):
        return {'symbol': self.symbol.text().split('—')[0].strip().upper(),
                'report': self.report.currentData(), 'period': self.period.currentData(),
                'from_year': self.from_year.value(), 'to_year': self.to_year.value(), 'source': 'Finhay MCP'}

    @staticmethod
    def financial_key(context):
        return tuple(context.get(key) for key in ('symbol', 'report', 'period', 'from_year', 'to_year'))

    def financial_selection_changed(self, *_):
        table = self.lookup_tables['financial']
        if self._financial_key in self.financial_cache:
            self.financial_states[self._financial_key] = table.snapshot()
        context = self.financial_context()
        key = self.financial_key(context)
        self._financial_key = key
        cached = self.financial_cache.get(key)
        if cached is not None:
            self.financial_cache.move_to_end(key)
            table.set_records(cached['rows'], cached['context'])
            table.restore_state(self.financial_states.get(key))
        else:
            table.set_records([], context)
            table.restore_state()

    def receive_financial(self, rows, result):
        config = result.get('config', {})
        context = {**self.financial_context(), **{k: config[k] for k in ('report', 'period', 'from_year', 'to_year') if k in config},
                   'symbol': result['symbol'], 'loaded': True}
        key = self.financial_key(context)
        self.financial_cache[key] = {'rows': rows, 'context': context}
        self.financial_cache.move_to_end(key)
        # Raw data already persists in SQLite. Keep only the 12 most recently
        # viewed query contexts in memory, including view state for each one.
        while len(self.financial_cache) > 12:
            old_key, _ = self.financial_cache.popitem(last=False)
            self.financial_states.pop(old_key, None)
        if key == self.financial_key(self.financial_context()):
            self.financial_selection_changed()

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
        note = QLabel('Quý: so cùng kỳ và quý trước. Năm: so năm trước. Chưa xác minh cơ sở quý → chưa tính tăng trưởng. Kỳ gốc ≤ 0: % để trống. Xuất file giữ VND gốc.')
        note.setWordWrap(True)
        layout.addWidget(note)
        bar = QHBoxLayout()
        self.start_scan = QPushButton('Chạy lượt quét mới')
        self.start_scan.setProperty('primary', True)
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
        self.symbol.setEnabled(not value)

    def launch(self, action, config=None):
        if self.worker is not None:
            self.log.append('Đang có tác vụ chạy. Chờ hoàn tất hoặc bấm tạm dừng.')
            return
        self.busy(True)
        self._task_summary = None
        if action == 'lookup' and config:
            self.fetch_buttons[config['section']].setText('Đang tải…')
            if config['section'] == 'financial':
                # Report and period are view selectors during a six-way fetch.
                # Symbol and year range remain locked to the submitted query.
                self.report_tabs.setEnabled(True)
                self.period.setEnabled(True)
        self.worker = Worker(self.store, action, config)
        self.worker.message.connect(self.log.append)
        self.worker.failed.connect(self.on_error)
        self.worker.result.connect(lambda result: self.on_result(action, result))
        self.worker.row_ready.connect(self.scan_row_ready)
        if action == 'lookup' and config and config['section'] == 'financial':
            self.worker.progress.connect(self.financial_progress)
        else:
            self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.worker_finished)
        self.log.append('Bắt đầu: ' + {'connect': 'kết nối Finhay', 'lookup': 'tra cứu', 'catalog': 'tải danh sách mã', 'scan': 'quét kết quả kinh doanh'}[action])
        self.worker.start()

    def worker_finished(self):
        worker = self.worker
        self.worker = None
        self.busy(False)
        for button in self.fetch_buttons.values():
            button.setText('Lấy dữ liệu')
        if worker:
            worker.deleteLater()
        if not self._task_summary:
            self.log.append('Tác vụ đã dừng/kết thúc. Dữ liệu nhận được đã lưu trên máy.')

    def financial_progress(self, done, total):
        self.fetch_buttons['financial'].setText(f'Đang tải {done}/{total}')

    def on_error(self, message):
        self._task_summary = message
        if any(word in message.lower() for word in ('đăng nhập', 'xác thực')):
            self.connection.setText('Cần kết nối lại Finhay')
        self.log.append(message)
        QMessageBox.warning(self, 'Tác vụ đã tạm dừng', message)

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
            if result.get('kind') == 'financial_summary':
                if result['cancelled']:
                    summary = f'{result["symbol"]}: đã dừng; giữ lại {result["completed"]}/{result["total"]} bộ báo cáo đã tải.'
                else:
                    summary = f'{result["symbol"]}: đã tải {result["completed"]}/{result["total"]} bộ báo cáo tài chính (quý và năm).'
                if result['failed']:
                    summary += f' {len(result["failed"])} bộ lỗi; xem Nhật ký và bấm Lấy dữ liệu để thử lại.'
                self._task_summary = summary
                self.log.append(summary)
                return
            section, rows = result['section'], result['rows']
            # Exported rows carry provenance and original units.
            rows = [dict(r, _symbol=result['symbol'], _fetched_at=r.get('_fetched_at') or result['stamp'], _source='Finhay MCP') for r in rows]
            if section == 'financial':
                self.receive_financial(rows, result)
            elif section == 'overview':
                self.lookup_tables[section].set_overview(result.get('overview') or overview_from_rows(rows), result['symbol'], result['stamp'])
            elif section == 'price':
                self.price_panel.set_result(rows, result.get('quote') or {}, result['symbol'], result['stamp'])
            else:
                self.lookup_tables[section].model.set_rows(rows)
                self.lookup_tables[section].view.resizeColumnsToContents()
            section_name = {'overview': 'tổng quan', 'financial': 'báo cáo tài chính', 'price': 'giá cổ phiếu', 'events': 'cổ tức và quyền'}[section]
            self.log.append(f'{result["symbol"]}: đã tải {section_name}.\n{result["stamp"]}')
        elif action == 'scan':
            self.current_run = result['run_id']
            self.reload_runs(self.current_run)
            if result.get('finished'):
                self._task_summary = ('Lượt quét đã tạm dừng.' if result.get('paused') else 'Đã xử lý hết các mã đang chờ.')
                if result.get('reason'):
                    self._task_summary += ' ' + result['reason']
                self.log.append(self._task_summary)

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
        config = self.store.config(self.current_run)
        config.setdefault('period', 'quarterly' if config.get('quarter') else 'annual')
        rows = []
        for job in jobs:
            data = json.loads(job['result']) if job['result'] else {}
            meta = config.get('universe', {}).get(job['symbol'], {})
            data.update(symbol=job['symbol'], name=data.get('name') or meta.get('name', ''), exchange=data.get('exchange') or meta.get('exchange', ''))
            if job['result'] and data.get('schema_version', 0) < 2:
                cached_rows = []
                for year in (config['year'], config['year'] - 1):
                    cached = self.store.cached('get_financial_statement', dict(symbol=job['symbol'], type='income-statement', period=config['period'], year=year, limit=5, page=1))
                    if cached:
                        cached_rows.extend(cached[0].get('items', []))
                if cached_rows:
                    enriched = build_result(job['symbol'], data['name'], data['exchange'], cached_rows, config['year'], config['quarter'], config['basis'])
                    old_message = data.get('message', '')
                    data.update(enriched)
                    if job['status'] == 'error':
                        data['message'] = old_message
                profile = self.store.cached('get_stock_profile', {'symbol': job['symbol']})
                if profile:
                    data.update(sector_info(profile[0]))
            data['status'] = job['status']
            data.setdefault('period_label', f'Q{config["quarter"]}/{config["year"]}' if config['quarter'] else str(config['year']))
            rows.append(data)
        self.scan_table.set_scan_rows(rows, config)
        self._scan_statuses = {job['symbol']: job['status'] for job in jobs}
        self._scan_config = config
        self.update_scan_counts()
        counts = {key: sum(j['status'] == key for j in jobs) for key in STATUS}
        self.update_progress(len(jobs) - counts['pending'], len(jobs))

    def scan_row_ready(self, row):
        self.scan_table.update_scan_row(row)
        self._scan_statuses[row['symbol']] = row['status']
        self.update_scan_counts()

    def update_scan_counts(self):
        config = self._scan_config
        counts = {key: sum(status == key for status in self._scan_statuses.values()) for key in STATUS}
        basis_label = {'unknown': 'chưa xác minh', 'standalone': 'quý riêng', 'cumulative': 'lũy kế'}.get(config['basis'], config['basis'])
        self.counts.setText(' | '.join(f'{STATUS[key]}: {val}' for key, val in counts.items()) + f' • Cơ sở quý: {basis_label}')

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
QWidget { font-family: "Segoe UI"; font-size: 10pt; color: #172b4d; }
QMainWindow, QTabWidget::pane { background: #f5f7fb; }
QTabWidget::pane { border: 1px solid #dbe4ed; border-radius: 6px; }
QTabBar::tab { padding: 9px 18px; background: #e2e8f0; color:#334155; border-bottom:3px solid transparent; }
QTabBar::tab:selected { background:#ffffff; color:#1d4ed8; border-bottom:3px solid #2563eb; font-weight:600; }
QPushButton { color:#172b4d; background:#ffffff; border:1px solid #aebed1; border-radius:5px; padding:7px 12px; }
QPushButton:hover { background:#eff6ff; border-color:#2563eb; }
QPushButton:pressed { background:#dbeafe; }
QPushButton[primary="true"] { background:#2563eb; color:#ffffff; border:1px solid #1d4ed8; font-weight:700; padding:8px 18px; }
QPushButton[primary="true"]:hover { background:#1d4ed8; }
QPushButton[primary="true"]:pressed { background:#1e40af; }
QPushButton:disabled, QPushButton[primary="true"]:disabled { color:#64748b; background:#e2e8f0; border-color:#cbd5e1; }
QLineEdit, QComboBox, QSpinBox, QDateEdit { color:#172b4d; background:white; padding:7px; border:1px solid #aebed1; border-radius:4px; selection-background-color:#dbeafe; selection-color:#0f172a; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus { border:1px solid #2563eb; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled { color:#64748b; background:#f1f5f9; }
QTableView { color:#172b4d; background:white; alternate-background-color:#f1f5f9; gridline-color:#e2e8f0; border:1px solid #cbd5e1; selection-background-color:#dbeafe; selection-color:#0f172a; }
QHeaderView::section { background:#e2e8f0; color:#334155; padding:8px; border:1px solid #cbd5e1; font-weight:600; }
QGroupBox { background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; margin-top:12px; padding:16px 12px 12px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 5px; color:#172b4d; }
QGroupBox QLabel, QGroupBox QTableWidget { font-weight:400; }
QScrollArea, QScrollArea > QWidget > QWidget { background:#f5f7fb; }
QProgressBar { border: 1px solid #cbd5e1; border-radius: 4px; text-align: center; min-height: 22px; }
QProgressBar::chunk { background: #7dd3fc; }
QTextEdit, QPlainTextEdit { color:#334155; background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; }
'''


def apply_theme(app):
    app.setStyle('Fusion')
    set_light_palette(app)
    app.setStyleSheet(STYLE)
