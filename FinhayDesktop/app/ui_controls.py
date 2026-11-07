"""Explicit light palette and visible, platform-independent spin controls."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QAbstractSpinBox, QSpinBox, QToolButton


def set_light_palette(app):
    palette = QPalette()
    colors = {
        QPalette.Window: '#f5f7fb', QPalette.WindowText: '#172b4d',
        QPalette.Base: '#ffffff', QPalette.AlternateBase: '#f1f5f9',
        QPalette.Text: '#172b4d', QPalette.Button: '#ffffff',
        QPalette.ButtonText: '#172b4d', QPalette.Highlight: '#dbeafe',
        QPalette.HighlightedText: '#0f172a', QPalette.Link: '#1d4ed8',
        QPalette.PlaceholderText: '#64748b', QPalette.ToolTipBase: '#ffffff',
        QPalette.ToolTipText: '#172b4d',
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        palette.setColor(QPalette.Disabled, role, QColor('#64748b'))
    app.setPalette(palette)


class StepSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setKeyboardTracking(False)
        self.setMinimumWidth(116)
        self.setMinimumHeight(36)
        self.setStyleSheet('QSpinBox { padding:0; } QSpinBox QLineEdit { padding:0; border:0; background:transparent; color:#172b4d; }')
        self.decrease_button = QToolButton(self)
        self.increase_button = QToolButton(self)
        for button, label, action, name in (
            (self.decrease_button, '−', self.stepDown, 'Giảm giá trị'),
            (self.increase_button, '+', self.stepUp, 'Tăng giá trị'),
        ):
            button.setObjectName('spinStepButton')
            button.setText(label)
            button.setAccessibleName(name)
            button.setToolTip(name)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(350)
            button.setAutoRepeatInterval(90)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet('QToolButton { color:#172b4d; background:#e2e8f0; border:0; border-radius:3px; font-size:16px; font-weight:700; padding:0; } QToolButton:hover { background:#cbd5e1; } QToolButton:pressed { background:#93c5fd; } QToolButton:disabled { color:#94a3b8; background:#f1f5f9; }')
            button.clicked.connect(action)
        self.valueChanged.connect(self.refresh_buttons)
        self.refresh_buttons()

    def setRange(self, minimum, maximum):
        super().setRange(minimum, maximum)
        self.refresh_buttons()

    def refresh_buttons(self, *_):
        if hasattr(self, 'increase_button'):
            self.decrease_button.setEnabled(self.value() > self.minimum() and not self.isReadOnly())
            self.increase_button.setEnabled(self.value() < self.maximum() and not self.isReadOnly())
            self.position_children()

    def position_children(self):
        if hasattr(self, 'increase_button'):
            # Font metrics vary with Windows display scaling and Qt's platform.
            digits = str(max(abs(self.minimum()), abs(self.maximum())))
            minimum = max(116, self.lineEdit().fontMetrics().horizontalAdvance(digits) + 82)
            if self.minimumWidth() != minimum:
                self.setMinimumWidth(minimum)
            self.lineEdit().setGeometry(8, 4, max(36, self.width() - 70), max(24, self.height() - 8))
            self.decrease_button.setGeometry(self.width() - 56, 4, 24, max(24, self.height() - 8))
            self.increase_button.setGeometry(self.width() - 29, 4, 24, max(24, self.height() - 8))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_children()

    def changeEvent(self, event):
        super().changeEvent(event)
        self.position_children()
