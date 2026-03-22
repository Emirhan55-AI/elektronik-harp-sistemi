"""
LogPanel — Log / durum / doğrulama mesajları paneli.

Monospace font, renkli prefix'ler, scroll-to-bottom.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat
from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QTextEdit, QLabel, QHBoxLayout, QPushButton,
)

from ehapp.theme.tokens import COLORS, FONTS, SIZES
from ehapp.strings.tr import LOG_TITLE, LOG_INFO, LOG_WARNING, LOG_ERROR, LOG_DEBUG


class LogPanel(QWidget):
    """Log/durum paneli."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Başlık çubuğu
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 2, 8, 2)

        # Başlık artık DockWidget tarafından sağlandığı için silindi.
        header_layout.addStretch()

        clear_btn = QPushButton("Temizle")
        clear_btn.setFixedHeight(22)
        clear_btn.setStyleSheet(
            f"font-size: {FONTS['size_xs']}px; "
            f"padding: 2px 8px;"
        )
        clear_btn.clicked.connect(self.clear)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Log alanı
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont(FONTS["family_mono"], FONTS["size_sm"]))
        self._text.setStyleSheet(
            f"background-color: {COLORS['bg_input']}; "
            f"border: none; "
            f"padding: 4px;"
        )
        layout.addWidget(self._text)

    def log(self, message: str, level: str = "info") -> None:
        """Mesajı log'a yaz."""
        timestamp = time.strftime("%H:%M:%S")
        prefix_map = {
            "info": (LOG_INFO, COLORS["text_primary"]),
            "warning": (LOG_WARNING, COLORS["warning"]),
            "error": (LOG_ERROR, COLORS["error"]),
            "debug": (LOG_DEBUG, COLORS["text_secondary"]),
            "success": (LOG_INFO, COLORS["success"]),
        }
        prefix, color = prefix_map.get(level, (LOG_INFO, COLORS["text_primary"]))

        html = (
            f'<span style="color:{COLORS["text_secondary"]}">{timestamp}</span> '
            f'<span style="color:{color}; font-weight:bold">{prefix}</span> '
            f'<span style="color:{COLORS["text_primary"]}">{message}</span>'
        )
        self._text.append(html)

        # Auto-scroll
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

    def clear(self) -> None:
        """Log'u temizle."""
        self._text.clear()
