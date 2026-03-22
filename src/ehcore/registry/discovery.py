"""
Plugin keşif modülü — harici eklenti klasörünü tarar ve adapter'ları kaydettirir.

Varsayılan olarak proje kökündeki `plugins/` klasörünü tarar.
Her .py dosyası import edilir; eğer `register_plugin()` fonksiyonu varsa çağrılır.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from .registry import NodeRegistry  # noqa: F401 — side-effect: registers

logger = logging.getLogger(__name__)


def discover_plugins(plugin_dir: str | Path) -> int:
    """
    Belirtilen klasördeki .py dosyalarını tara ve adapter'ları kaydet.

    Her plugin dosyası iki yoldan biriyle kayıt yapabilir:
    1. @NodeRegistry.register decorator kullanarak (import sırasında otomatik)
    2. register_plugin() fonksiyonu tanımlayarak (bu fonksiyon çağrılır)

    Args:
        plugin_dir: Taranacak klasör yolu.

    Returns:
        Başarıyla yüklenen plugin dosyası sayısı.
    """
    plugin_path = Path(plugin_dir)
    if not plugin_path.is_dir():
        logger.warning("Plugin klasörü bulunamadı: %s", plugin_path)
        return 0

    loaded = 0
    for py_file in sorted(plugin_path.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        module_name = f"ehcore_plugin_{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                logger.warning("Plugin yüklenemedi (spec yok): %s", py_file)
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Eğer register_plugin() fonksiyonu varsa çağır
            register_fn = getattr(module, "register_plugin", None)
            if callable(register_fn):
                register_fn()

            loaded += 1
            logger.info("Plugin yüklendi: %s", py_file.name)

        except Exception:
            logger.exception("Plugin yüklenirken hata: %s", py_file.name)

    logger.info("Toplam %d plugin yüklendi (%s)", loaded, plugin_path)
    return loaded
