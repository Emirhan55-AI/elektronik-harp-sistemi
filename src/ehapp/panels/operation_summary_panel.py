"""
OperationSummaryPanel - operasyon ozeti.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QVBoxLayout, QWidget

from ehapp.strings import tr
from ehapp.theme.tokens import COLORS


class OperationSummaryPanel(QWidget):
    """Pipeline ve tespitler icin ust duzey kisa durum ozeti."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self._pipeline_card, pipeline_form = self._create_card(tr.SECTION_PIPELINE)
        self._runtime_card, runtime_form = self._create_card(tr.SECTION_RUNTIME)
        self._events_card, events_form = self._create_card(tr.SECTION_EVENTS)

        self._pipeline_state = self._make_value_label(tr.STATUS_READY, state="idle")
        self._issue_count = self._make_value_label("0")
        self._issue_breakdown = self._make_value_label(
            tr.SUMMARY_ISSUE_BREAKDOWN_TEXT.format(errors=0, warnings=0)
        )
        self._active_nodes = self._make_value_label("0 / 0")
        self._avg_latency = self._make_value_label("0.0 ms")
        self._slowest_node = self._make_value_label(tr.COMMON_PLACEHOLDER)
        self._source_label = self._make_value_label(tr.COMMON_PLACEHOLDER)
        self._variable_count = self._make_value_label("0")
        self._ui_mode = self._make_value_label(tr.COMMON_PLACEHOLDER)
        self._layout_name = self._make_value_label(tr.COMMON_PLACEHOLDER)
        self._recipe_name = self._make_value_label(tr.SUMMARY_RECIPE_NONE)
        self._plugin_status = self._make_value_label(tr.SUMMARY_PLUGIN_NONE)
        self._event_count = self._make_value_label(
            tr.SUMMARY_EVENT_BREAKDOWN.format(count=0, level=tr.EVENT_LEVEL_INFO)
        )
        self._last_event = self._make_value_label(tr.EVENT_NONE)
        self._confirmed_count = self._make_value_label("0")
        self._active_tracks = self._make_value_label("0")
        self._last_target = self._make_value_label(tr.COMMON_PLACEHOLDER)

        pipeline_form.addRow(tr.SUMMARY_PIPELINE, self._pipeline_state)
        pipeline_form.addRow(tr.SUMMARY_ISSUES, self._issue_count)
        pipeline_form.addRow(tr.SUMMARY_ISSUE_BREAKDOWN, self._issue_breakdown)

        runtime_form.addRow(tr.SUMMARY_ACTIVE_NODES, self._active_nodes)
        runtime_form.addRow(tr.SUMMARY_AVG_LATENCY, self._avg_latency)
        runtime_form.addRow(tr.SUMMARY_SLOWEST_NODE, self._slowest_node)
        runtime_form.addRow(tr.SUMMARY_SOURCE, self._source_label)
        runtime_form.addRow(tr.SUMMARY_VARIABLES, self._variable_count)
        runtime_form.addRow(tr.SUMMARY_UI_MODE, self._ui_mode)
        runtime_form.addRow(tr.SUMMARY_LAYOUT, self._layout_name)
        runtime_form.addRow(tr.SUMMARY_RECIPE, self._recipe_name)
        runtime_form.addRow(tr.SUMMARY_PLUGINS, self._plugin_status)

        events_form.addRow(tr.SUMMARY_EVENTS, self._event_count)
        events_form.addRow(tr.SUMMARY_LAST_EVENT, self._last_event)
        events_form.addRow(tr.SUMMARY_CONFIRMED_TARGETS, self._confirmed_count)
        events_form.addRow(tr.SUMMARY_ACTIVE_TRACKS, self._active_tracks)
        events_form.addRow(tr.SUMMARY_LAST_TARGET, self._last_target)

        layout.addWidget(self._pipeline_card)
        layout.addWidget(self._runtime_card)
        layout.addWidget(self._events_card)
        layout.addStretch(1)

    def _create_card(self, title: str) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("InspectorCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(7)
        layout.addLayout(form)
        return card, form

    def _make_value_label(self, text: str, *, state: str = "normal") -> QLabel:
        label = QLabel(text)
        label.setObjectName("SummaryValue")
        label.setWordWrap(True)
        self._apply_value_state(label, state)
        return label

    def _apply_value_state(self, label: QLabel, state: str) -> None:
        color = {
            "idle": COLORS["text_primary"],
            "running": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["error"],
            "muted": COLORS["text_secondary"],
            "accent": COLORS["accent_primary"],
        }.get(state, COLORS["text_primary"])
        label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def set_pipeline_state(self, state: str) -> None:
        self._pipeline_state.setText(state)
        normalized = state.casefold()
        if normalized == tr.SUMMARY_PIPELINE_RUNNING.casefold():
            self._apply_value_state(self._pipeline_state, "running")
        elif normalized == tr.SUMMARY_PIPELINE_ERROR.casefold():
            self._apply_value_state(self._pipeline_state, "error")
        else:
            self._apply_value_state(self._pipeline_state, "idle")

    def set_issue_count(self, count: int) -> None:
        self._issue_count.setText(str(count))
        if count <= 0:
            self._apply_value_state(self._issue_count, "running")
        else:
            self._apply_value_state(self._issue_count, "warning")

    def set_issue_breakdown(self, error_count: int, warning_count: int) -> None:
        self._issue_breakdown.setText(
            tr.SUMMARY_ISSUE_BREAKDOWN_TEXT.format(errors=error_count, warnings=warning_count)
        )
        if error_count > 0:
            self._apply_value_state(self._issue_breakdown, "error")
        elif warning_count > 0:
            self._apply_value_state(self._issue_breakdown, "warning")
        else:
            self._apply_value_state(self._issue_breakdown, "running")

    def set_runtime_health(
        self,
        *,
        active_nodes: int,
        total_nodes: int,
        avg_latency_ms: float,
        slowest_node: str,
        source_label: str,
        variable_count: int,
        ui_mode_label: str,
        layout_label: str,
        recipe_label: str,
        plugin_label: str,
    ) -> None:
        self._active_nodes.setText(f"{active_nodes} / {total_nodes}")
        self._avg_latency.setText(f"{avg_latency_ms:.1f} ms")
        self._slowest_node.setText(slowest_node or tr.COMMON_PLACEHOLDER)
        self._source_label.setText(source_label or tr.COMMON_PLACEHOLDER)
        self._variable_count.setText(str(variable_count))
        self._ui_mode.setText(ui_mode_label or tr.COMMON_PLACEHOLDER)
        self._layout_name.setText(layout_label or tr.COMMON_PLACEHOLDER)
        self._recipe_name.setText(recipe_label or tr.SUMMARY_RECIPE_NONE)
        self._plugin_status.setText(plugin_label or tr.SUMMARY_PLUGIN_NONE)

        self._apply_value_state(
            self._active_nodes,
            "running" if active_nodes > 0 else "muted",
        )
        self._apply_value_state(
            self._avg_latency,
            "warning" if avg_latency_ms >= 50.0 else "accent",
        )
        self._apply_value_state(
            self._slowest_node,
            "muted" if slowest_node in {"", tr.COMMON_PLACEHOLDER} else "normal",
        )
        self._apply_value_state(
            self._source_label,
            "muted" if source_label in {"", tr.COMMON_PLACEHOLDER} else "normal",
        )
        self._apply_value_state(
            self._variable_count,
            "accent" if variable_count > 0 else "muted",
        )
        self._apply_value_state(
            self._ui_mode,
            "accent" if ui_mode_label not in {"", tr.COMMON_PLACEHOLDER} else "muted",
        )
        self._apply_value_state(
            self._layout_name,
            "accent" if layout_label not in {"", tr.COMMON_PLACEHOLDER} else "muted",
        )
        self._apply_value_state(
            self._recipe_name,
            "muted" if recipe_label in {"", tr.COMMON_PLACEHOLDER, tr.SUMMARY_RECIPE_NONE} else "accent",
        )
        self._apply_value_state(
            self._plugin_status,
            "muted"
            if not plugin_label or plugin_label == tr.SUMMARY_PLUGIN_NONE
            else ("warning" if "hata" in (plugin_label or "").casefold() else "accent"),
        )

    def set_event_summary(self, count: int, last_event: str, last_level: str) -> None:
        self._event_count.setText(tr.SUMMARY_EVENT_BREAKDOWN.format(count=count, level=last_level))
        self._last_event.setText(last_event or tr.EVENT_NONE)

        self._apply_value_state(self._event_count, "accent" if count > 0 else "muted")
        event_level = (last_level or "").casefold()
        if event_level == tr.EVENT_LEVEL_ERROR.casefold():
            self._apply_value_state(self._last_event, "error")
        elif event_level == tr.EVENT_LEVEL_WARNING.casefold():
            self._apply_value_state(self._last_event, "warning")
        else:
            self._apply_value_state(self._last_event, "normal")

    def set_target_summary(self, confirmed_count: int, active_tracks: int, last_target: str) -> None:
        self._confirmed_count.setText(str(confirmed_count))
        self._active_tracks.setText(str(active_tracks))
        self._last_target.setText(last_target or tr.COMMON_PLACEHOLDER)

        self._apply_value_state(self._confirmed_count, "accent" if confirmed_count > 0 else "muted")
        self._apply_value_state(self._active_tracks, "running" if active_tracks > 0 else "muted")
        self._apply_value_state(
            self._last_target,
            "normal" if last_target and last_target != tr.COMMON_PLACEHOLDER else "muted",
        )

    def reset(self) -> None:
        self.set_pipeline_state(tr.STATUS_READY)
        self.set_issue_count(0)
        self.set_issue_breakdown(0, 0)
        self.set_runtime_health(
            active_nodes=0,
            total_nodes=0,
            avg_latency_ms=0.0,
            slowest_node=tr.COMMON_PLACEHOLDER,
            source_label=tr.COMMON_PLACEHOLDER,
            variable_count=0,
            ui_mode_label=tr.COMMON_PLACEHOLDER,
            layout_label=tr.COMMON_PLACEHOLDER,
            recipe_label=tr.SUMMARY_RECIPE_NONE,
            plugin_label=tr.SUMMARY_PLUGIN_NONE,
        )
        self.set_event_summary(0, tr.EVENT_NONE, tr.EVENT_LEVEL_INFO)
        self.set_target_summary(0, 0, tr.COMMON_PLACEHOLDER)
