"""
Elektronik Harp Arayüz Sistemi — Entry Point.

Kullanım:
    python -m ehapp
    python run.py
"""

import sys
from PySide6.QtWidgets import QApplication
from ehapp.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Elektronik Harp Arayüz Sistemi")
    app.setOrganizationName("TEKNOFEST")

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
