"""
EventFeedPanel - operasyon icin kisa olay akisi.
"""

from __future__ import annotations

import time

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from app.strings import tr
from app.theme.tokens import COLORS


class EventFeedPanel(QWidget):
    """Kisa olay akisi listesi."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("EventFeedRoot")
        self._max_items = 200
        self._event_count = 0
        self._last_message = ""
        self._last_level = "info"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._list = QListWidget()
        self._list.setObjectName("EventFeedList")
        layout.addWidget(self._list)

    def add_event(self, message: str, level: str = "info") -> None:
        timestamp = time.strftime("%H:%M:%S")
        item = QListWidgetItem(f"{timestamp}  {message}")
        item.setForeground(QBrush(QColor(self._level_color(level))))
        self._list.insertItem(0, item)
        self._event_count += 1
        self._last_message = message
        self._last_level = level
        while self._list.count() > self._max_items:
            self._list.takeItem(self._list.count() - 1)

    def clear(self) -> None:
        self._list.clear()
        self._event_count = 0
        self._last_message = ""
        self._last_level = "info"

    def summary(self) -> dict[str, str | int]:
        return {
            "count": self._event_count,
            "last_message": self._last_message or tr.EVENT_NONE,
            "last_level": self._translate_level(self._last_level),
        }

    @staticmethod
    def _level_color(level: str) -> str:
        return {
            "error": COLORS["error"],
            "warning": COLORS["warning"],
            "success": COLORS["success"],
            "info": COLORS["text_primary"],
            "debug": COLORS["text_secondary"],
        }.get(level, COLORS["text_primary"])

    @staticmethod
    def _translate_level(level: str) -> str:
        return {
            "error": tr.EVENT_LEVEL_ERROR,
            "warning": tr.EVENT_LEVEL_WARNING,
            "success": tr.EVENT_LEVEL_SUCCESS,
            "info": tr.EVENT_LEVEL_INFO,
            "debug": tr.EVENT_LEVEL_DEBUG,
        }.get(level, tr.EVENT_LEVEL_INFO)


