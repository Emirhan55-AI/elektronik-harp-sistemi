"""
Spektrum/Waterfall Görüntüleyici Adapter — Sink node.

Bu adaptör gelen FFT/waterfall verisini kendinde tutar; UI tarafı
bridge/worker aracılığıyla bu veriyi sorgular ve grafiğe basar.

Görüntüleyici adapter'ı veriyi dönüştürmez — sadece absorbe eder (sink).
"""

from __future__ import annotations

import threading
from collections import deque
from typing import ClassVar

from ehcore.contracts import (
    DataEnvelope,
    NodeDescriptor,
    PortDef,
    PortType,
)
from ehcore.registry import NodeRegistry

from ._base import BaseAdapter

# Waterfall buffer: en son N satır tutulur
_MAX_WATERFALL_ROWS = 200


@NodeRegistry.register
class ViewerAdapter(BaseAdapter):
    """Spektrum/Waterfall Görüntüleyici — veri toplayan sink node."""

    descriptor: ClassVar[NodeDescriptor] = NodeDescriptor(
        node_id="spectrum_viewer",
        display_name="Spektrum/Waterfall Görüntüleyici",
        category="Görüntüleyiciler",
        description="Gelen FFT verisini spektrum ve waterfall olarak görüntüler.",
        input_ports=(
            PortDef(
                name="fft_in",
                port_type=PortType.FFT,
                display_name="FFT Giriş",
                required=False,
            ),
            PortDef(
                name="waterfall_in",
                port_type=PortType.WATERFALL,
                display_name="Waterfall Giriş",
                required=False,
            ),
        ),
        output_ports=(),
        config_schema={
            "max_waterfall_rows": {
                "type": "int",
                "default": _MAX_WATERFALL_ROWS,
                "label": "Waterfall Satır Limiti",
            },
        },
    )

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._latest_fft: DataEnvelope | None = None
        self._waterfall_buffer: deque[DataEnvelope] = deque(
            maxlen=_MAX_WATERFALL_ROWS
        )

    def configure(self, config: dict) -> None:
        defaults = self.descriptor.default_config()
        defaults.update(config)
        self._config = defaults

        max_rows = int(self._config.get("max_waterfall_rows", _MAX_WATERFALL_ROWS))
        self._waterfall_buffer = deque(maxlen=max_rows)

    def process(
        self,
        inputs: dict[str, DataEnvelope],
    ) -> dict[str, DataEnvelope]:
        """Gelen veriyi buffer'a yaz. Çıkış üretmez (sink)."""
        with self._lock:
            fft_data = inputs.get("fft_in")
            if fft_data is not None:
                self._latest_fft = fft_data

            waterfall_data = inputs.get("waterfall_in")
            if waterfall_data is not None:
                self._waterfall_buffer.append(waterfall_data)

        return {}  # Sink — çıkış yok

    def reset(self) -> None:
        """Buffer'ları temizle."""
        super().reset()
        with self._lock:
            self._latest_fft = None
            self._waterfall_buffer.clear()

    # ── Bridge/UI Tarafından Okunacak ────────────────────────────

    def get_latest_fft(self) -> DataEnvelope | None:
        """En son FFT çerçevesini getir (thread-safe)."""
        with self._lock:
            return self._latest_fft

    def get_waterfall_rows(self) -> list[DataEnvelope]:
        """Tüm waterfall satırlarını getir (thread-safe)."""
        with self._lock:
            return list(self._waterfall_buffer)

    def get_waterfall_row_count(self) -> int:
        """Buffer'daki satır sayısı."""
        with self._lock:
            return len(self._waterfall_buffer)
