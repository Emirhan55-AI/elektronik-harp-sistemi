"""
ProjectIO — JSON tabanlı proje dosyası kaydetme/yükleme.

Dosya uzantısı: .ehproj

Kaydedilen bilgiler:
- Proje sürümü
- Node'lar (tip, config, pozisyon)
- Bağlantılar (edge'ler)
- Aktif sekme
- Tema seçimi
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ehcore.runtime.graph import PipelineGraph


# Proje dosya versiyonu
PROJECT_VERSION = "1.0"


def save_project(
    filepath: str | Path,
    graph: PipelineGraph,
    workspace: dict[str, Any] | None = None,
) -> None:
    """
    Projeyi JSON dosyasına kaydet.

    Args:
        filepath: .ehproj dosya yolu.
        graph: Pipeline grafiği.
        workspace: Ek çalışma alanı bilgileri (aktif sekme, vb.)
    """
    data = {
        "version": PROJECT_VERSION,
        "graph": graph.to_dict(),
        "workspace": workspace or {
            "active_tab": 0,
            "theme": "dark",
        },
    }

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project(filepath: str | Path) -> tuple[PipelineGraph, dict[str, Any]]:
    """
    Projeyi JSON dosyasından yükle.

    Args:
        filepath: .ehproj dosya yolu.

    Returns:
        (PipelineGraph, workspace_dict)

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ValueError: Geçersiz dosya formatı.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Proje dosyası bulunamadı: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Versiyon kontrolü
    version = data.get("version", "unknown")
    if version != PROJECT_VERSION:
        # İleride migration mantığı eklenebilir
        pass

    graph_data = data.get("graph", {"nodes": [], "edges": []})
    graph = PipelineGraph.from_dict(graph_data)

    workspace = data.get("workspace", {"active_tab": 0, "theme": "dark"})

    return graph, workspace
