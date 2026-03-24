"""Akis tarifleri icin kaydetme/yukleme yardimcilari."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ehcore.contracts import check_port_compatibility
from ehcore.registry import NodeRegistry
from ehcore.runtime import PipelineGraph
from ehapp.strings import tr

from .layout_presets import LAYOUT_PRESETS
from .flow_recipes import FlowRecipe, FlowRecipeEdge, FlowRecipeNode


RECIPE_VERSION = "1.0"


class FlowRecipeValidationError(ValueError):
    """Akis tarifi gecersiz oldugunda firlatilir."""


def save_flow_recipe(filepath: str | Path, recipe: FlowRecipe) -> None:
    validate_flow_recipe(recipe)
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": RECIPE_VERSION,
        "recipe": _recipe_to_dict(recipe),
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_flow_recipe(filepath: str | Path) -> FlowRecipe:
    path = Path(filepath)
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    version = data.get("version", "unknown")
    if version != RECIPE_VERSION:
        raise ValueError(tr.RECIPEIO_VERSION_UNSUPPORTED.format(version=version))

    recipe = _recipe_from_dict(data["recipe"])
    validate_flow_recipe(recipe)
    return recipe


def build_recipe_from_graph(
    graph: PipelineGraph,
    *,
    display_name: str,
    description: str = "",
    recipe_id: str | None = None,
    ui_mode: str = "design",
    layout_preset: str = "design",
) -> FlowRecipe:
    recipe_nodes: list[FlowRecipeNode] = []
    node_index_by_id: dict[str, int] = {}

    for index, node in enumerate(graph.nodes):
        recipe_nodes.append(
            FlowRecipeNode(
                node_type_id=node.node_type_id,
                position=(float(node.position[0]), float(node.position[1])),
                config=dict(node.config),
            )
        )
        node_index_by_id[node.instance_id] = index

    recipe_edges: list[FlowRecipeEdge] = []
    for edge in graph.edges:
        source_index = node_index_by_id.get(edge.source_node_id)
        target_index = node_index_by_id.get(edge.target_node_id)
        if source_index is None or target_index is None:
            continue
        recipe_edges.append(
            FlowRecipeEdge(
                source_index=source_index,
                source_port=edge.source_port,
                target_index=target_index,
                target_port=edge.target_port,
            )
        )

    recipe = FlowRecipe(
        recipe_id=recipe_id or slugify_recipe_id(display_name),
        display_name=display_name,
        description=description,
        ui_mode=ui_mode,
        layout_preset=layout_preset,
        nodes=tuple(recipe_nodes),
        edges=tuple(recipe_edges),
    )
    validate_flow_recipe(recipe)
    return recipe


def validate_flow_recipe(recipe: FlowRecipe) -> None:
    """Tarifin sistemde uygulanabilir olup olmadigini kontrol et."""
    if recipe.ui_mode not in {"design", "operation"}:
        raise FlowRecipeValidationError(tr.RECIPEIO_INVALID_UI_MODE.format(value=recipe.ui_mode))
    if recipe.layout_preset not in LAYOUT_PRESETS:
        raise FlowRecipeValidationError(
            tr.RECIPEIO_UNKNOWN_LAYOUT.format(value=recipe.layout_preset)
        )
    if not recipe.nodes:
        raise FlowRecipeValidationError(tr.RECIPEIO_EMPTY_FLOW)

    descriptors_by_index = _collect_node_descriptors(recipe.nodes)
    node_count = len(recipe.nodes)
    for edge in recipe.edges:
        _validate_edge(edge, descriptors_by_index, node_count=node_count)


def slugify_recipe_id(display_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")
    return slug or "akis_tarifi"


def _recipe_to_dict(recipe: FlowRecipe) -> dict:
    return {
        "recipe_id": recipe.recipe_id,
        "display_name": recipe.display_name,
        "description": recipe.description,
        "ui_mode": recipe.ui_mode,
        "layout_preset": recipe.layout_preset,
        "nodes": [
            {
                "node_type_id": node.node_type_id,
                "position": [node.position[0], node.position[1]],
                "config": dict(node.config),
            }
            for node in recipe.nodes
        ],
        "edges": [
            {
                "source_index": edge.source_index,
                "source_port": edge.source_port,
                "target_index": edge.target_index,
                "target_port": edge.target_port,
            }
            for edge in recipe.edges
        ],
    }


def _recipe_from_dict(data: dict) -> FlowRecipe:
    return FlowRecipe(
        recipe_id=str(data["recipe_id"]),
        display_name=str(data["display_name"]),
        description=str(data.get("description", "")),
        ui_mode=str(data.get("ui_mode", "design")),
        layout_preset=str(data.get("layout_preset", "design")),
        nodes=tuple(
            FlowRecipeNode(
                node_type_id=str(node["node_type_id"]),
                position=(float(node["position"][0]), float(node["position"][1])),
                config=dict(node.get("config", {})),
            )
            for node in data.get("nodes", [])
        ),
        edges=tuple(
            FlowRecipeEdge(
                source_index=int(edge["source_index"]),
                source_port=str(edge["source_port"]),
                target_index=int(edge["target_index"]),
                target_port=str(edge["target_port"]),
            )
            for edge in data.get("edges", [])
        ),
    )


def _collect_node_descriptors(nodes: tuple[FlowRecipeNode, ...]) -> dict[int, object]:
    descriptors_by_index: dict[int, object] = {}
    for index, node in enumerate(nodes):
        adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
        if adapter_cls is None:
            raise FlowRecipeValidationError(
                tr.RECIPEIO_UNKNOWN_NODE_TYPE.format(value=node.node_type_id)
            )
        descriptors_by_index[index] = adapter_cls.descriptor
    return descriptors_by_index


def _validate_edge(edge: FlowRecipeEdge, descriptors_by_index: dict[int, object], *, node_count: int) -> None:
    if edge.source_index < 0 or edge.source_index >= node_count:
        raise FlowRecipeValidationError(
            tr.RECIPEIO_INVALID_SOURCE_INDEX.format(value=edge.source_index)
        )
    if edge.target_index < 0 or edge.target_index >= node_count:
        raise FlowRecipeValidationError(
            tr.RECIPEIO_INVALID_TARGET_INDEX.format(value=edge.target_index)
        )

    source_descriptor = descriptors_by_index[edge.source_index]
    target_descriptor = descriptors_by_index[edge.target_index]

    source_port = next(
        (port for port in source_descriptor.output_ports if port.name == edge.source_port),
        None,
    )
    if source_port is None:
        raise FlowRecipeValidationError(
            tr.RECIPEIO_SOURCE_PORT_MISSING.format(
                value=f"{source_descriptor.node_id}.{edge.source_port}"
            )
        )

    target_port = next(
        (port for port in target_descriptor.input_ports if port.name == edge.target_port),
        None,
    )
    if target_port is None:
        raise FlowRecipeValidationError(
            tr.RECIPEIO_TARGET_PORT_MISSING.format(
                value=f"{target_descriptor.node_id}.{edge.target_port}"
            )
        )

    if not check_port_compatibility(source_port.port_type, target_port.port_type):
        raise FlowRecipeValidationError(
            tr.RECIPEIO_PORT_INCOMPATIBLE.format(
                value=(
                    f"{source_descriptor.node_id}.{edge.source_port} -> "
                    f"{target_descriptor.node_id}.{edge.target_port}"
                )
            )
        )
