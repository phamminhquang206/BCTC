import argparse
import os
import sys
from pathlib import Path

# Embeddable Python isolates sys.path; make the source tree importable explicitly.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description='Finhay Desktop')
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'FinhayDesktop')
    parser.add_argument('--smoke', type=Path, help='Offscreen GUI smoke test; save screenshot and exit')
    args = parser.parse_args()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from app.gui import MainWindow, STYLE
    app = QApplication(sys.argv[:1])
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    window = MainWindow(args.data_dir)
    window.show()
    if args.smoke:
        def capture():
            args.smoke.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.smoke))
            window.close()
            app.quit()
        QTimer.singleShot(500, capture)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
