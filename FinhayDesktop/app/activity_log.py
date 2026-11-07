"""Bounded detail log and a compact, local-time source label."""
import re
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QPlainTextEdit


def source_summary(stamp):
    timestamps = re.findall(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', stamp or '')
    dates = []
    for value in timestamps:
        try:
            dates.append(datetime.fromisoformat(value.replace('Z', '+00:00')))
        except ValueError:
            continue
    if not dates:
        return 'Nguồn: Finhay'
    latest = max(dates).astimezone(timezone(timedelta(hours=7)))
    return 'Nguồn: Finhay · Lấy lúc ' + latest.strftime('%H:%M %d/%m/%Y')


class ActivityLog(QPlainTextEdit):
    message_added = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(300)
        self.setPlaceholderText('Nhật ký xử lý sẽ xuất hiện tại đây…')

    @Slot(str)
    def append(self, message):
        message = str(message)
        self.appendPlainText(message)
        summary = next((line.strip() for line in message.splitlines() if line.strip()), '')
        self.message_added.emit(summary)
