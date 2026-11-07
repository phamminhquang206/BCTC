"""Statement matrix: indicators down rows, chronological periods across columns."""
from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QRectF
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QStyledItemDelegate, QTableView,
    QVBoxLayout, QWidget, QAbstractItemView,
)

from .exporting import export_rows
from .finance import number
from .financial_labels import LABELS, TOTALS, unit_for, ordered_metrics

REPORT_NAMES = {'income-statement': 'Kết quả kinh doanh', 'balance-sheet': 'Cân đối kế toán', 'cash-flow': 'Lưu chuyển tiền tệ'}
SCALES = [('Tỷ VND', 1_000_000_000), ('Triệu VND', 1_000_000), ('VND', 1)]
IGNORED = {'year', 'quarter', 'symbol', 'currency', 'period', 'type', 'unit', 'updated_at', 'report_scope', 'period_basis', 'is_consolidated'}


def period_label(period):
    year, quarter = period
    return f'Q{quarter}/{year}' if quarter is not None else str(year)


class FinancialModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.records, self.periods, self.metrics = [], [], []
        self.by_period = {}
        self.scale = 1_000_000_000
        self.window_size, self.end = 8, 0

    @property
    def visible_periods(self):
        return self.periods[max(0, self.end - self.window_size):self.end] if self.window_size else self.periods

    def set_records(self, records):
        self.beginResetModel()
        self.records = [dict(r) for r in records if isinstance(r.get('year'), int) and (r.get('quarter') is None or r.get('quarter') in (1, 2, 3, 4))]
        self.by_period = {(r['year'], r.get('quarter')): r for r in self.records}
        periods = sorted(self.by_period, key=lambda p: (p[0], p[1] or 0))
        # Missing periods between available reports stay visible as blank columns.
        if periods and all(p[1] is not None for p in periods):
            start, stop = periods[0][0] * 4 + periods[0][1] - 1, periods[-1][0] * 4 + periods[-1][1] - 1
            self.periods = [(n // 4, n % 4 + 1) for n in range(start, stop + 1)]
        elif periods and all(p[1] is None for p in periods):
            self.periods = [(y, None) for y in range(periods[0][0], periods[-1][0] + 1)]
        else:
            self.periods = periods
        keys = list(dict.fromkeys(k for r in self.records for k in r if k not in IGNORED and not k.startswith('_')))
        keys = [k for k in keys if all(r.get(k) is None or number(r.get(k)) is not None for r in self.records)]
        self.metrics = ordered_metrics(keys)
        self.end = len(self.periods)
        self.endResetModel()

    def set_window(self, size, end=None):
        self.beginResetModel()
        self.window_size = size
        minimum = min(size, len(self.periods)) if size else len(self.periods)
        self.end = min(len(self.periods), max(minimum, self.end if end is None else end))
        self.endResetModel()

    def set_scale(self, scale):
        self.scale = scale
        if self.rowCount() and self.columnCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.metrics)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 2 + len(self.visible_periods)

    def value(self, key, period):
        return number(self.by_period.get(period, {}).get(key))

    def label(self, key):
        label = LABELS.get(key, key)
        unit = unit_for(key)
        return label if unit == 'VND' else f'{label} ({unit})'

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            return ('Chỉ tiêu', 'Xu hướng')[section] if section < 2 else period_label(self.visible_periods[section - 2])
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter) if section == 0 else int(Qt.AlignRight | Qt.AlignVCenter)
        if role == Qt.FontRole and section >= 2 and self.visible_periods[section - 2] == self.periods[-1]:
            font = QFont()
            font.setBold(True)
            return font

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        key, column = self.metrics[index.row()], index.column()
        period = self.visible_periods[column - 2] if column >= 2 else None
        value = self.value(key, period) if period else None
        if role == Qt.UserRole:
            return [self.value(key, p) for p in self.visible_periods] if column == 1 else value
        if role == Qt.DisplayRole:
            if column == 0:
                return f'{index.row() + 1}. {self.label(key)}'
            if column == 1:
                return ''
            if value is None:
                return '—'
            if unit_for(key) == 'VND':
                return f'{value / self.scale:,.1f}' if self.scale != 1 else f'{value:,.0f}'
            return f'{value:,.2f}'.rstrip('0').rstrip('.')
        if role == Qt.ToolTipRole:
            if column < 2:
                return self.label(key) + '\nMã chỉ tiêu nguồn: ' + key
            row = self.by_period.get(period, {})
            raw = 'Không có dữ liệu' if value is None else f'{value:,} {unit_for(key)}'
            return f'{self.label(key)} • {period_label(period)}\n{raw}\nLấy từ Finhay: {row.get("_fetched_at", "không có kỳ này")}'
        if role == Qt.TextAlignmentRole:
            return int((Qt.AlignLeft if column == 0 else Qt.AlignRight) | Qt.AlignVCenter)
        if role == Qt.ForegroundRole and column >= 2:
            if value is None:
                return QColor('#94a3b8')
            if value < 0:
                return QColor('#dc2626')
            return QColor('#0f172a' if period == self.periods[-1] else '#475569')
        if role == Qt.BackgroundRole and key in TOTALS:
            return QColor('#f0f7fc')
        if role == Qt.FontRole:
            font = QFont()
            font.setBold(key in TOTALS or (column >= 2 and period == self.periods[-1]))
            return font


class TrendDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        values = index.data(Qt.UserRole) or []
        known = [v for v in values if v is not None]
        if not known:
            return
        painter.save()
        area = option.rect.adjusted(9, 9, -9, -9)
        low, high = min(0, min(known)), max(0, max(known))
        span = high - low or 1
        baseline = area.top() + high / span * area.height()
        step = area.width() / max(1, len(values))
        painter.setPen(Qt.NoPen)
        for i, value in enumerate(values):
            if value is None:
                continue
            painter.setBrush(QColor('#dc2626' if value < 0 else '#3b82f6'))
            y = area.top() + (high - value) / span * area.height()
            rect = QRectF(area.left() + i * step, min(y, baseline), max(1, step - 2), max(1, abs(y - baseline)))
            painter.drawRect(rect)
        painter.restore()


class FrozenStatementTable(QTableView):
    def __init__(self, model):
        super().__init__()
        self.setModel(model)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(34)
        self.horizontalHeader().setMinimumSectionSize(68)
        self.horizontalHeader().setDefaultSectionSize(90)
        self.horizontalHeader().setStretchLastSection(False)
        self.setItemDelegateForColumn(1, TrendDelegate(self))
        self.frozen = QTableView(self)
        self.frozen.setModel(model)
        self.frozen.setSelectionModel(self.selectionModel())
        self.frozen.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.frozen.setSelectionMode(QAbstractItemView.SingleSelection)
        self.frozen.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.frozen.setFocusPolicy(Qt.NoFocus)
        self.frozen.verticalHeader().hide()
        self.frozen.verticalHeader().setDefaultSectionSize(34)
        self.frozen.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozen.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozen.setAlternatingRowColors(True)
        self.frozen.setShowGrid(False)
        self.frozen.setStyleSheet('QTableView { border:0; border-right: 1px solid #cbd5e1; }')
        self.verticalScrollBar().valueChanged.connect(self.frozen.verticalScrollBar().setValue)
        self.frozen.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)
        self.horizontalHeader().sectionResized.connect(self.resize_column)
        self.frozen.horizontalHeader().sectionResized.connect(lambda col, old, width: self.setColumnWidth(0, width) if col == 0 else None)
        model.modelReset.connect(self.configure)
        self.configure()

    def configure(self):
        for col in range(1, self.model().columnCount()):
            self.frozen.setColumnHidden(col, True)
        self.setColumnWidth(0, min(440, max(300, int(self.width() * .35))))
        self.setColumnWidth(1, 78)
        self.update_frozen()

    def resize_column(self, col, old, width):
        if col == 0:
            self.frozen.setColumnWidth(0, width)
            self.update_frozen()

    def update_frozen(self):
        if hasattr(self, 'frozen'):
            self.frozen.setGeometry(self.frameWidth(), self.frameWidth(), self.columnWidth(0), self.viewport().height() + self.horizontalHeader().height())
            self.frozen.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'frozen'):
            self.setColumnWidth(0, min(440, max(300, int(self.width() * .35))))
        self.update_frozen()

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        if index.column() != 0:
            super().scrollTo(index, hint)


class FinancialView(QWidget):
    def __init__(self):
        super().__init__()
        self.model = FinancialModel()
        self.context = {}
        self.setStyleSheet('QTableView { color:#172b4d; background:white; alternate-background-color:#f1f5f9; selection-background-color:#dbeafe; selection-color:#0f172a; } QHeaderView::section { background:#e2e8f0; color:#334155; border:0; border-bottom:1px solid #b8c5d6; padding:9px; }')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.heading = QLabel('Báo cáo tài chính')
        self.heading.setStyleSheet('font-weight:700; font-size:12pt; padding:4px 0;')
        layout.addWidget(self.heading)
        bar = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText('Tìm chỉ tiêu: doanh thu, lợi nhuận, tiền…')
        self.query.textChanged.connect(self.filter_rows)
        self.primary_only = QCheckBox('Chỉ tiêu chính')
        self.primary_only.toggled.connect(self.filter_rows)
        self.unit = QComboBox()
        for label, scale in SCALES:
            self.unit.addItem(label, scale)
        self.unit.currentIndexChanged.connect(lambda: self.model.set_scale(self.unit.currentData()))
        self.window = QComboBox()
        for label, count in [('8 kỳ', 8), ('12 kỳ', 12), ('Tất cả kỳ', 0)]:
            self.window.addItem(label, count)
        self.window.currentIndexChanged.connect(self.window_changed)
        self.previous, self.next = QPushButton('‹'), QPushButton('›')
        self.previous.setToolTip('Xem kỳ trước')
        self.next.setToolTip('Xem kỳ sau')
        self.previous.setMaximumWidth(32)
        self.next.setMaximumWidth(32)
        self.previous.clicked.connect(lambda: self.move(-1))
        self.next.clicked.connect(lambda: self.move(1))
        self.export_current = QPushButton('Xuất đang xem')
        self.export_all = QPushButton('Xuất tất cả')
        self.export_current.clicked.connect(lambda: self.export(True))
        self.export_all.clicked.connect(lambda: self.export(False))
        for widget in (self.query, self.primary_only, QLabel('Đơn vị'), self.unit, self.previous, self.window, self.next, self.export_current, self.export_all):
            bar.addWidget(widget)
        layout.addLayout(bar)
        self.view = FrozenStatementTable(self.model)
        layout.addWidget(self.view)
        self.summary = QLabel('Chọn loại báo cáo và khoảng năm, sau đó bấm Lấy dữ liệu.')
        self.summary.setStyleSheet('color:#64748b; padding:4px;')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.model.modelReset.connect(self.refresh_view)
        self.refresh_view()

    def set_records(self, rows, context=None):
        self.context = context or {}
        name = REPORT_NAMES.get(self.context.get('report'), 'Báo cáo tài chính')
        self.heading.setText(f'{self.context.get("symbol", "")} · {name}'.strip(' ·'))
        self.model.set_records(rows)

    def window_changed(self):
        self.model.set_window(self.window.currentData())

    def snapshot(self):
        return {'query': self.query.text(), 'primary': self.primary_only.isChecked(),
                'unit': self.unit.currentIndex(), 'window': self.window.currentIndex(),
                'end': self.model.end, 'at_latest': self.model.end == len(self.model.periods),
                'horizontal': self.view.horizontalScrollBar().value(),
                'vertical': self.view.verticalScrollBar().value()}

    def restore_state(self, state=None):
        state = state or {}
        self.query.setText(state.get('query', ''))
        self.primary_only.setChecked(state.get('primary', False))
        self.unit.setCurrentIndex(state.get('unit', 0))
        self.model.set_scale(self.unit.currentData())
        self.window.setCurrentIndex(state.get('window', 0))
        end = len(self.model.periods) if state.get('at_latest', True) else state.get('end', len(self.model.periods))
        self.model.set_window(self.window.currentData(), end)
        self.view.doItemsLayout()
        self.view.frozen.doItemsLayout()
        self.view.horizontalScrollBar().setValue(state.get('horizontal', 0))
        self.view.verticalScrollBar().setValue(state.get('vertical', 0))

    def move(self, delta):
        self.model.set_window(self.model.window_size, self.model.end + delta)

    def filter_rows(self):
        query = self.query.text().strip().casefold()
        for row, key in enumerate(self.model.metrics):
            hidden = (query not in (LABELS.get(key, key) + ' ' + key).casefold()) or (self.primary_only.isChecked() and key not in TOTALS)
            self.view.setRowHidden(row, hidden)
            self.view.frozen.setRowHidden(row, hidden)

    def refresh_view(self):
        self.filter_rows()
        periods = self.model.visible_periods
        self.previous.setEnabled(bool(self.model.window_size and self.model.end > self.model.window_size))
        self.next.setEnabled(bool(self.model.window_size and self.model.end < len(self.model.periods)))
        self.export_current.setEnabled(bool(self.model.metrics))
        self.export_all.setEnabled(bool(self.model.metrics))
        if not self.model.records:
            self.summary.setText('Finhay chưa có số liệu cho khoảng thời gian này.' if self.context.get('loaded') else 'Chưa tải báo cáo cho lựa chọn này. Bấm Lấy dữ liệu để tải. Các báo cáo đã tải ở lựa chọn khác vẫn được giữ lại.')
            return
        span = f'{period_label(periods[0])} → {period_label(periods[-1])}' if periods else 'Chưa có số liệu'
        self.summary.setText(f'{span} · {len(self.model.metrics)} chỉ tiêu · Cột tên cố định khi cuộn ngang · “—”: thiếu dữ liệu · Số âm: màu đỏ · EPS giữ VND/cổ phiếu.\nSố liệu theo nguồn Finhay; chưa tự xác định quý riêng/lũy kế hoặc hợp nhất/riêng lẻ. Xuất file giữ giá trị gốc.')

    def export_data(self, current):
        periods = self.model.visible_periods if current else self.model.periods
        keys = [key for row, key in enumerate(self.model.metrics) if not current or not self.view.isRowHidden(row)]
        return [{'Chỉ tiêu': LABELS.get(key, key), 'Mã chỉ tiêu': key, 'Đơn vị gốc': unit_for(key),
                 **{period_label(p): self.model.value(key, p) for p in periods}} for key in keys]

    def export(self, current):
        rows = self.export_data(current)
        if not rows:
            QMessageBox.information(self, 'Xuất báo cáo', 'Không có chỉ tiêu đang xem để xuất.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Xuất báo cáo — các giá trị giữ đơn vị gốc', 'bao-cao-tai-chinh.xlsx', 'Excel (*.xlsx);;CSV UTF-8 (*.csv)')
        if path:
            try:
                metadata = {**self.context, 'xuat_luc': datetime.now().astimezone().isoformat(), 'don_vi_hien_thi': self.unit.currentText(), 'gia_tri_xuat': 'Đơn vị gốc theo từng chỉ tiêu'}
                export_rows(path, rows, metadata)
                QMessageBox.information(self, 'Đã xuất', 'Đã lưu bảng báo cáo theo chỉ tiêu và kỳ. Số tiền giữ VND gốc; EPS giữ VND/cổ phiếu.')
            except Exception as exc:
                QMessageBox.warning(self, 'Không lưu được', f'Kiểm tra quyền ghi và đóng file đang mở. ({type(exc).__name__})')
