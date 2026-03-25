"""Main window icin hazir dock yerlesim presetleri."""

from __future__ import annotations

from dataclasses import dataclass

from app.strings import tr


@dataclass(frozen=True, slots=True)
class LayoutPreset:
    preset_id: str
    display_name: str
    ui_mode: str
    dock_visibility: dict[str, bool]


LAYOUT_PRESETS: dict[str, LayoutPreset] = {
    "design": LayoutPreset(
        preset_id="design",
        display_name=tr.LAYOUT_PRESET_DESIGN,
        ui_mode="design",
        dock_visibility={
            "palette": True,
            "properties": False,
            "log": True,
            "summary": False,
            "spectrum": False,
            "waterfall": False,
            "detections": False,
        },
    ),
    "operation": LayoutPreset(
        preset_id="operation",
        display_name=tr.LAYOUT_PRESET_OPERATION,
        ui_mode="operation",
        dock_visibility={
            "palette": False,
            "properties": False,
            "log": False,
            "summary": True,
            "spectrum": True,
            "waterfall": True,
            "detections": True,
        },
    ),
    "analysis": LayoutPreset(
        preset_id="analysis",
        display_name=tr.LAYOUT_PRESET_ANALYSIS,
        ui_mode="design",
        dock_visibility={
            "palette": True,
            "properties": True,
            "log": True,
            "summary": True,
            "spectrum": True,
            "waterfall": True,
            "detections": True,
        },
    ),
}


