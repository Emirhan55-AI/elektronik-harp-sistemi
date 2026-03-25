"""
Scheduler — Topological sort ile pipeline yürütme sırası belirleme.

Kahn's algorithm kullanarak DAG'daki node'ların yürütme
sırasını belirler. Cycle varsa hata fırlatır.
"""

from __future__ import annotations

from collections import deque

from .graph import PipelineGraph


class CycleDetectedError(Exception):
    """Pipeline'da döngü algılandı."""
    pass


def topological_sort(graph: PipelineGraph) -> list[str]:
    """
    Kahn's algorithm ile topological sort.

    Args:
        graph: Pipeline grafiği.

    Returns:
        Node instance ID'leri yürütme sırasında.

    Raises:
        CycleDetectedError: Grafik bir döngü içeriyorsa.
    """
    # In-degree hesapla (Benzersiz predecessor node sayısına göre)
    in_degree: dict[str, int] = {nid: len(graph.get_predecessors(nid)) for nid in graph.node_ids}

    # In-degree = 0 olan node'larla başla
    queue: deque[str] = deque()
    for nid, degree in in_degree.items():
        if degree == 0:
            queue.append(nid)

    result: list[str] = []

    while queue:
        node_id = queue.popleft()
        result.append(node_id)

        for successor_id in graph.get_successors(node_id):
            in_degree[successor_id] -= 1
            if in_degree[successor_id] == 0:
                queue.append(successor_id)

    if len(result) != len(graph):
        # Tüm node'lar sıralanamamış → döngü var
        remaining = set(graph.node_ids) - set(result)
        raise CycleDetectedError(remaining)

    return result


