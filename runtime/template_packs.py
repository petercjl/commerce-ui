"""Discovery, validation, scaffolding, and installation for UI template packs."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import py_compile
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from jsonschema import Draft202012Validator


ROOT = pathlib.Path(__file__).resolve().parent
PACK_FORMAT = "commerce-ui-template-pack@1"
BUNDLED_PACK_ROOT = ROOT / "template-packs"
PACK_ROOT = pathlib.Path(os.environ.get("COMMERCE_UI_DATA_ROOT", pathlib.Path.home() / ".local" / "share" / "commerce-ui")) / "template-packs"
SCAFFOLD_ROOT = ROOT / "scaffolds" / "template-pack"
BUILTIN_ID = "compact-workbench"
BUILTIN_CONTRACT = "compact-workbench@1.0"
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


@dataclass(frozen=True)
class TemplatePack:
    pack_id: str
    contract: str
    version: str
    title: str
    description: str
    root: pathlib.Path
    schema: pathlib.Path
    template: pathlib.Path
    renderer: pathlib.Path
    validator: pathlib.Path
    fixture: pathlib.Path
    builtin: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.pack_id,
            "contract": self.contract,
            "version": self.version,
            "title": self.title,
            "description": self.description,
            "source": str(self.root),
            "builtin": self.builtin,
        }


def builtin_pack() -> TemplatePack:
    return TemplatePack(
        pack_id=BUILTIN_ID,
        contract=BUILTIN_CONTRACT,
        version="1.0.7",
        title="Compact Commerce Workbench",
        description="Compact ecommerce operations dashboards and modular business workbenches.",
        root=ROOT,
        schema=ROOT / "schema" / "compact-workbench-1.0.schema.json",
        template=ROOT / "templates" / "workbench.html",
        renderer=ROOT / "renderer.py",
        validator=ROOT / "validator.py",
        fixture=ROOT / "tests" / "minimal.json",
        builtin=True,
    )


def _safe_file(root: pathlib.Path, value: str, label: str) -> pathlib.Path:
    candidate = pathlib.Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} must be a safe pack-relative path")
    resolved = (root / candidate).resolve()
    if root.resolve() not in resolved.parents:
        raise ValueError(f"{label} escapes the template pack")
    return resolved


def load_manifest(root_value: pathlib.Path | str) -> TemplatePack:
    root = pathlib.Path(root_value).expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"template pack manifest not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("pack_format") != PACK_FORMAT:
        raise ValueError(f"pack_format must be {PACK_FORMAT}")
    pack_id = str(data.get("id", ""))
    contract = str(data.get("contract", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}[a-z0-9]", pack_id):
        raise ValueError("template pack id must be 3-64 lowercase letters, digits, or hyphens")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*@[0-9]+\.[0-9]+", contract):
        raise ValueError("contract must look like evidence-analysis@1.0")
    files = data.get("files") or {}
    return TemplatePack(
        pack_id=pack_id,
        contract=contract,
        version=str(data.get("version", "0.0.0")),
        title=str(data.get("title") or pack_id),
        description=str(data.get("description") or ""),
        root=root,
        schema=_safe_file(root, str(files.get("schema", "schema.json")), "schema"),
        template=_safe_file(root, str(files.get("template", "template.html")), "template"),
        renderer=_safe_file(root, str(files.get("renderer", "renderer.py")), "renderer"),
        validator=_safe_file(root, str(files.get("validator", "validator.py")), "validator"),
        fixture=_safe_file(root, str(files.get("fixture", "fixture.json")), "fixture"),
    )


def discover() -> dict[str, TemplatePack]:
    packs = {BUILTIN_ID: builtin_pack()}
    for library in dict.fromkeys((BUNDLED_PACK_ROOT, PACK_ROOT)):
        if not library.is_dir():
            continue
        for child in sorted(library.iterdir()):
            if not child.is_dir() or not (child / "manifest.json").is_file():
                continue
            pack = load_manifest(child)
            if pack.pack_id in packs and (library == BUNDLED_PACK_ROOT or packs[pack.pack_id].contract != pack.contract):
                raise ValueError(f"duplicate template pack id: {pack.pack_id}")
            if any(existing.contract == pack.contract and existing.pack_id != pack.pack_id for existing in packs.values()):
                raise ValueError(f"duplicate template contract: {pack.contract}")
            packs[pack.pack_id] = pack
    return packs


def select(pack_id: str | None = None, contract: str | None = None) -> TemplatePack:
    packs = discover()
    if pack_id:
        if pack_id not in packs:
            raise ValueError(f"unknown template pack: {pack_id}")
        pack = packs[pack_id]
        if contract and pack.contract != contract:
            raise ValueError(f"template {pack_id} provides {pack.contract}, not {contract}")
        return pack
    if contract:
        matches = [pack for pack in packs.values() if pack.contract == contract]
        if not matches:
            raise ValueError(f"unsupported contract: {contract}")
        return matches[0]
    return packs[BUILTIN_ID]


def _load_module(path: pathlib.Path, role: str):
    token = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(f"commerce_ui_pack_{role}_{token}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {role}: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_with(pack: TemplatePack, input_path: pathlib.Path, output_path: pathlib.Path, cli_version: str) -> dict:
    document = json.loads(pathlib.Path(input_path).read_text(encoding="utf-8"))
    schema = json.loads(pack.schema.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda item: list(item.path))
    if errors:
        details = [f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}" for error in errors[:12]]
        raise ValueError("ViewModel schema validation failed: " + "; ".join(details))
    if pack.builtin:
        from renderer import render_file

        return render_file(input_path, output_path)
    module = _load_module(pack.renderer, "renderer")
    if not hasattr(module, "render_file"):
        raise ValueError(f"renderer does not define render_file: {pack.renderer}")
    result = module.render_file(input_path, output_path, cli_version=cli_version, pack=pack.as_dict())
    if not isinstance(result, dict):
        raise ValueError("renderer.render_file must return an object")
    return result


def validate_html_with(pack: TemplatePack, html_path: pathlib.Path) -> dict:
    if pack.builtin:
        from validator import validate_file

        return validate_file(html_path)
    module = _load_module(pack.validator, "validator")
    if not hasattr(module, "validate_file"):
        raise ValueError(f"validator does not define validate_file: {pack.validator}")
    result = module.validate_file(html_path, pack=pack.as_dict())
    if not isinstance(result, dict) or "ok" not in result:
        raise ValueError("validator.validate_file must return an object containing ok")
    return result


def contract_from_html(path_value: pathlib.Path | str) -> str:
    path = pathlib.Path(path_value).expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    match = re.search(r'<meta\s+name=["\']commerce-ui-contract["\']\s+content=["\']([^"\']+)', text, re.I)
    if not match:
        raise ValueError("HTML does not declare commerce-ui-contract metadata")
    return match.group(1)


def validate_pack(root_value: pathlib.Path | str, cli_version: str) -> dict:
    pack = load_manifest(root_value)
    required = [pack.schema, pack.template, pack.renderer, pack.validator, pack.fixture]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"template pack files missing: {missing}")
    schema = json.loads(pack.schema.read_text(encoding="utf-8"))
    fixture = json.loads(pack.fixture.read_text(encoding="utf-8"))
    if fixture.get("contract") != pack.contract:
        raise ValueError("fixture contract does not match manifest contract")
    expected = (((schema.get("properties") or {}).get("contract") or {}).get("const"))
    if expected != pack.contract:
        raise ValueError("schema contract const does not match manifest contract")
    py_compile.compile(str(pack.renderer), doraise=True)
    py_compile.compile(str(pack.validator), doraise=True)
    with tempfile.TemporaryDirectory(prefix="commerce-ui-pack-test-") as directory:
        output = pathlib.Path(directory) / "fixture.html"
        rendered = render_with(pack, pack.fixture, output, cli_version)
        validation = validate_html_with(pack, output)
    return {
        "ok": bool(validation.get("ok")),
        "pack": pack.as_dict(),
        "render": rendered,
        "validation": validation,
    }


def scaffold(pack_id: str, contract: str, output_value: pathlib.Path | str) -> dict:
    output = pathlib.Path(output_value).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing scaffold output: {output}")
    if not SCAFFOLD_ROOT.is_dir():
        raise FileNotFoundError(f"template pack scaffold is missing: {SCAFFOLD_ROOT}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}[a-z0-9]", pack_id):
        raise ValueError("template pack id must be 3-64 lowercase letters, digits, or hyphens")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*@[0-9]+\.[0-9]+", contract):
        raise ValueError("contract must look like evidence-analysis@1.0")
    shutil.copytree(SCAFFOLD_ROOT, output, ignore=COPY_IGNORE)
    for path in output.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        content = content.replace("__PACK_ID__", pack_id).replace("__CONTRACT__", contract)
        path.write_text(content, encoding="utf-8")
    return {"ok": True, "output": str(output), "id": pack_id, "contract": contract}


def install(root_value: pathlib.Path | str, cli_version: str) -> dict:
    result = validate_pack(root_value, cli_version)
    if not result["ok"]:
        raise ValueError("template pack self-test failed")
    pack = load_manifest(root_value)
    destination = PACK_ROOT / pack.pack_id
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite installed template pack: {destination}")
    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pack.root, destination, ignore=COPY_IGNORE)
    installed = load_manifest(destination)
    return {"ok": True, "action": "installed", "pack": installed.as_dict()}


def update(root_value: pathlib.Path | str, cli_version: str) -> dict:
    result = validate_pack(root_value, cli_version)
    if not result["ok"]:
        raise ValueError("template pack self-test failed")
    incoming = load_manifest(root_value)
    if incoming.pack_id == BUILTIN_ID:
        raise ValueError("the built-in template pack is updated with the commerce-ui release, not template update")
    destination = PACK_ROOT / incoming.pack_id
    previous = destination if destination.is_dir() else BUNDLED_PACK_ROOT / incoming.pack_id
    if not previous.is_dir():
        raise FileNotFoundError(f"installed template pack not found: {destination}")
    installed = load_manifest(previous)
    if installed.pack_id != incoming.pack_id:
        raise ValueError("installed and incoming template pack ids do not match")
    backup_root = pathlib.Path.home() / ".local" / "state" / "commerce-ui" / "template-pack-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / f"{incoming.pack_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if backup.exists():
        raise FileExistsError(f"template backup already exists: {backup}")
    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    if destination.is_dir():
        shutil.move(str(destination), str(backup))
    else:
        shutil.copytree(previous, backup, ignore=COPY_IGNORE)
    try:
        shutil.copytree(incoming.root, destination, ignore=COPY_IGNORE)
    except Exception:
        if not destination.exists() and backup.exists():
            shutil.move(str(backup), str(destination))
        raise
    return {"ok": True, "action": "updated", "backup": str(backup), "pack": load_manifest(destination).as_dict()}
