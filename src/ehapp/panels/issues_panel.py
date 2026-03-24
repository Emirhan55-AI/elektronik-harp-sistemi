"""
IssuesPanel - validation ve runtime sorunlarini listeleyen panel.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ehapp.strings import tr
from ehapp.theme.tokens import COLORS


class IssuesPanel(QWidget):
    """Sistem issue listesini tek noktadan sunar."""

    issue_activated = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._summary = QLabel(tr.ISSUES_NONE)
        self._summary.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self._summary)

        self._list = QListWidget()
        self._list.setObjectName("IssuesList")
        self._list.itemActivated.connect(self._emit_issue)
        self._list.itemClicked.connect(self._emit_issue)
        layout.addWidget(self._list)

    def set_issues(self, issues) -> None:
        self._list.clear()
        if not issues:
            self._summary.setText(tr.ISSUES_NONE)
            placeholder = QListWidgetItem(tr.ISSUES_NONE_DETAIL)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(QBrush(QColor(COLORS["text_secondary"])))
            self._list.addItem(placeholder)
            return

        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity != "error")
        preview_count = sum(1 for issue in issues if issue.source == "preview")
        runtime_count = len(issues) - preview_count
        self._summary.setText(
            tr.ISSUES_SUMMARY.format(
                errors=error_count,
                warnings=warning_count,
                runtime=runtime_count,
                preview=preview_count,
            )
        )

        for issue in issues:
            prefix = tr.ISSUE_LEVEL_ERROR if issue.severity == "error" else tr.ISSUE_LEVEL_WARNING
            source = {
                "runtime": tr.ISSUE_SOURCE_RUNTIME,
                "validation": tr.ISSUE_SOURCE_VALIDATION,
                "preview": tr.ISSUE_SOURCE_PREVIEW,
            }.get(issue.source, tr.ISSUE_SOURCE_GENERIC)
            label = f"{prefix} - {source}: {issue.message}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, issue.node_id)
            color = COLORS["error"] if issue.severity == "error" else COLORS["warning"]
            item.setForeground(QBrush(QColor(color)))
            if issue.node_id:
                item.setToolTip(
                    tr.ISSUE_TOOLTIP_NODE.format(message=issue.message, node_id=issue.node_id)
                )
            else:
                item.setToolTip(issue.message)
            self._list.addItem(item)

    def _emit_issue(self, item: QListWidgetItem) -> None:
        node_id = item.data(Qt.ItemDataRole.UserRole) or ""
        if node_id:
            self.issue_activated.emit(node_id)
