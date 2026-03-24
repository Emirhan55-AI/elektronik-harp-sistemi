"""Manifest dogrulama yardimcilari."""

from __future__ import annotations

import importlib
from collections import Counter
from typing import Iterable

from ehcore.algorithms import AlgorithmKernel

from .types import NodeManifest


class ManifestValidationError(ValueError):
    """Manifest yapisi gecerli olmadiginda firlatilir."""


def validate_manifest(
    manifest: NodeManifest,
    *,
    validate_algorithm: bool = True,
) -> tuple[str, ...]:
    """Tek bir manifest icin yapisal hata listesini don."""
    errors: list[str] = []
    prefix = f"[{manifest.node_id or '?'}]"

    def add(message: str) -> None:
        errors.append(f"{prefix} {message}")

    if not manifest.node_id.strip():
        add("node_id bos olamaz.")
    if not manifest.display_name.strip():
        add("display_name bos olamaz.")
    if not manifest.category.strip():
        add("category bos olamaz.")
    if not manifest.algorithm_import_path.strip():
        add("algorithm_import_path bos olamaz.")
    if not manifest.algorithm_class_name.strip():
        add("algorithm_class_name bos olamaz.")
    if not isinstance(manifest.config_schema, dict):
        add("config_schema bir dict olmalidir.")
    if not isinstance(manifest.ui_hints, dict):
        add("ui_hints bir dict olmalidir.")

    _validate_ports(errors, prefix, manifest)
    _validate_config_schema(errors, prefix, manifest)
    _validate_visualization_bindings(errors, prefix, manifest)
    _validate_aliases(errors, prefix, manifest)

    if validate_algorithm and manifest.algorithm_import_path and manifest.algorithm_class_name:
        _validate_algorithm_target(errors, prefix, manifest)

    return tuple(errors)


def validate_manifest_collection(
    manifests: Iterable[NodeManifest],
    *,
    validate_algorithm: bool = True,
) -> tuple[str, ...]:
    """Manifest koleksiyonunu capraz olarak dogrula."""
    manifest_list = tuple(manifests)
    errors: list[str] = []
    errors.extend(
        error
        for manifest in manifest_list
        for error in validate_manifest(manifest, validate_algorithm=validate_algorithm)
    )

    node_counter = Counter(manifest.node_id for manifest in manifest_list if manifest.node_id)
    for node_id, count in node_counter.items():
        if count > 1:
            errors.append(f"[{node_id}] node_id birden fazla manifestte tanimli ({count}).")

    claimed_names: dict[str, str] = {}
    for manifest in manifest_list:
        names = [manifest.node_id, *manifest.compat_aliases]
        for name in names:
            if not name:
                continue
            existing = claimed_names.get(name)
            if existing is not None and existing != manifest.node_id:
                errors.append(
                    f"[{manifest.node_id}] '{name}' mevcut manifest adi/alias'i ile cakisiyor: {existing}."
                )
                continue
            claimed_names[name] = manifest.node_id

    return tuple(errors)


def ensure_valid_manifest_collection(
    manifests: Iterable[NodeManifest],
    *,
    validate_algorithm: bool = True,
) -> tuple[NodeManifest, ...]:
    """Manifest koleksiyonunu dogrula, hatada exception firlat."""
    manifest_list = tuple(manifests)
    errors = validate_manifest_collection(manifest_list, validate_algorithm=validate_algorithm)
    if errors:
        raise ManifestValidationError("\n".join(errors))
    return manifest_list


def ensure_valid_manifest(
    manifest: NodeManifest,
    *,
    validate_algorithm: bool = True,
) -> NodeManifest:
    """Tek manifesti dogrula, hatada exception firlat."""
    errors = validate_manifest(manifest, validate_algorithm=validate_algorithm)
    if errors:
        raise ManifestValidationError("\n".join(errors))
    return manifest


def _validate_ports(errors: list[str], prefix: str, manifest: NodeManifest) -> None:
    input_names = [port.name for port in manifest.input_ports]
    output_names = [port.name for port in manifest.output_ports]

    for duplicate in _duplicates(input_names):
        errors.append(f"{prefix} giris portu adi tekrar ediyor: {duplicate}.")
    for duplicate in _duplicates(output_names):
        errors.append(f"{prefix} cikis portu adi tekrar ediyor: {duplicate}.")

    overlap = sorted(set(input_names) & set(output_names))
    for port_name in overlap:
        errors.append(f"{prefix} ayni port adi hem giris hem cikista kullanilmis: {port_name}.")

    for port in [*manifest.input_ports, *manifest.output_ports]:
        if not port.name.strip():
            errors.append(f"{prefix} port name bos olamaz.")
        if not port.display_name.strip():
            errors.append(f"{prefix} '{port.name}' portu icin display_name bos olamaz.")


def _validate_config_schema(errors: list[str], prefix: str, manifest: NodeManifest) -> None:
    if not isinstance(manifest.config_schema, dict):
        return

    for field_name, spec in manifest.config_schema.items():
        if not str(field_name).strip():
            errors.append(f"{prefix} config alani adi bos olamaz.")
            continue
        if not isinstance(spec, dict):
            errors.append(f"{prefix} '{field_name}' config tanimi dict olmalidir.")
            continue
        field_type = spec.get("type")
        if field_type is None:
            errors.append(f"{prefix} '{field_name}' config taniminda type eksik.")
        elif not isinstance(field_type, str):
            errors.append(f"{prefix} '{field_name}' config type degeri string olmalidir.")


def _validate_visualization_bindings(
    errors: list[str],
    prefix: str,
    manifest: NodeManifest,
) -> None:
    output_names = {port.name for port in manifest.output_ports}
    for binding in manifest.visualization_bindings:
        if not binding.port_name.strip():
            errors.append(f"{prefix} visualization binding port_name bos olamaz.")
        elif binding.port_name not in output_names:
            errors.append(
                f"{prefix} visualization binding bilinmeyen cikis portuna bagli: {binding.port_name}."
            )
        if not binding.view_id.strip():
            errors.append(f"{prefix} visualization binding view_id bos olamaz.")


def _validate_aliases(errors: list[str], prefix: str, manifest: NodeManifest) -> None:
    alias_list = [alias for alias in manifest.compat_aliases if alias]
    for duplicate in _duplicates(alias_list):
        errors.append(f"{prefix} compat_alias tekrar ediyor: {duplicate}.")
    for alias in alias_list:
        if alias == manifest.node_id:
            errors.append(f"{prefix} compat_alias node_id ile ayni olamaz: {alias}.")

    debug_caps = [cap for cap in manifest.debug_capabilities if cap]
    for duplicate in _duplicates(debug_caps):
        errors.append(f"{prefix} debug_capability tekrar ediyor: {duplicate}.")


def _validate_algorithm_target(errors: list[str], prefix: str, manifest: NodeManifest) -> None:
    try:
        module = importlib.import_module(manifest.algorithm_import_path)
    except Exception as exc:
        errors.append(
            f"{prefix} algoritma modulu import edilemedi: {manifest.algorithm_import_path} ({exc})."
        )
        return

    kernel_cls = getattr(module, manifest.algorithm_class_name, None)
    if kernel_cls is None:
        errors.append(
            f"{prefix} algoritma sinifi bulunamadi: {manifest.algorithm_class_name}."
        )
        return

    if not isinstance(kernel_cls, type) or not issubclass(kernel_cls, AlgorithmKernel):
        errors.append(
            f"{prefix} {manifest.algorithm_class_name} AlgorithmKernel alt sinifi olmali."
        )


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counter = Counter(value for value in values if value)
    return tuple(sorted(value for value, count in counter.items() if count > 1))
