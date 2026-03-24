"""JSON tabanli proje kaydetme ve yukleme yardimcilari."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ehapp.strings import tr
from ehcore.runtime.graph import PipelineGraph


PROJECT_VERSION = "1.0"


def save_project(
    filepath: str | Path,
    graph: PipelineGraph,
    workspace: dict[str, Any] | None = None,
) -> None:
    data = {
        "version": PROJECT_VERSION,
        "graph": graph.to_dict(),
        "workspace": workspace or {},
    }

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_project(filepath: str | Path) -> tuple[PipelineGraph, dict[str, Any]]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(tr.PROJECTIO_FILE_NOT_FOUND.format(path=path))

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    version = data.get("version", "unknown")
    if version != PROJECT_VERSION:
        raise ValueError(
            tr.PROJECTIO_VERSION_UNSUPPORTED.format(
                version=version,
                expected=PROJECT_VERSION,
            )
        )

    graph_data = data.get("graph", {"nodes": [], "edges": []})
    graph = PipelineGraph.from_dict(graph_data)
    workspace = data.get("workspace", {})
    return graph, workspace
