"""
Elektronik Harp Arayüz Sistemi — Entry Point.

Kullanım:
    python -m ehapp
    python run.py
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from ehapp.main_window import MainWindow
from ehcore.registry import discover_plugins


def main() -> None:
    plugin_dir = Path(__file__).resolve().parents[2] / "plugins"
    discover_plugins(plugin_dir)

    app = QApplication(sys.argv)
    app.setApplicationName("Elektronik Harp Arayüz Sistemi")
    app.setOrganizationName("TEKNOFEST")

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
