import os
import time
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal
from PySide6.QtTest import QSignalSpy
from app.activity_log import ActivityLog, source_summary
from app.gui import MainWindow


def test_source_summary_uses_latest_time_and_vietnam_day():
    stamp = 'Hồ sơ: 2026-11-06T16:59:00.123+00:00\nChỉ số: 2026-11-06T17:01:00+00:00'
    assert source_summary(stamp) == 'Nguồn: Finhay · Lấy lúc 00:01 07/11/2026'
    assert source_summary('') == 'Nguồn: Finhay'


def test_hidden_log_retains_messages_and_can_be_opened(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path)
    window.show()
    app.processEvents()
    assert not window.log_dock.isVisible()
    window.log.append('FPT: đã tải tổng quan.\nChi tiết thời gian')
    assert window.statusBar().currentMessage() == 'FPT: đã tải tổng quan.'
    window.log_toggle.click()
    app.processEvents()
    assert window.log_dock.isVisible()
    assert 'Chi tiết thời gian' in window.log.toPlainText()
    window.log_toggle.click()
    app.processEvents()
    assert not window.log_dock.isVisible()
    assert 'Chi tiết thời gian' in window.log.toPlainText()
    window.close()


def test_log_is_bounded_and_literal_text():
    app = QApplication.instance() or QApplication([])
    log = ActivityLog()
    for i in range(350):
        log.append(f'Dòng {i}')
    assert log.blockCount() == 300
    assert log.toPlainText().splitlines()[0] == 'Dòng 50'
    log.append('<b>Giữ nguyên nội dung</b>')
    assert '<b>Giữ nguyên nội dung</b>' in log.toPlainText()
    log.close()


def test_background_worker_can_update_hidden_log():
    class Emitter(QThread):
        message = Signal(str)

        def run(self):
            self.message.emit('Đã lấy dữ liệu trong luồng nền')

    log = ActivityLog()
    worker = Emitter()
    worker.message.connect(log.append)
    spy = QSignalSpy(log.message_added)
    worker.start()
    deadline = time.monotonic() + 2
    while spy.count() == 0 and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.01)
    assert worker.wait(2000)
    assert spy.count() == 1
    assert 'luồng nền' in log.toPlainText()
    log.close()
