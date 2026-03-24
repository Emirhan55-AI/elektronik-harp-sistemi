"""
Elektronik Harp Arayuz Sistemi - Entry Point.

Kullanim:
    python -m ehapp
    python run.py
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ehapp.main_window import MainWindow
from ehapp.strings import tr
from ehcore.registry import discover_plugins_report


def main() -> None:
    plugin_dir = Path(__file__).resolve().parents[2] / "plugins"
    plugin_report = discover_plugins_report(plugin_dir)

    app = QApplication(sys.argv)
    app.setApplicationName(tr.APP_TITLE)
    app.setOrganizationName(tr.APP_ORGANIZATION)
    app._plugin_discovery_report = plugin_report

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
