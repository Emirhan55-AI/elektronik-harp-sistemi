"""
SigMF Kaynak Adaptörü — SigMF dosyasından IQ verisi besleyen node.

Bu node, pipeline'ın başlangıç noktasıdır — veri kaynağı.
SigMF dosyasını okur ve her tick'te bir IQ bloğu üretir.

İleride BladeRF adaptörü de aynı çıkış portlarını kullanacak.
Kullanıcı sadece kaynak node'u değiştirerek sistemi gerçek SDR'ye
bağlayabilecek.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

from ehcore.contracts import (
    DataEnvelope,
    NodeDescriptor,
    PortDef,
    PortType,
)
from ehcore.io.sigmf_reader import SigMFReader
from ehcore.registry import NodeRegistry

from ._base import BaseAdapter

logger = logging.getLogger(__name__)


@NodeRegistry.register
class SigMFSourceAdapter(BaseAdapter):
    """SigMF Kaynağı — Dosyadan IQ verisi besler."""

    descriptor: ClassVar[NodeDescriptor] = NodeDescriptor(
        node_id="sigmf_source",
        display_name="SigMF Kaynağı",
        category="Kaynaklar",
        description="SigMF dosyasından IQ verisi okur ve pipeline'a besler.",
        input_ports=(),
        output_ports=(
            PortDef(name="iq_out", port_type=PortType.IQ, display_name="IQ Çıkış"),
        ),
        config_schema={
            "file_path": {
                "type": "file",
                "default": "",
                "label": "SigMF Dosya Yolu",
                "required": True,
            },
            "block_size": {
                "type": "int",
                "default": 65536,
                "label": "Blok Boyutu (sample)",
                "options": [4096, 8192, 16384, 32768, 65536, 131072],
            },
            "loop": {
                "type": "bool",
                "default": True,
                "label": "Döngü (Dosya Sonunda Başa Sar)",
            },
        },
    )

    def __init__(self) -> None:
        super().__init__()
        self._reader = SigMFReader()

    def configure(self, config: dict) -> None:
        defaults = self.descriptor.default_config()
        defaults.update(config)
        self._config = defaults

    def start(self) -> None:
        super().start()
        file_path = self._config.get("file_path", "")
        if file_path:
            try:
                self._reader.open(Path(file_path))
                self._reader._loop = self._config.get("loop", True)
                logger.info("SigMF kaynak başlatıldı: %s", file_path)
            except Exception as e:
                self.set_error(f"SigMF açılamadı: {e}")

    def stop(self) -> None:
        super().stop()
        self._reader.close()

    def process(
        self,
        inputs: dict[str, DataEnvelope],
    ) -> dict[str, DataEnvelope]:
        """Her tick'te bir IQ bloğu oku."""
        if not self._reader.is_open:
            return {}

        block_size = int(self._config.get("block_size", 65536))
        envelope = self._reader.read_block(block_size=block_size)

        if envelope is None:
            return {}

        return {"iq_out": envelope}
