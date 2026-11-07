"""Daily/weekly OHLC candles, locally aggregated from the fetched daily series."""
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSplitter, QVBoxLayout, QWidget, QScrollArea, QFormLayout, QFrame,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QAbstractSpinBox, QLayout,
)

from .finance import number
from .indicators import calculate_indicators
from .ui_controls import StepSpinBox

VN = timezone(timedelta(hours=7))
GREEN, RED, FLAT = '#15803d', '#dc2626', '#64748b'


def trading_date(timestamp):
    return datetime.fromtimestamp(timestamp, VN).date()


def valid_ohlc(row):
    values = [number(row.get(k)) for k in ('o', 'h', 'l', 'c')]
    if any(value is None or value <= 0 for value in values):
        return False
    o, h, l, c = values
    return h >= max(o, c) and l <= min(o, c) and h >= l


def candle_color(row):
    return GREEN if row['c'] > row['o'] else (RED if row['c'] < row['o'] else FLAT)


def candle_change(close, base):
    """Return percent only with a known, positive comparison price."""
    close, base = number(close), number(base)
    return (close - base) / base * 100 if close is not None and base is not None and base > 0 else None


def price_series(rows, timeframe='1D'):
    """Use first open, max high, min low, last close; never invent missing OHLC."""
    by_time = {}
    for row in rows:
        stamp = number(row.get('t'))
        if stamp is None:
            continue
        try:
            trading_date(stamp)
        except (OSError, ValueError, OverflowError):
            continue
        item = {key: number(row.get(key)) for key in ('o', 'h', 'l', 'c', 'v')}
        item['t'] = int(stamp)
        if item['v'] is not None and item['v'] < 0:
            item['v'] = None
        by_time[item['t']] = item
    daily = sorted(by_time.values(), key=lambda row: row['t'])
    if timeframe == '1D':
        return daily
    if timeframe != '1W':
        raise ValueError('Khung giá phải là 1D hoặc 1W.')
    groups = defaultdict(list)
    for row in daily:
        day = trading_date(row['t'])
        groups[day - timedelta(days=day.weekday())].append(row)
    weekly = []
    for monday, group in sorted(groups.items()):
        stamp = int(datetime.combine(monday, time.min, VN).timestamp())
        # One incomplete daily bar makes the week's full OHLC unverified.
        if all(valid_ohlc(row) for row in group):
            values = dict(o=group[0]['o'], h=max(r['h'] for r in group),
                          l=min(r['l'] for r in group), c=group[-1]['c'])
        else:
            values = dict(o=None, h=None, l=None, c=None)
        volume = sum(row['v'] for row in group) if all(row['v'] is not None for row in group) else None
        weekly.append(dict(t=stamp, v=volume, **values))
    return weekly


class CandlestickChart(QWidget):
    hovered = Signal(object)
    view_changed = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.rows = []
        self.indicators = {}
        self.indicator_colors = {}
        self.end, self.count = 0, 0
        self.hover_index = None
        self._drag = None
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setToolTip('Rê chuột: xem OHLC · Cuộn: phóng/thu · Kéo ngang: xem các phiên trước · Toàn bộ: đặt lại khung xem')

    @property
    def visible_rows(self):
        return self.rows[max(0, self.end - self.count):self.end]

    def set_rows(self, rows):
        self.rows = [dict(row) for row in rows if valid_ohlc(row)]
        self._drag = None
        self.end = len(self.rows)
        self.count = min(150, len(self.rows))
        self.hover_index = None
        self.view_changed.emit(len(self.visible_rows), len(self.rows))
        self.hovered.emit(self.rows[-1] if self.rows else None)
        self.update()

    def set_indicators(self, rows, values):
        self.indicators = {key: {row['t']: value for row, value in zip(rows, series)}
                           for key, series in values.items()}
        ma_keys = [key for key in values if key.startswith('MA')]
        self.indicator_colors = {key: ('#d97706' if i == 0 else '#2563eb') for i, key in enumerate(ma_keys)}
        self.indicator_colors.update({'BB giữa': '#0891b2', 'BB trên': '#0891b2', 'BB dưới': '#0891b2'})
        self.indicator_colors.update({key: '#7c3aed' for key in values if key.startswith('RSI')})
        self.update()

    def reset_view(self):
        self.end = self.count = len(self.rows)
        self.hover_index = None
        self.view_changed.emit(len(self.visible_rows), len(self.rows))
        self.update()

    def plot_rect(self):
        return QRectF(16, 22, max(1, self.width() - 110), max(1, self.height() - 72))

    def zoom(self, factor):
        if not self.rows:
            return
        minimum = min(8, len(self.rows))
        self.count = max(minimum, min(len(self.rows), int(round(self.count * factor))))
        self.end = max(self.count, min(self.end, len(self.rows)))
        self.hover_index = None
        self.view_changed.emit(len(self.visible_rows), len(self.rows))
        self.update()

    def wheelEvent(self, event):
        self.zoom(.8 if event.angleDelta().y() > 0 else 1.25)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = (event.position().x(), self.end)
            self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        self._drag = None
        self.unsetCursor()

    def mouseMoveEvent(self, event):
        rect, visible = self.plot_rect(), self.visible_rows
        if not visible:
            return
        step = rect.width() / len(visible)
        if self._drag:
            distance = int((self._drag[0] - event.position().x()) / step)
            self.end = max(self.count, min(len(self.rows), self._drag[1] + distance))
            self.hover_index = None
            self.view_changed.emit(len(self.visible_rows), len(self.rows))
        elif rect.contains(event.position()):
            self.hover_index = min(len(visible) - 1, max(0, int((event.position().x() - rect.left()) / step)))
            self.hovered.emit(visible[self.hover_index])
        else:
            self.hover_index = None
        self.update()

    def leaveEvent(self, event):
        self.hover_index = None
        self.hovered.emit(self.rows[-1] if self.rows else None)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#ffffff'))
        rows = self.visible_rows
        if not rows:
            painter.setPen(QColor('#64748b'))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Chưa có đủ dữ liệu mở–cao–thấp–đóng cửa để vẽ nến.\nChọn khoảng ngày và bấm Lấy dữ liệu.')
            return
        rect = self.plot_rect()
        rsi_key = next((key for key in self.indicators if key.startswith('RSI')), None)
        rsi_height = rect.height() * .23 if rsi_key else 0
        rsi_top = rect.bottom() - rsi_height
        volume_bottom = rsi_top - 25 if rsi_key else rect.bottom()
        volume_height = max(10, rect.height() * .13)
        price_height = max(1, volume_bottom - rect.top() - volume_height - 26)
        volume_top = rect.top() + price_height + 26
        volume_height = max(1, volume_bottom - volume_top)
        low, high = min(r['l'] for r in rows), max(r['h'] for r in rows)
        overlay_values = [series.get(row['t']) for key, series in self.indicators.items()
                          if not key.startswith('RSI') for row in rows if series.get(row['t']) is not None]
        if overlay_values:
            low, high = min(low, min(overlay_values)), max(high, max(overlay_values))
        margin = max((high - low) * .07, high * .005, 1)
        low, high = low - margin, high + margin
        def y(value):
            return rect.top() + (high - value) / (high - low) * price_height
        ticks = 5 if price_height >= 120 else 3
        for i in range(ticks):
            value = high - (high - low) * i / (ticks - 1)
            yy = y(value)
            painter.setPen(QPen(QColor('#e2e8f0'), 1))
            painter.drawLine(QPointF(rect.left(), yy), QPointF(rect.right(), yy))
            painter.setPen(QColor('#475569'))
            painter.drawText(QRectF(rect.right() + 8, yy - 10, 82, 20), Qt.AlignLeft | Qt.AlignVCenter, f'{value:,.0f}')
        painter.drawText(QRectF(rect.right() + 8, 0, 82, 20), Qt.AlignLeft | Qt.AlignVCenter, 'VND')
        painter.setPen(QColor('#64748b'))
        painter.drawText(QRectF(rect.left(), volume_top - 20, 160, 20), Qt.AlignLeft | Qt.AlignVCenter, 'Khối lượng (cổ phiếu)')
        max_volume = max((row['v'] or 0 for row in rows), default=0)
        step = rect.width() / len(rows)
        body_width = max(1, min(16, step * .68))
        legend_x = rect.left()
        for key in self.indicators:
            if key in ('BB trên', 'BB dưới'):
                continue
            painter.setPen(QColor(self.indicator_colors[key]))
            label = 'BB' if key == 'BB giữa' else key
            width = painter.fontMetrics().horizontalAdvance(label) + 18
            painter.drawText(QRectF(legend_x, 0, width, 20), Qt.AlignLeft | Qt.AlignVCenter, label)
            legend_x += width
        for i, row in enumerate(rows):
            x = rect.left() + (i + .5) * step
            color = QColor(candle_color(row))
            painter.setPen(QPen(color, 1))
            painter.drawLine(QPointF(x, y(row['h'])), QPointF(x, y(row['l'])))
            painter.setBrush(color)
            painter.drawRect(QRectF(x - body_width / 2, min(y(row['o']), y(row['c'])), body_width, max(1, abs(y(row['o']) - y(row['c'])))))
            if max_volume and row['v'] is not None:
                color.setAlpha(110)
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                height = row['v'] / max_volume * volume_height
                painter.drawRect(QRectF(x - body_width / 2, volume_bottom - height, body_width, height))
        def draw_series(key, position_y):
            path = QPainterPath()
            previous = False
            for i, row in enumerate(rows):
                value = self.indicators[key].get(row['t'])
                if value is None:
                    previous = False
                    continue
                point = QPointF(rect.left() + (i + .5) * step, position_y(value))
                if previous:
                    path.lineTo(point)
                else:
                    path.moveTo(point)
                previous = True
            painter.setBrush(Qt.NoBrush)
            style = Qt.DashLine if key in ('BB trên', 'BB dưới') else Qt.SolidLine
            painter.setPen(QPen(QColor(self.indicator_colors[key]), 1.5, style))
            painter.drawPath(path)
        for key in self.indicators:
            if not key.startswith('RSI'):
                draw_series(key, y)
        if rsi_key:
            def rsi_y(value):
                return rsi_top + (100 - value) / 100 * rsi_height
            painter.fillRect(QRectF(rect.left(), rsi_y(70), rect.width(), rsi_y(30) - rsi_y(70)), QColor('#faf5ff'))
            painter.setPen(QColor('#7c3aed'))
            painter.drawText(QRectF(rect.left(), rsi_top - 22, 180, 20), Qt.AlignLeft | Qt.AlignVCenter, f'{rsi_key} · 30 / 70')
            for value in (0, 30, 70, 100):
                painter.setPen(QPen(QColor('#ddd6fe'), 1, Qt.DashLine))
                painter.drawLine(QPointF(rect.left(), rsi_y(value)), QPointF(rect.right(), rsi_y(value)))
                painter.setPen(QColor('#64748b'))
                painter.drawText(QRectF(rect.right() + 8, rsi_y(value) - 8, 82, 16), Qt.AlignLeft | Qt.AlignVCenter, str(value))
            draw_series(rsi_key, rsi_y)
        indices = sorted({round((len(rows) - 1) * i / min(4, len(rows) - 1)) for i in range(min(5, len(rows)))}) if len(rows) > 1 else [0]
        for index in indices:
            x = rect.left() + (index + .5) * step
            painter.setPen(QColor('#475569'))
            label_rect = QRectF(max(rect.left(), min(x - 48, rect.right() - 96)), rect.bottom() + 12, 96, 24)
            painter.drawText(label_rect, Qt.AlignCenter, trading_date(rows[index]['t']).strftime('%d/%m/%Y'))
        if self.hover_index is not None and self.hover_index < len(rows):
            x = rect.left() + (self.hover_index + .5) * step
            painter.setPen(QPen(QColor('#64748b'), 1, Qt.DashLine))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))


class PriceView(QWidget):
    def __init__(self, table_factory):
        super().__init__()
        self.raw_rows, self.series, self.symbol, self.stamp = [], [], '', ''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quote = QLabel('Chọn khoảng ngày để tải dữ liệu')
        self.quote.setTextFormat(Qt.PlainText)
        self.quote.setWordWrap(True)
        self.quote.setStyleSheet('font-size:12px; color:#475569; padding:2px 0;')
        toolbar = QHBoxLayout()
        self.timeframe = QComboBox()
        self.timeframe.addItem('Ngày (1D)', '1D')
        self.timeframe.addItem('Tuần (1W)', '1W')
        self.timeframe.currentIndexChanged.connect(self.refresh_series)
        self.timeframe.setToolTip('Đổi khung xem từ dữ liệu ngày đã tải, không gọi thêm Finhay.')
        self.legend = QLabel('Xanh: đóng cửa > mở cửa · Đỏ: đóng cửa < mở cửa · Xám: bằng nhau')
        self.legend.setStyleSheet('color:#475569; font-size:12px;')
        reset = QPushButton('Toàn bộ')
        reset.setToolTip('Hiển thị toàn bộ nến trong khoảng dữ liệu đã tải')
        self.show_table = QCheckBox('Hiện bảng dữ liệu')
        self.show_table.toggled.connect(self.toggle_table)
        self.chart_title = QLabel('Biểu đồ giá')
        self.chart_title.setStyleSheet('font-weight:600;')
        for widget in (self.chart_title, self.timeframe, reset):
            toolbar.addWidget(widget)
        toolbar.addStretch()
        toolbar.addWidget(self.show_table)
        self.show_details = QPushButton('Thông tin ›')
        self.show_details.setCheckable(True)
        self.show_details.setChecked(True)
        self.show_details.setToolTip('Ẩn/hiện bộ chọn ngày và chi tiết nến ở cạnh phải')
        self.indicator_button = QPushButton('Chỉ báo')
        toolbar.insertWidget(3, self.indicator_button)
        toolbar.addWidget(self.show_details)
        layout.addLayout(toolbar)
        self.hover_label = QLabel('Rê chuột lên nến để xem ngày, giá và khối lượng.')
        self.hover_label.setWordWrap(True)
        self.hover_label.setStyleSheet('color:#334155; font-size:12px;')
        self.chart = CandlestickChart()
        reset.clicked.connect(self.chart.reset_view)
        self.chart.hovered.connect(self.show_candle)
        self.chart.view_changed.connect(self.update_note)
        self.table = table_factory()
        self.table.setMinimumHeight(120)
        self.table.price_mode = True
        self.table.model.datetime_values = True
        self.table.model.column_order = ['t', 'o', 'h', 'l', 'c', 'v']
        self.table.model.column_labels = {'t': 'Ngày giao dịch', 'o': 'Mở cửa (VND)', 'h': 'Cao nhất (VND)', 'l': 'Thấp nhất (VND)', 'c': 'Đóng cửa (VND)', 'v': 'Khối lượng (cổ phiếu)'}
        self.table.query.setPlaceholderText('Lọc bảng dữ liệu giá…')
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.chart)
        self.splitter.addWidget(self.table)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        self.table.hide()
        content = QHBoxLayout()
        content.setSpacing(10)
        content.addWidget(self.splitter, 1)
        self.sidebar = QScrollArea()
        self.sidebar.setWidgetResizable(True)
        self.sidebar.setFrameShape(QFrame.NoFrame)
        self.sidebar.setFixedWidth(260)
        side = QWidget()
        self.side_layout = QVBoxLayout(side)
        self.side_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.side_layout.setContentsMargins(8, 0, 8, 0)
        self.query_layout = QVBoxLayout()
        self.side_layout.addLayout(self.query_layout)
        self.side_layout.addWidget(self.quote)
        heading = QLabel('CHI TIẾT NẾN')
        heading.setStyleSheet('font-weight:600; color:#475569; margin-top:8px;')
        self.side_layout.addWidget(heading)
        self.side_layout.addWidget(self.hover_label)
        fields = QFormLayout()
        fields.setHorizontalSpacing(12)
        self.candle_values = {}
        for key, title in [('open_change', 'So mở cửa'), ('previous_change', 'So nến trước'),
                           ('o', 'Mở cửa'), ('h', 'Cao nhất'), ('l', 'Thấp nhất'), ('c', 'Đóng cửa'), ('v', 'Khối lượng')]:
            value = QLabel('—')
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.candle_values[key] = value
            fields.addRow(title, value)
        self.candle_values['open_change'].setToolTip('(Đóng cửa − Mở cửa) / Mở cửa × 100%')
        self.candle_values['previous_change'].setToolTip('(Đóng cửa − Đóng cửa nến trước) / Đóng cửa nến trước × 100%; theo khung ngày/tuần đang xem')
        self.side_layout.addLayout(fields)
        self.indicator_values = QLabel('')
        self.indicator_values.setWordWrap(True)
        self.indicator_values.setTextFormat(Qt.PlainText)
        self.indicator_values.setStyleSheet('font-size:12px; color:#475569;')
        self.side_layout.addWidget(self.indicator_values)
        self.legend.setWordWrap(True)
        self.side_layout.addWidget(self.legend)
        self.side_layout.addStretch()
        self.sidebar.setWidget(side)
        content.addWidget(self.sidebar)
        self.show_details.toggled.connect(self.toggle_details)
        layout.addLayout(content, 1)
        self.note = QLabel('Cuộn để phóng/thu · Kéo ngang để xem các phiên trước · Bảng dữ liệu mặc định ẩn')
        self.note.setWordWrap(True)
        self.note.setStyleSheet('color:#64748b; font-size:12px;')
        layout.addWidget(self.note)
        self.create_indicator_controls()

    def create_indicator_controls(self):
        self.indicator_dialog = QDialog(self)
        self.indicator_dialog.setWindowTitle('Chỉ báo kỹ thuật')
        self.indicator_dialog.setMinimumWidth(380)
        layout = QVBoxLayout(self.indicator_dialog)
        hint = QLabel('Tính từ giá đóng cửa của khung ngày/tuần đang xem.\nBật/tắt và chỉnh tham số để cập nhật ngay trên chart.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        self.indicator_checks, self.indicator_periods = {}, {}
        for key, title, default in [('ma1', 'MA nhanh (SMA)', 20), ('ma2', 'MA chậm (SMA)', 50),
                                    ('bb', 'Bollinger Bands', 20), ('rsi', 'RSI (Wilder)', 14)]:
            check = QCheckBox(title)
            period = StepSpinBox()
            period.setRange(2, 500)
            period.setValue(default)
            period.setSuffix(' nến')
            self.indicator_checks[key], self.indicator_periods[key] = check, period
            form.addRow(check, period)
            check.toggled.connect(self.refresh_indicators)
            period.valueChanged.connect(self.refresh_indicators)
        self.bb_deviation = QDoubleSpinBox()
        self.bb_deviation.setRange(.1, 5)
        self.bb_deviation.setSingleStep(.1)
        self.bb_deviation.setValue(2)
        self.bb_deviation.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        form.addRow('Độ lệch chuẩn BB (σ)', self.bb_deviation)
        self.bb_deviation.valueChanged.connect(self.refresh_indicators)
        layout.addLayout(form)
        note = QLabel('MA: trung bình đơn giản · BB: SMA ± kσ (σ tổng thể).\nRSI: ngưỡng tham chiếu 30/70. Chưa đủ nến thì để trống; dữ liệu thiếu sẽ bắt đầu tính lại. Chỉ dùng dữ liệu đã tải, không gọi thêm Finhay.')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText('Đóng')
        buttons.rejected.connect(self.indicator_dialog.hide)
        layout.addWidget(buttons)
        self.indicator_button.clicked.connect(self.open_indicator_controls)
        self.indicator_data = {}
        self.active_candle = None

    def open_indicator_controls(self):
        self.indicator_dialog.show()
        self.indicator_dialog.raise_()
        self.indicator_dialog.activateWindow()

    def refresh_indicators(self, *_):
        enabled = lambda key: self.indicator_checks[key].isChecked()
        period = lambda key: self.indicator_periods[key].value()
        ma_periods = list(dict.fromkeys(period(key) for key in ('ma1', 'ma2') if enabled(key)))
        values = calculate_indicators(self.series, ma_periods, period('bb') if enabled('bb') else None,
                                      self.bb_deviation.value(), period('rsi') if enabled('rsi') else None)
        self.indicator_data = {row['t']: {key: series[i] for key, series in values.items()}
                               for i, row in enumerate(self.series)}
        self.chart.set_indicators(self.series, values)
        count = sum(enabled(key) for key in self.indicator_checks)
        self.indicator_button.setText(f'Chỉ báo ({count})' if count else 'Chỉ báo')
        if self.active_candle is not None:
            self.show_candle(self.active_candle)

    def set_query_controls(self, from_date, to_date, fetch_button):
        form = QFormLayout()
        form.addRow('Từ ngày', from_date)
        form.addRow('Đến ngày', to_date)
        self.query_layout.addLayout(form)
        self.query_layout.addWidget(fetch_button)

    def toggle_details(self, visible):
        self.sidebar.setVisible(visible)
        self.show_details.setText('Thông tin ›' if visible else '‹ Thông tin')

    def set_result(self, rows, quote, symbol, stamp):
        self.raw_rows = [dict(row) for row in rows]
        self.symbol, self.stamp = symbol, stamp
        price, change = number(quote.get('price')), number(quote.get('change_percent'))
        price_text = f'{price:,.0f} VND' if price is not None else 'Chưa có giá'
        change_text = f'{change:+.2f}%' if change is not None else '—'
        updated = quote.get('updated_at')
        try:
            updated = datetime.fromisoformat(updated.replace('Z', '+00:00')).astimezone(VN).strftime('%H:%M %d/%m/%Y')
        except (AttributeError, ValueError):
            updated = 'chưa rõ thời điểm'
        self.chart_title.setText(f'{symbol} · {price_text}')
        self.quote.setText(f'Giá hiện tại: {price_text}\nThay đổi: {change_text}\nCập nhật {updated}')
        self.quote.setToolTip(stamp)
        self.refresh_series()

    def refresh_series(self, *_):
        frame = self.timeframe.currentData()
        self.series = price_series(self.raw_rows, frame)
        self.previous_closes = {row['t']: self.series[i - 1]['c'] if i else None
                                for i, row in enumerate(self.series)}
        self.active_candle = None
        self.refresh_indicators()
        self.table.model.column_labels['t'] = 'Tuần từ (thứ Hai)' if frame == '1W' else 'Ngày giao dịch'
        self.table.model.set_rows(self.series)
        self.table.export_metadata = {'ma': self.symbol, 'khung_nen': frame, 'lay_du_lieu_luc': self.stamp}
        for column, width in enumerate((145, 135, 135, 135, 135, 165)):
            self.table.view.setColumnWidth(column, width)
        self.chart.set_rows(self.series)

    def toggle_table(self, visible):
        self.chart.setMinimumHeight(160 if visible else 240)
        self.table.setVisible(visible)
        if visible:
            QTimer.singleShot(0, self.balance_splitter)

    def balance_splitter(self):
        if self.show_table.isChecked():
            height = self.splitter.height()
            self.splitter.setSizes([int(height * .75), int(height * .25)])

    def show_candle(self, row):
        self.active_candle = row
        indicator_values = self.indicator_data.get(row['t'], {}) if row else {}
        self.indicator_values.setText('\n'.join(f'{key}: {value:,.2f}' if value is not None else f'{key}: — (chưa đủ dữ liệu)'
                                               for key, value in indicator_values.items()))
        if row is None:
            self.hover_label.setText('Không có nến OHLC hợp lệ trong khoảng đã tải.')
            for value in self.candle_values.values():
                value.setText('—')
                value.setStyleSheet('')
            return
        date = trading_date(row['t']).strftime('%d/%m/%Y')
        prefix = 'Tuần từ' if self.timeframe.currentData() == '1W' else 'Ngày'
        self.hover_label.setText(f'{prefix} {date} · Giá: VND')
        for key in ('o', 'h', 'l', 'c', 'v'):
            self.candle_values[key].setText(f'{row[key]:,.0f}' if row.get(key) is not None else '—')
        for key, base in [('open_change', row['o']), ('previous_change', self.previous_closes.get(row['t']))]:
            change = candle_change(row['c'], base)
            value = self.candle_values[key]
            value.setText(f'{change:+.2f}%' if change is not None else '—')
            color = FLAT if change is None or change == 0 else (GREEN if change > 0 else RED)
            value.setStyleSheet(f'color:{color}; font-weight:600;')

    def update_note(self, visible, total):
        skipped = len(self.series) - total
        text = f'Đang xem {visible}/{total} nến · Cuộn để phóng/thu · Kéo ngang để xem các phiên trước'
        if skipped:
            text += f' · {skipped} kỳ thiếu/sai OHLC không vẽ nến'
        if self.timeframe.currentData() == '1W':
            text += ' · Tuần gộp từ các phiên trong khoảng đã chọn; tuần đầu/cuối có thể chưa đủ phiên.'
        self.note.setText(text)
