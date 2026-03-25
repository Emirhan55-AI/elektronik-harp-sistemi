"""
PipelineGraph — DAG tabanlı pipeline veri yapısı.

Node ekleme/silme, edge ekleme/silme, topoloji sorgulaması.
UI bağımsız — saf Python veri yapısı.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeInstance:
    """Pipeline'daki tek bir node örneği."""
    instance_id: str                     # Benzersiz instance ID (UUID)
    node_type_id: str                    # Adapter'ın node_id'si ("sigmf_source")
    config: dict[str, Any] = field(default_factory=dict)
    position: tuple[float, float] = (0.0, 0.0)  # Canvas pozisyonu (UI için)


@dataclass(frozen=True, slots=True)
class Edge:
    """İki node port arasındaki bağlantı."""
    source_node_id: str       # Çıkış node instance ID
    source_port: str          # Çıkış port adı
    target_node_id: str       # Giriş node instance ID
    target_port: str          # Giriş port adı


class PipelineGraph:
    """
    DAG tabanlı pipeline grafiği.

    Node'lar ve edge'leri tutar. Topoloji sorgulamaları yapar.
    UI'dan bağımsız — serialization için to_dict/from_dict sağlar.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, NodeInstance] = {}
        self._edges: list[Edge] = []
        self._variables: dict[str, Any] = {}

    # ── Node İşlemleri ───────────────────────────────────────────

    def add_node(
        self,
        node_type_id: str,
        config: dict[str, Any] | None = None,
        position: tuple[float, float] = (0.0, 0.0),
        instance_id: str | None = None,
    ) -> NodeInstance:
        """Yeni node ekle ve instance döndür."""
        iid = instance_id or uuid.uuid4().hex[:12]
        node = NodeInstance(
            instance_id=iid,
            node_type_id=node_type_id,
            config=config or {},
            position=position,
        )
        self._nodes[iid] = node
        return node

    def remove_node(self, instance_id: str) -> None:
        """Node'u ve ilişkili tüm edge'leri sil."""
        self._nodes.pop(instance_id, None)
        self._edges = [
            e for e in self._edges
            if e.source_node_id != instance_id and e.target_node_id != instance_id
        ]

    def get_node(self, instance_id: str) -> NodeInstance | None:
        return self._nodes.get(instance_id)

    @property
    def nodes(self) -> list[NodeInstance]:
        return list(self._nodes.values())

    @property
    def node_ids(self) -> list[str]:
        return list(self._nodes.keys())

    # ── Edge İşlemleri ───────────────────────────────────────────

    def add_edge(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> Edge:
        """Yeni bağlantı ekle."""
        if source_node_id not in self._nodes:
            raise ValueError(f"Kaynak node bulunamadı: {source_node_id}")
        if target_node_id not in self._nodes:
            raise ValueError(f"Hedef node bulunamadı: {target_node_id}")

        # Aynı hedef porta birden fazla bağlantı olmamalı
        for e in self._edges:
            if e.target_node_id == target_node_id and e.target_port == target_port:
                raise ValueError(
                    f"Port '{target_port}' zaten bağlı: "
                    f"{e.source_node_id}.{e.source_port}"
                )

        edge = Edge(source_node_id, source_port, target_node_id, target_port)
        self._edges.append(edge)
        return edge

    def remove_edge(self, edge: Edge) -> None:
        """Edge sil."""
        try:
            self._edges.remove(edge)
        except ValueError:
            pass

    def remove_edge_between(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> bool:
        """Endpoint bilgisine göre edge sil."""
        edge = Edge(source_node_id, source_port, target_node_id, target_port)
        try:
            self._edges.remove(edge)
            return True
        except ValueError:
            return False

    def remove_edges_for_port(
        self,
        node_id: str,
        port_name: str,
    ) -> int:
        """Belirli bir portun tüm bağlantılarını sil. Silinen sayıyı döndür."""
        before = len(self._edges)
        self._edges = [
            e for e in self._edges
            if not (
                (e.source_node_id == node_id and e.source_port == port_name)
                or (e.target_node_id == node_id and e.target_port == port_name)
            )
        ]
        return before - len(self._edges)

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    @property
    def variables(self) -> dict[str, Any]:
        return dict(self._variables)

    def set_variable(self, name: str, value: Any) -> None:
        self._variables[str(name)] = value

    def set_variables(self, variables: dict[str, Any]) -> None:
        self._variables = dict(variables)

    def remove_variable(self, name: str) -> None:
        self._variables.pop(name, None)

    # ── Topoloji Sorguları ───────────────────────────────────────

    def get_successors(self, node_id: str) -> list[str]:
        """Node'un çıkışlarına bağlı node ID'leri."""
        return list({e.target_node_id for e in self._edges if e.source_node_id == node_id})

    def get_predecessors(self, node_id: str) -> list[str]:
        """Node'a giriş eden node ID'leri."""
        return list({e.source_node_id for e in self._edges if e.target_node_id == node_id})

    def get_source_nodes(self) -> list[str]:
        """Girişi olmayan node'lar (kaynak/source)."""
        all_targets = {e.target_node_id for e in self._edges}
        return [nid for nid in self._nodes if nid not in all_targets]

    def get_sink_nodes(self) -> list[str]:
        """Çıkışı olmayan node'lar (sink/viewer)."""
        all_sources = {e.source_node_id for e in self._edges}
        return [nid for nid in self._nodes if nid not in all_sources]

    def get_edges_from(self, node_id: str) -> list[Edge]:
        """Node'dan çıkan tüm edge'ler."""
        return [e for e in self._edges if e.source_node_id == node_id]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        """Node'a giren tüm edge'ler."""
        return [e for e in self._edges if e.target_node_id == node_id]

    # ── Serialization ────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Grafiği JSON-serializable dict'e dönüştür."""
        return {
            "variables": dict(self._variables),
            "nodes": [
                {
                    "instance_id": n.instance_id,
                    "node_type_id": n.node_type_id,
                    "config": n.config,
                    "position": list(n.position),
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source_node_id": e.source_node_id,
                    "source_port": e.source_port,
                    "target_node_id": e.target_node_id,
                    "target_port": e.target_port,
                }
                for e in self._edges
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> PipelineGraph:
        """Dict'ten grafik oluştur."""
        graph = cls()
        graph.set_variables(data.get("variables", {}))
        for n in data.get("nodes", []):
            graph.add_node(
                node_type_id=n["node_type_id"],
                config=n.get("config", {}),
                position=tuple(n.get("position", [0.0, 0.0])),
                instance_id=n["instance_id"],
            )
        for e in data.get("edges", []):
            graph.add_edge(
                source_node_id=e["source_node_id"],
                source_port=e["source_port"],
                target_node_id=e["target_node_id"],
                target_port=e["target_port"],
            )
        return graph

    def clear(self) -> None:
        """Tüm node ve edge'leri temizle."""
        self._nodes.clear()
        self._edges.clear()
        self._variables.clear()

    def __len__(self) -> int:
        return len(self._nodes)


