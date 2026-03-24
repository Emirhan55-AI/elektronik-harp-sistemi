"""
NodeDescriptor — Bir node tipinin kimlik kartı.

Her adapter sınıfı, pipeline/UI'ya kendini tanıtan bir
NodeDescriptor taşır. Bu descriptor'lar:
- Paletten blok ekleme
- Config formları oluşturma
- Port uyumluluk kontrolü
- Persistence (kaydetme/yükleme)
için temel bilgi kaynağıdır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .port_types import PortDef


@dataclass(frozen=True, slots=True)
class NodeDescriptor:
    """Bir node tipinin değişmez tanımı."""

    # ── Kimlik ───────────────────────────────────────────────────
    node_id: str            # Benzersiz tip ID: "sdr_source", "fft_processor"
    display_name: str       # Türkçe görünen ad: "SDR Kaynağı"
    category: str           # Türkçe kategori: "Kaynaklar", "İşleyiciler"
    description: str = ""   # Türkçe açıklama

    # ── Portlar ──────────────────────────────────────────────────
    input_ports: tuple[PortDef, ...] = ()
    output_ports: tuple[PortDef, ...] = ()

    # ── Config ───────────────────────────────────────────────────
    config_schema: dict[str, Any] = field(default_factory=dict)
    """
    JSON-Schema benzeri config tanımı. Örnek:
    {
        "center_freq": {"type": "float", "default": 100e6, "label": "Merkez Frekans (Hz)"},
        "sample_rate": {"type": "float", "default": 2.4e6, "label": "Örnekleme Hızı (Hz)"},
        "gain":        {"type": "float", "default": 30.0,  "label": "Kazanç (dB)"},
    }
    """

    # ── Yardımcılar ──────────────────────────────────────────────

    def get_input_port(self, name: str) -> PortDef | None:
        """İsme göre input port bul."""
        for p in self.input_ports:
            if p.name == name:
                return p
        return None

    def get_output_port(self, name: str) -> PortDef | None:
        """İsme göre output port bul."""
        for p in self.output_ports:
            if p.name == name:
                return p
        return None

    def default_config(self) -> dict[str, Any]:
        """Config schema'dan varsayılan değerlerin dict'ini üret."""
        defaults: dict[str, Any] = {}
        for key, spec in self.config_schema.items():
            if isinstance(spec, dict) and "default" in spec:
                defaults[key] = spec["default"]
        return defaults

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """
        Config'i schema'ya karşı doğrula.
        Hata mesajları listesi döner (boş = geçerli).
        """
        errors: list[str] = []
        for key, spec in self.config_schema.items():
            if not isinstance(spec, dict):
                continue
            required = spec.get("required", False)
            if not required:
                continue

            label = spec.get("label", key)
            if key not in config:
                errors.append(f"Zorunlu ayar eksik: {label}")
                continue

            value = config.get(key)
            if value is None:
                errors.append(f"Zorunlu ayar eksik: {label}")
                continue

            if isinstance(value, str) and not value.strip():
                errors.append(f"Zorunlu ayar eksik: {label}")
        return errors
