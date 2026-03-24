"""Hazir akis tarifleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ehapp.strings import tr


@dataclass(frozen=True, slots=True)
class FlowRecipeNode:
    node_type_id: str
    position: tuple[float, float]
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FlowRecipeEdge:
    source_index: int
    source_port: str
    target_index: int
    target_port: str


@dataclass(frozen=True, slots=True)
class FlowRecipe:
    recipe_id: str
    display_name: str
    description: str
    ui_mode: str
    layout_preset: str
    nodes: tuple[FlowRecipeNode, ...]
    edges: tuple[FlowRecipeEdge, ...]


FLOW_RECIPES: dict[str, FlowRecipe] = {
    "standard_detection": FlowRecipe(
        recipe_id="standard_detection",
        display_name=tr.RECIPE_STANDARD_DETECTION_NAME,
        description=tr.RECIPE_STANDARD_DETECTION_DESC,
        ui_mode="design",
        layout_preset="analysis",
        nodes=(
            FlowRecipeNode("sigmf_source", (80.0, 150.0)),
            FlowRecipeNode("stft_processor", (340.0, 170.0)),
            FlowRecipeNode("cfar_detector", (620.0, 190.0)),
            FlowRecipeNode("stability_filter", (900.0, 170.0)),
        ),
        edges=(
            FlowRecipeEdge(0, "iq_out", 1, "iq_in"),
            FlowRecipeEdge(1, "fft_out", 2, "fft_in"),
            FlowRecipeEdge(2, "detections_out", 3, "detections_in"),
        ),
    ),
    "spectrum_only": FlowRecipe(
        recipe_id="spectrum_only",
        display_name=tr.RECIPE_SPECTRUM_ONLY_NAME,
        description=tr.RECIPE_SPECTRUM_ONLY_DESC,
        ui_mode="design",
        layout_preset="analysis",
        nodes=(
            FlowRecipeNode("sigmf_source", (120.0, 180.0)),
            FlowRecipeNode("stft_processor", (420.0, 200.0)),
        ),
        edges=(
            FlowRecipeEdge(0, "iq_out", 1, "iq_in"),
        ),
    ),
}
