"""Release smoke checks for the desktop application."""

from __future__ import annotations

import os
import sys
import tempfile
import tomllib
from pathlib import Path

from app.persistence.project_io import load_project, save_project
from ehplatform.registry import NodeRegistry, discover_plugins_report
from ehplatform.runtime import PipelineGraph

REQUIRED_NODE_IDS = {
    "sigmf_source",
    "stft_processor",
    "cfar_detector",
    "stability_filter",
}


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    failures: list[str] = []
    try:
        _check_entrypoint()
        _check_registry()
        _check_plugin_discovery()
        _check_palette()
        _check_project_roundtrip()
    except Exception as exc:
        failures.append(f"Beklenmeyen smoke hatasi: {exc}")

    if failures:
        for failure in failures:
            print(f"[SMOKE][FAIL] {failure}", file=sys.stderr)
        return 1

    print("[SMOKE][OK] entrypoint, registry, palette, plugin discovery ve proje roundtrip saglam.")
    return 0


def _check_entrypoint() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as handle:
        project_data = tomllib.load(handle)
    scripts = project_data["project"]["scripts"]
    entrypoint = scripts.get("eh-system")
    if entrypoint != "app.__main__:main":
        raise RuntimeError(f"Beklenen eh-system entrypoint'i bulunamadi: {entrypoint!r}")


def _check_registry() -> None:
    import ehplatform.adapters  # noqa: F401

    discovered = {manifest.node_id for manifest in NodeRegistry.get_all_manifests()}
    missing = sorted(REQUIRED_NODE_IDS - discovered)
    if missing:
        raise RuntimeError(f"Yerlesik node kayitlari eksik: {', '.join(missing)}")


def _check_plugin_discovery() -> None:
    plugin_dir = Path(__file__).resolve().parents[2] / "plugins"
    report = discover_plugins_report(plugin_dir)
    if report.failed_count:
        raise RuntimeError(f"Plugin discovery hatali dondu: {report.failed_count} hata")


def _check_palette() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from app.canvas.palette import BlockPalette

    app = QApplication.instance()
    created_app = False
    if app is None:
        app = QApplication(["eh-system-smoke"])
        created_app = True

    palette = BlockPalette()
    seen_node_ids: set[str] = set()
    for top_index in range(palette._tree.topLevelItemCount()):
        category_item = palette._tree.topLevelItem(top_index)
        for child_index in range(category_item.childCount()):
            child = category_item.child(child_index)
            node_id = child.data(0, Qt.ItemDataRole.UserRole)
            if node_id:
                seen_node_ids.add(str(node_id))

    missing = sorted(REQUIRED_NODE_IDS - seen_node_ids)
    if missing:
        raise RuntimeError(f"Palette built-in bloklari gostermiyor: {', '.join(missing)}")

    palette.deleteLater()
    if created_app:
        app.quit()


def _check_project_roundtrip() -> None:
    graph = PipelineGraph()
    source = graph.add_node(
        node_type_id="sigmf_source",
        instance_id="src000000001",
        config={"file_path": "sample.sigmf-data"},
    )
    stft = graph.add_node(
        node_type_id="stft_processor",
        instance_id="stft00000001",
    )
    cfar = graph.add_node(
        node_type_id="cfar_detector",
        instance_id="cfar00000001",
    )
    graph.add_edge(source.instance_id, "iq_out", stft.instance_id, "iq_in")
    graph.add_edge(stft.instance_id, "fft_out", cfar.instance_id, "fft_in")
    graph.set_variable("session_name", "smoke")

    with tempfile.TemporaryDirectory(prefix="eh-system-smoke-") as temp_dir:
        project_path = Path(temp_dir) / "smoke.ehproj"
        save_project(project_path, graph, workspace={"layout": "design"})
        loaded_graph, workspace = load_project(project_path)

    loaded_node_ids = {node.node_type_id for node in loaded_graph.nodes}
    if not {"sigmf_source", "stft_processor", "cfar_detector"}.issubset(loaded_node_ids):
        raise RuntimeError("Proje roundtrip sonrasi node tipleri korunmadi")
    if len(loaded_graph.edges) != 2:
        raise RuntimeError("Proje roundtrip sonrasi edge sayisi bozuldu")
    if workspace.get("layout") != "design":
        raise RuntimeError("Workspace bilgisi proje roundtrip sonrasi korunmadi")
