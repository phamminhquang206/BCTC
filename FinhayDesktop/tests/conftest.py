import sys
import os
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='session', autouse=True)
def qt_application_session():
    # Qt supports one application per process. Retain it across GUI test modules
    # rather than repeatedly destroying/recreating QApplication at fixture exit.
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def dispose_test_windows(qt_application_session):
    yield
    from PySide6.QtCore import QCoreApplication, QEvent
    for widget in qt_application_session.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
