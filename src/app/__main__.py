"""Elektronik Harp Arayuz Sistemi giris noktasi."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.strings import tr
from ehplatform.registry import discover_plugins_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke dogrulamasi calistir ve cik.",
    )
    args, qt_args = parser.parse_known_args(list(argv) if argv is not None else sys.argv[1:])
    if args.smoke:
        from app.smoke import main as smoke_main

        return smoke_main()

    plugin_dir = Path(__file__).resolve().parents[2] / "plugins"
    plugin_report = discover_plugins_report(plugin_dir)

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName(tr.APP_TITLE)
    app.setOrganizationName(tr.APP_ORGANIZATION)
    app._plugin_discovery_report = plugin_report

    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
