#!/usr/bin/env python3
"""Stable command-line interface for Compact Commerce UI rendering."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import pathlib
import platform
import sys
import tempfile

from skill_manager import AGENT_ROOTS, SOURCE as SKILL_SOURCE
from skill_manager import install as install_skill
from skill_manager import resolve_root as resolve_skill_root
from skill_manager import source_digest as skill_source_digest
from skill_manager import status as skill_status
from skill_manager import update as update_skill
from template_packs import BUILTIN_CONTRACT, PACK_FORMAT
from template_packs import contract_from_html, discover as discover_templates
from template_packs import install as install_template
from template_packs import render_with, scaffold as scaffold_template
from template_packs import select as select_template
from template_packs import validate_html_with, validate_pack
from template_packs import update as update_template


ROOT = pathlib.Path(__file__).resolve().parent
VERSION = json.loads((ROOT.parent / "package.json").read_text(encoding="utf-8"))["version"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commerce-ui",
        description="Render and validate versioned Compact Commerce UI HTML reports.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    version = sub.add_parser("version", help="Print CLI and contract versions")
    version.add_argument("--json", action="store_true", dest="as_json")

    contracts = sub.add_parser("contracts", help="List supported UI contracts")
    contracts.add_argument("--json", action="store_true", dest="as_json")
    sub.add_parser("doctor", help="Check the installed runtime and resources")
    sub.add_parser("self-test", help="Render and validate the bundled contract fixture")

    skill = sub.add_parser("skill", help="Discover and install the companion Agent Skill")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)
    skill_source = skill_sub.add_parser("source", help="Print the canonical bundled Skill source")
    skill_source.add_argument("--json", action="store_true", dest="as_json")
    for name in ("status", "install", "update"):
        command = skill_sub.add_parser(name, help=f"{name.title()} the companion Skill")
        target = command.add_mutually_exclusive_group(required=True)
        target.add_argument("--agent", choices=sorted(AGENT_ROOTS))
        target.add_argument("--target-dir", type=pathlib.Path, help="Agent Skill root directory")
        if name == "install":
            command.add_argument("--mode", choices=("auto", "link", "copy"), default="auto")

    templates = sub.add_parser("templates", help="Discover, create, validate, and install template packs")
    templates_sub = templates.add_subparsers(dest="templates_command", required=True)
    templates_list = templates_sub.add_parser("list", help="List installed template packs")
    templates_list.add_argument("--json", action="store_true", dest="as_json")
    templates_inspect = templates_sub.add_parser("inspect", help="Inspect an installed template pack")
    templates_inspect.add_argument("template_id")
    templates_source = templates_sub.add_parser("source", help="Print an installed template pack source")
    templates_source.add_argument("template_id")
    templates_scaffold = templates_sub.add_parser("scaffold", help="Create a new editable template pack outside the CLI")
    templates_scaffold.add_argument("--id", required=True, dest="template_id")
    templates_scaffold.add_argument("--contract", required=True)
    templates_scaffold.add_argument("--output", required=True, type=pathlib.Path)
    for name in ("validate", "install", "update"):
        command = templates_sub.add_parser(name, help=f"{name.title()} an external template pack")
        command.add_argument("--path", required=True, type=pathlib.Path)
        if name in {"install", "update"}:
            command.add_argument("--trust-local-code", choices=("YES",), required=True)

    schema = sub.add_parser("schema", help="Print or copy the Report ViewModel schema")
    schema.add_argument("--contract")
    schema.add_argument("--template")
    schema.add_argument("--output", type=pathlib.Path)

    render = sub.add_parser("render", help="Render a ViewModel JSON file to self-contained HTML")
    render.add_argument("--input", required=True, type=pathlib.Path)
    render.add_argument("--output", required=True, type=pathlib.Path)
    render.add_argument("--contract")
    render.add_argument("--template")

    validate = sub.add_parser("validate", help="Run deterministic HTML contract checks")
    validate.add_argument("html", type=pathlib.Path)
    validate.add_argument("--json", action="store_true", dest="as_json")
    validate.add_argument("--contract")
    validate.add_argument("--template")
    return parser


def command_version(as_json: bool) -> int:
    contracts = [pack.contract for pack in discover_templates().values()]
    info = {"cli": "commerce-ui", "version": VERSION, "template_pack_format": PACK_FORMAT, "contracts": contracts}
    print(json.dumps(info, ensure_ascii=False) if as_json else "\n".join([f"commerce-ui {VERSION}", *contracts]))
    return 0


def command_doctor() -> int:
    packs = discover_templates()
    checks = {
        "python": platform.python_version(),
        "jsonschema": importlib.metadata.version("jsonschema"),
        "root": str(ROOT),
        "version_file": (ROOT / "VERSION").is_file(),
        "template_packs": all(all(path.is_file() for path in (pack.schema, pack.template, pack.renderer, pack.validator, pack.fixture)) for pack in packs.values()),
        "template_scaffold": (ROOT / "scaffolds" / "template-pack" / "manifest.json").is_file(),
        "companion_skill": SKILL_SOURCE.is_dir(),
    }
    ok = all(v for k, v in checks.items() if k not in {"python", "root"})
    companion = {
        "name": "compact-commerce-ui",
        "source": str(SKILL_SOURCE),
        "source_digest": skill_source_digest(),
        "install": "commerce-ui skill install --agent codex",
        "generic_install": "commerce-ui skill install --target-dir <agent-skill-root>",
    }
    print(json.dumps({"ok": ok, "cli_version": VERSION, "contracts": [pack.contract for pack in packs.values()], "template_packs": [pack.as_dict() for pack in packs.values()], "checks": checks, "companion_skill": companion}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def command_self_test() -> int:
    results = []
    with tempfile.TemporaryDirectory(prefix="commerce-ui-self-test-") as directory:
        for pack in discover_templates().values():
            output = pathlib.Path(directory) / f"{pack.pack_id}.html"
            rendered = render_with(pack, pack.fixture, output, VERSION)
            validation = validate_html_with(pack, output)
            results.append({"ok": validation["ok"], "pack": pack.as_dict(), "render": rendered, "validation": validation})
    result = {"ok": all(item["ok"] for item in results), "cli_version": VERSION, "packs": results}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def command_schema(contract: str, template_id: str | None, output: pathlib.Path | None) -> int:
    pack = select_template(template_id, contract)
    content = pack.schema.read_text(encoding="utf-8")
    if output:
        target = output.expanduser().resolve()
        if target.exists():
            print(f"Refusing to overwrite existing output: {target}", file=sys.stderr)
            return 3
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"Schema written: {target}")
    else:
        print(content)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "version":
        return command_version(args.as_json)
    if args.command == "contracts":
        packs = list(discover_templates().values())
        if args.as_json:
            print(json.dumps({"contracts": [pack.contract for pack in packs], "template_packs": [pack.as_dict() for pack in packs]}, ensure_ascii=False, indent=2))
        else:
            print("\n".join(pack.contract for pack in packs))
        return 0
    if args.command == "doctor":
        return command_doctor()
    if args.command == "self-test":
        return command_self_test()
    if args.command == "skill":
        if args.skill_command == "source":
            result = {
                "skill": "compact-commerce-ui",
                "source": str(SKILL_SOURCE),
                "source_digest": skill_source_digest(),
                "install_hint": "commerce-ui skill install --target-dir <agent-skill-root>",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.as_json else SKILL_SOURCE)
            return 0 if SKILL_SOURCE.is_dir() else 1
        try:
            root = resolve_skill_root(args.agent, args.target_dir)
            if args.skill_command == "status":
                result = skill_status(root)
            elif args.skill_command == "install":
                result = install_skill(root, args.mode, VERSION)
            else:
                result = update_skill(root, VERSION)
        except (OSError, ValueError) as exc:
            print(f"Companion Skill {args.skill_command} failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("current") else 1
    if args.command == "templates":
        try:
            packs = discover_templates()
            if args.templates_command == "list":
                values = [pack.as_dict() for pack in packs.values()]
                if args.as_json:
                    print(json.dumps({"template_pack_format": PACK_FORMAT, "template_packs": values}, ensure_ascii=False, indent=2))
                else:
                    for value in values:
                        print(f"{value['id']}\t{value['contract']}\t{value['version']}\t{value['title']}")
                return 0
            if args.templates_command in {"inspect", "source"}:
                pack = select_template(args.template_id)
                print(str(pack.root) if args.templates_command == "source" else json.dumps(pack.as_dict(), ensure_ascii=False, indent=2))
                return 0
            if args.templates_command == "scaffold":
                result = scaffold_template(args.template_id, args.contract, args.output)
            elif args.templates_command == "validate":
                result = validate_pack(args.path, VERSION)
            elif args.templates_command == "update":
                result = update_template(args.path, VERSION)
            else:
                result = install_template(args.path, VERSION)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("ok") else 1
        except (OSError, ValueError, json.JSONDecodeError, SyntaxError) as exc:
            print(f"Template pack {args.templates_command} failed: {exc}", file=sys.stderr)
            return 1
    if args.command == "schema":
        try:
            return command_schema(args.contract, args.template, args.output)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"Schema lookup failed: {exc}", file=sys.stderr)
            return 2
    if args.command == "render":
        try:
            input_path = args.input.expanduser().resolve()
            document = json.loads(input_path.read_text(encoding="utf-8"))
            input_contract = document.get("contract")
            if args.contract and input_contract and args.contract != input_contract:
                raise ValueError(f"--contract {args.contract} does not match input contract {input_contract}")
            pack = select_template(args.template, args.contract or input_contract)
            result = render_with(pack, input_path, args.output, VERSION)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"Render failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate":
        try:
            detected = contract_from_html(args.html)
            if args.contract and args.contract != detected:
                raise ValueError(f"--contract {args.contract} does not match HTML contract {detected}")
            pack = select_template(args.template, args.contract or detected)
            result = validate_html_with(pack, args.html)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"Validation failed: {exc}", file=sys.stderr)
            return 1
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result["ok"]:
            print(f"Commerce UI validation OK: {result['path']}")
        else:
            print("Commerce UI validation failed:", file=sys.stderr)
            for error in result["errors"]:
                print(f"- {error}", file=sys.stderr)
        return 0 if result["ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
