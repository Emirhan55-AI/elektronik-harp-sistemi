"""
LogPanel - log, durum ve dogrulama mesajlari paneli.
"""

from __future__ import annotations

import time

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from app.strings import tr
from app.theme.tokens import COLORS, FONTS


class LogPanel(QWidget):
    """Log/durum paneli."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("LogPanelRoot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._text = QTextEdit()
        self._text.setObjectName("LogOutput")
        self._text.setReadOnly(True)
        self._text.setFont(QFont(FONTS["family_mono"], max(1, int(FONTS["size_sm"]))))
        self._text.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; "
            "border: none; "
            "padding: 4px;"
        )
        layout.addWidget(self._text)

    def log(self, message: str, level: str = "info") -> None:
        timestamp = time.strftime("%H:%M:%S")
        if message.lstrip().startswith("[TESP"):
            html = (
                f'<span style="color:{COLORS["text_secondary"]}">{timestamp}</span> '
                f'<span style="color:{COLORS["success"]}; font-weight:bold">{message}</span>'
            )
            self._text.append(html)
            scrollbar = self._text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            return

        prefix_map = {
            "info": (tr.LOG_INFO, COLORS["text_primary"]),
            "warning": (tr.LOG_WARNING, COLORS["warning"]),
            "error": (tr.LOG_ERROR, COLORS["error"]),
            "debug": (tr.LOG_DEBUG, COLORS["text_secondary"]),
            "success": (tr.LOG_INFO, COLORS["success"]),
        }
        prefix, color = prefix_map.get(level, (tr.LOG_INFO, COLORS["text_primary"]))

        html = (
            f'<span style="color:{COLORS["text_secondary"]}">{timestamp}</span> '
            f'<span style="color:{color}; font-weight:bold">{prefix}</span> '
            f'<span style="color:{COLORS["text_primary"]}">{message}</span>'
        )
        self._text.append(html)

        scrollbar = self._text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def log_info(self, message: str) -> None:
        self.log(message, "info")

    def log_warning(self, message: str) -> None:
        self.log(message, "warning")

    def log_error(self, message: str) -> None:
        self.log(message, "error")

    def log_success(self, message: str) -> None:
        self.log(message, "success")

    def log_debug(self, message: str) -> None:
        self.log(message, "debug")

    def clear(self) -> None:
        self._text.clear()


