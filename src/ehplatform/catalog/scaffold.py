"""AI-friendly manifest taslak ureticileri."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ManifestPortDraft:
    name: str
    port_type: str
    display_name: str
    tooltip: str
    required: bool = True
    visible: bool = True


@dataclass(frozen=True, slots=True)
class ManifestConfigDraft:
    name: str
    field_type: str
    default: Any
    label: str
    options: tuple[Any, ...] = ()
    required: bool | None = None


@dataclass(frozen=True, slots=True)
class ManifestDraft:
    node_id: str
    display_name: str
    category: str
    description: str
    algorithm_import_path: str
    algorithm_class_name: str
    input_ports: tuple[ManifestPortDraft, ...] = ()
    output_ports: tuple[ManifestPortDraft, ...] = ()
    config_fields: tuple[ManifestConfigDraft, ...] = ()
    visualization_bindings: tuple[tuple[str, str], ...] = ()
    debug_capabilities: tuple[str, ...] = ()
    compat_aliases: tuple[str, ...] = ()
    ui_hints: dict[str, Any] = field(default_factory=dict)


def manifest_draft_from_mapping(data: Mapping[str, Any]) -> ManifestDraft:
    """JSON benzeri bir mapping'den ManifestDraft uret."""
    return ManifestDraft(
        node_id=_require_text(data, "node_id"),
        display_name=_require_text(data, "display_name"),
        category=_require_text(data, "category"),
        description=_require_text(data, "description"),
        algorithm_import_path=_require_text(data, "algorithm_import_path"),
        algorithm_class_name=_require_text(data, "algorithm_class_name"),
        input_ports=_coerce_port_drafts(data.get("input_ports", ())),
        output_ports=_coerce_port_drafts(data.get("output_ports", ())),
        config_fields=_coerce_config_drafts(data.get("config_fields", ())),
        visualization_bindings=_coerce_bindings(data.get("visualization_bindings", ())),
        debug_capabilities=_coerce_text_tuple(data.get("debug_capabilities", ())),
        compat_aliases=_coerce_text_tuple(data.get("compat_aliases", ())),
        ui_hints=dict(data.get("ui_hints", {})),
    )


def suggest_manifest_module(category: str, node_id: str = "") -> str:
    """Kategoriye gore uygun manifest modul yolunu oner."""
    normalized = _normalize_text(category)
    if normalized in {"kaynaklar", "kaynak"}:
        return "src/ehplatform/catalog/manifests/sources.py"
    if normalized in {"on_isleme", "isleme", "dsp"}:
        return "src/ehplatform/catalog/manifests/dsp.py"
    if normalized in {"tespit", "detection", "tracking", "izleme"}:
        return "src/ehplatform/catalog/manifests/detection.py"
    if node_id:
        return f"src/ehplatform/catalog/manifests/{_normalize_text(node_id)}.py"
    return "src/ehplatform/catalog/manifests/yeni_modul.py"


def render_manifest_module(draft: ManifestDraft) -> str:
    """Verilen taslaktan Python manifest modul metni uret."""
    lines: list[str] = [
        '"""AI tarafindan uretilen manifest modul taslagi."""',
        "",
        "from __future__ import annotations",
        "",
        "from ehplatform.contracts import PortType",
        "",
        "from ehplatform.catalog.types import NodeManifest, PortManifest, VisualizationBinding",
        "",
        "MANIFESTS = (",
        "    NodeManifest(",
        f"        node_id={_py_string(draft.node_id)},",
        f"        display_name={_py_string(draft.display_name)},",
        f"        category={_py_string(draft.category)},",
        f"        description={_py_string(draft.description)},",
        f"        algorithm_import_path={_py_string(draft.algorithm_import_path)},",
        f"        algorithm_class_name={_py_string(draft.algorithm_class_name)},",
        "        input_ports=(",
    ]

    lines.extend(_render_port_lines(draft.input_ports, indent="            "))
    lines.extend(
        [
            "        ),",
            "        output_ports=(",
        ]
    )
    lines.extend(_render_port_lines(draft.output_ports, indent="            "))
    lines.extend(
        [
            "        ),",
            "        config_schema={",
        ]
    )
    lines.extend(_render_config_lines(draft.config_fields, indent="            "))
    lines.extend(
        [
            "        },",
            f"        ui_hints={_py_value(draft.ui_hints)},",
            "        visualization_bindings=(",
        ]
    )
    for port_name, view_id in draft.visualization_bindings:
        lines.append(
            "            VisualizationBinding("
            f"port_name={_py_string(port_name)}, view_id={_py_string(view_id)}"
            "),"
        )
    lines.extend(
        [
            "        ),",
            f"        debug_capabilities={_py_value(tuple(draft.debug_capabilities))},",
            f"        compat_aliases={_py_value(tuple(draft.compat_aliases))},",
            "    ),",
            ")",
            "",
        ]
    )
    return "\n".join(lines)


def build_ai_handoff_text(draft: ManifestDraft) -> str:
    """AI'ye verilecek duz metin entegrasyon paketini uret."""
    lines = [
        f"Algoritma dosya yolu: {draft.algorithm_import_path}",
        f"Sinif adi: {draft.algorithm_class_name}",
        f"Node id: {draft.node_id}",
        f"Gorunen ad: {draft.display_name}",
        f"Kategori: {draft.category}",
        "Girisler:",
    ]
    lines.extend(
        f"- {port.name} / {port.port_type} / {'zorunlu' if port.required else 'opsiyonel'}"
        for port in draft.input_ports
    )
    lines.append("Cikislar:")
    lines.extend(f"- {port.name} / {port.port_type}" for port in draft.output_ports)
    if draft.config_fields:
        lines.append("Config:")
        for field in draft.config_fields:
            lines.append(f"- {field.name} ({field.field_type}, default {field.default!r})")
    if draft.visualization_bindings:
        lines.append("Gorsellestirme:")
        for port_name, view_id in draft.visualization_bindings:
            lines.append(f"- {port_name} -> {view_id}")
    return "\n".join(lines)


def build_integration_checklist_text(draft: ManifestDraft) -> str:
    """Yeni blok entegrasyonu icin pratik kabul listesini uret."""
    lines = [
        "Entegrasyon kontrol listesi:",
        f"1. Algoritma modulu mevcut mu: {draft.algorithm_import_path}",
        f"2. Kernel sinifi belirli mi: {draft.algorithm_class_name}",
        f"3. Node id net mi: {draft.node_id}",
        f"4. Gorunen ad Turkce mi: {draft.display_name}",
        f"5. Kategori secildi mi: {draft.category}",
        "6. Giris portlari:",
    ]
    if draft.input_ports:
        lines.extend(
            f"   - {port.name} / {port.port_type} / {'zorunlu' if port.required else 'opsiyonel'} / "
            f"{'gorunur' if port.visible else 'gizli'}"
            for port in draft.input_ports
        )
    else:
        lines.append("   - Giris yok")

    lines.append("7. Cikis portlari:")
    if draft.output_ports:
        lines.extend(
            f"   - {port.name} / {port.port_type} / {'gorunur' if port.visible else 'gizli'}"
            for port in draft.output_ports
        )
    else:
        lines.append("   - Cikis yok")

    lines.append("8. Config alanlari:")
    if draft.config_fields:
        lines.extend(
            f"   - {field.name} ({field.field_type}, default={field.default!r})"
            for field in draft.config_fields
        )
    else:
        lines.append("   - Config yok")

    lines.append("9. Gorsellestirme baglari:")
    if draft.visualization_bindings:
        lines.extend(
            f"   - {port_name} -> {view_id}"
            for port_name, view_id in draft.visualization_bindings
        )
    else:
        lines.append("   - Bag yok")

    lines.extend(
        [
            f"10. Onerilen manifest modulu: {suggest_manifest_module(draft.category, draft.node_id)}",
            "11. AI gorevi:",
            "   - manifesti ekle",
            "   - UI/plot baglarini bagla",
            "   - algoritma dosyasina dokunma",
        ]
    )
    return "\n".join(lines)


def _render_port_lines(ports: tuple[ManifestPortDraft, ...], *, indent: str) -> list[str]:
    lines: list[str] = []
    for port in ports:
        lines.extend(
            [
                f"{indent}PortManifest(",
                f"{indent}    name={_py_string(port.name)},",
                f"{indent}    port_type=PortType.{port.port_type},",
                f"{indent}    display_name={_py_string(port.display_name)},",
                f"{indent}    required={port.required},",
                f"{indent}    visible={port.visible},",
                f"{indent}    tooltip={_py_string(port.tooltip)},",
                f"{indent}),",
            ]
        )
    return lines


def _render_config_lines(fields: tuple[ManifestConfigDraft, ...], *, indent: str) -> list[str]:
    lines: list[str] = []
    for field in fields:
        spec: dict[str, Any] = {
            "type": field.field_type,
            "default": field.default,
            "label": field.label,
        }
        if field.options:
            spec["options"] = list(field.options)
        if field.required is not None:
            spec["required"] = field.required
        lines.append(f"{indent}{_py_string(field.name)}: {_py_value(spec)},")
    return lines


def _py_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _py_value(value: Any) -> str:
    return repr(value)


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    translation = str.maketrans(
        {
            "ı": "i",
            "ş": "s",
            "ğ": "g",
            "ü": "u",
            "ö": "o",
            "ç": "c",
        }
    )
    lowered = lowered.translate(translation)
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


def _require_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' alani bos bir metin olmalidir")
    return value.strip()


def _coerce_port_drafts(value: Any) -> tuple[ManifestPortDraft, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("Port listeleri sirali bir yapi olmalidir")

    ports: list[ManifestPortDraft] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TypeError("Her port taslagi bir mapping olmalidir")
        ports.append(
            ManifestPortDraft(
                name=_require_text(item, "name"),
                port_type=_require_text(item, "port_type"),
                display_name=_require_text(item, "display_name"),
                tooltip=_require_text(item, "tooltip"),
                required=bool(item.get("required", True)),
                visible=bool(item.get("visible", True)),
            )
        )
    return tuple(ports)


def _coerce_config_drafts(value: Any) -> tuple[ManifestConfigDraft, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("Config alanlari sirali bir yapi olmalidir")

    fields: list[ManifestConfigDraft] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TypeError("Her config taslagi bir mapping olmalidir")
        fields.append(
            ManifestConfigDraft(
                name=_require_text(item, "name"),
                field_type=_require_text(item, "field_type"),
                default=item.get("default"),
                label=_require_text(item, "label"),
                options=tuple(item.get("options", ())),
                required=item.get("required"),
            )
        )
    return tuple(fields)


def _coerce_bindings(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("Gorsellestirme baglari sirali bir yapi olmalidir")

    bindings: list[tuple[str, str]] = []
    for item in value:
        if isinstance(item, Mapping):
            port_name = _require_text(item, "port_name")
            view_id = _require_text(item, "view_id")
            bindings.append((port_name, view_id))
            continue
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) == 2:
            port_name, view_id = item
            if not isinstance(port_name, str) or not isinstance(view_id, str):
                raise TypeError("Gorsellestirme baglari metin ikilisi olmalidir")
            bindings.append((port_name.strip(), view_id.strip()))
            continue
        raise TypeError("Gorsellestirme baglari mapping veya ikili liste olmalidir")
    return tuple(bindings)


def _coerce_text_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("Metin listesi sirali bir yapi olmalidir")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("Liste elemanlari metin olmalidir")
        cleaned = item.strip()
        if cleaned:
            result.append(cleaned)
    return tuple(result)


