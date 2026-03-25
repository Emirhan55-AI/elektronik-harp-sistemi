"""Plugin kesif ve kayit yardimcilari."""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ehplatform.catalog import NodeManifest
from ehplatform.catalog.validation import ensure_valid_manifest_collection

from .registry import NodeRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PluginDiscoveryEntry:
    name: str
    path: str
    status: str
    loaded_manifests: int = 0
    error: str = ""


@dataclass(frozen=True, slots=True)
class PluginDiscoveryReport:
    plugin_dir: str
    entries: tuple[PluginDiscoveryEntry, ...]

    @property
    def successful_count(self) -> int:
        return sum(1 for entry in self.entries if entry.status == "loaded")

    @property
    def failed_count(self) -> int:
        return sum(1 for entry in self.entries if entry.status == "error")

    @property
    def discovered_count(self) -> int:
        return len(self.entries)


def discover_plugins(plugin_dir: str | Path) -> int:
    """Uyumluluk icin yalnizca yuklenen plugin sayisini dondur."""
    return discover_plugins_report(plugin_dir).successful_count


def discover_plugins_report(plugin_dir: str | Path) -> PluginDiscoveryReport:
    """Plugin klasorunu tara ve ayrintili kesif raporu dondur."""
    plugin_path = Path(plugin_dir)
    if not plugin_path.is_dir():
        logger.warning("Plugin klasoru bulunamadi: %s", plugin_path)
        return PluginDiscoveryReport(
            plugin_dir=str(plugin_path),
            entries=(),
        )

    entries: list[PluginDiscoveryEntry] = []
    for candidate in _iter_plugin_candidates(plugin_path):
        module_name = _build_module_name(candidate)
        try:
            module = _load_plugin_module(candidate, module_name)

            register_fn = getattr(module, "register_plugin", None)
            if callable(register_fn):
                register_fn()

            manifests = ensure_valid_manifest_collection(_extract_manifests(module))
            for manifest in manifests:
                NodeRegistry.register_manifest(manifest)

            entries.append(
                PluginDiscoveryEntry(
                    name=candidate.name,
                    path=str(candidate),
                    status="loaded",
                    loaded_manifests=len(manifests),
                )
            )
            logger.info("Plugin yuklendi: %s", candidate.name)
        except Exception as exc:
            entries.append(
                PluginDiscoveryEntry(
                    name=candidate.name,
                    path=str(candidate),
                    status="error",
                    error=str(exc),
                )
            )
            logger.exception("Plugin yuklenirken hata: %s", candidate.name)

    report = PluginDiscoveryReport(
        plugin_dir=str(plugin_path),
        entries=tuple(entries),
    )
    logger.info(
        "Plugin kesfi tamamlandi: %d yuklendi, %d hata, %d aday (%s)",
        report.successful_count,
        report.failed_count,
        report.discovered_count,
        plugin_path,
    )
    return report


def _iter_plugin_candidates(plugin_dir: Path) -> Iterable[Path]:
    files = sorted(path for path in plugin_dir.glob("*.py") if not path.name.startswith("_"))
    packages = sorted(
        path
        for path in plugin_dir.iterdir()
        if path.is_dir()
        and not path.name.startswith("_")
        and (path / "__init__.py").is_file()
    )
    yield from files
    yield from packages


def _load_plugin_module(candidate: Path, module_name: str):
    if candidate.is_dir():
        init_file = candidate / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            module_name,
            init_file,
            submodule_search_locations=[str(candidate)],
        )
    else:
        spec = importlib.util.spec_from_file_location(module_name, candidate)

    if spec is None or spec.loader is None:
        raise ImportError(f"Plugin spec olusturulamadi: {candidate}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_module_name(candidate: Path) -> str:
    suffix = "pkg" if candidate.is_dir() else "py"
    sanitized = "".join(ch if ch.isalnum() else "_" for ch in candidate.stem.lower())
    return f"ehcore_plugin_{suffix}_{sanitized}"


def _extract_manifests(module) -> Iterable[NodeManifest]:
    if hasattr(module, "get_manifests") and callable(module.get_manifests):
        return _coerce_manifests(module.get_manifests())
    if hasattr(module, "MANIFESTS"):
        return _coerce_manifests(module.MANIFESTS)
    return ()


def _coerce_manifests(value) -> tuple[NodeManifest, ...]:
    manifests = tuple(value or ())
    for manifest in manifests:
        if not isinstance(manifest, NodeManifest):
            raise TypeError("Plugin MANIFESTS yalnizca NodeManifest nesneleri icermelidir")
    return manifests


