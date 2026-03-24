"""Manifest scaffold CLI yardimcilari."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .scaffold import (
    build_integration_checklist_text,
    build_ai_handoff_text,
    manifest_draft_from_mapping,
    render_manifest_module,
    suggest_manifest_module,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ehcore.catalog",
        description="Manifest taslagi ve AI handoff ciktilari uretir.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    suggest_parser = subparsers.add_parser(
        "suggest-module",
        help="Kategoriye gore uygun manifest modul yolunu onerir.",
    )
    suggest_parser.add_argument("category", help="Blok kategorisi")
    suggest_parser.add_argument(
        "--node-id",
        default="",
        help="Kategori esitlenemezse fallback olarak kullanilacak node id",
    )

    render_parser = subparsers.add_parser(
        "render",
        help="JSON spec dosyasindan manifest modul ve handoff metni uretir.",
    )
    render_parser.add_argument("spec", help="Manifest draft JSON dosyasi")
    render_parser.add_argument(
        "--output",
        help="Uretilen manifest modulunun yazilacagi hedef dosya",
    )
    render_parser.add_argument(
        "--handoff-output",
        help="AI handoff metninin yazilacagi hedef dosya",
    )
    render_parser.add_argument(
        "--print-handoff",
        action="store_true",
        help="AI handoff metnini stdout'a da yazdir",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="JSON spec dosyasini okuyup entegrasyon ozeti ve checklist yazar.",
    )
    check_parser.add_argument("spec", help="Manifest draft JSON dosyasi")
    check_parser.add_argument(
        "--print-module",
        action="store_true",
        help="Onerilen manifest modul yolunu da yazdir",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "suggest-module":
        print(suggest_manifest_module(args.category, node_id=args.node_id))
        return 0

    if args.command == "render":
        return _handle_render(args)
    if args.command == "check":
        return _handle_check(args)

    parser.error("Bilinmeyen komut")
    return 2


def _handle_render(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    draft = manifest_draft_from_mapping(spec_data)

    module_text = render_manifest_module(draft)
    handoff_text = build_ai_handoff_text(draft)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(module_text, encoding="utf-8")
    else:
        print(module_text)

    if args.handoff_output:
        handoff_path = Path(args.handoff_output)
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(handoff_text, encoding="utf-8")

    if args.print_handoff:
        if args.output:
            print("=== AI Handoff ===")
        print(handoff_text)

    return 0


def _handle_check(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    draft = manifest_draft_from_mapping(spec_data)

    if args.print_module:
        print("=== Onerilen Modul ===")
        print(suggest_manifest_module(draft.category, node_id=draft.node_id))
        print()

    print("=== AI Handoff ===")
    print(build_ai_handoff_text(draft))
    print()
    print("=== Checklist ===")
    print(build_integration_checklist_text(draft))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
