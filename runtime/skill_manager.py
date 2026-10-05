"""Manage the companion Agent Skill shipped with commerce-ui."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import tempfile
from datetime import datetime, timezone


SKILL_NAME = "compact-commerce-ui"
ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT.parent / "skill" / SKILL_NAME
MANIFEST = ".commerce-ui-managed.json"

AGENT_ROOTS = {
    "codex": pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex")) / "skills",
    "agents": pathlib.Path.home() / ".agents" / "skills",
    "openclaw": pathlib.Path.home() / ".openclaw" / "skills",
    "sealseek": pathlib.Path.home() / ".sealseek" / "skill_pool",
}


def source_digest() -> str:
    if not SOURCE.is_dir():
        return ""
    digest = hashlib.sha256()
    for path in sorted(SOURCE.rglob("*")):
        if not path.is_file() or path.name == MANIFEST or "__pycache__" in path.parts:
            continue
        digest.update(path.relative_to(SOURCE).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def resolve_root(agent: str | None, target_dir: pathlib.Path | None) -> pathlib.Path:
    if bool(agent) == bool(target_dir):
        raise ValueError("Choose exactly one of --agent or --target-dir")
    if agent:
        return AGENT_ROOTS[agent].expanduser().resolve()
    return target_dir.expanduser().resolve()


def destination(root: pathlib.Path) -> pathlib.Path:
    return root / SKILL_NAME


def _read_manifest(dest: pathlib.Path) -> dict:
    path = dest / MANIFEST
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def status(root: pathlib.Path) -> dict:
    dest = destination(root)
    digest = source_digest()
    result = {
        "skill": SKILL_NAME,
        "source": str(SOURCE),
        "source_digest": digest,
        "target_root": str(root),
        "destination": str(dest),
    }
    if not SOURCE.is_dir():
        return {**result, "state": "source-missing", "managed": False, "current": False}
    if dest.is_symlink():
        try:
            resolved = dest.resolve(strict=True)
        except FileNotFoundError:
            return {**result, "state": "broken-link", "managed": True, "current": False}
        current = resolved == SOURCE.resolve()
        return {**result, "state": "current" if current else "foreign-link", "mode": "link", "managed": current, "current": current, "resolved": str(resolved)}
    if not dest.exists():
        return {**result, "state": "absent", "managed": False, "current": False}
    manifest = _read_manifest(dest)
    managed = manifest.get("managed_by") == "commerce-ui" and manifest.get("skill") == SKILL_NAME
    if not managed:
        return {**result, "state": "unmanaged", "mode": "copy", "managed": False, "current": False}
    current = manifest.get("source_digest") == digest
    return {**result, "state": "current" if current else "stale", "mode": "copy", "managed": True, "current": current, "installed_digest": manifest.get("source_digest"), "installed_cli_version": manifest.get("cli_version")}


def _manifest(cli_version: str) -> dict:
    return {
        "managed_by": "commerce-ui",
        "skill": SKILL_NAME,
        "cli_version": cli_version,
        "source_digest": source_digest(),
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }


def _install_copy(dest: pathlib.Path, cli_version: str) -> None:
    shutil.copytree(SOURCE, dest, symlinks=False)
    (dest / MANIFEST).write_text(json.dumps(_manifest(cli_version), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def install(root: pathlib.Path, mode: str, cli_version: str) -> dict:
    if not SOURCE.is_dir():
        raise FileNotFoundError(f"Companion Skill source is missing: {SOURCE}")
    dest = destination(root)
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(f"Refusing to replace existing Skill: {dest}. Use skill status/update.")
    root.mkdir(parents=True, exist_ok=True)
    selected = "link" if mode == "auto" and os.name != "nt" else ("copy" if mode == "auto" else mode)
    if selected == "link":
        dest.symlink_to(SOURCE, target_is_directory=True)
    else:
        _install_copy(dest, cli_version)
    return {**status(root), "action": "installed"}


def update(root: pathlib.Path, cli_version: str) -> dict:
    before = status(root)
    dest = destination(root)
    if before["state"] == "absent":
        raise FileNotFoundError(f"Skill is not installed: {dest}. Use skill install first.")
    if before["state"] == "current":
        return {**before, "action": "unchanged"}
    if before.get("mode") != "copy" or not before.get("managed"):
        raise PermissionError(f"Refusing to update an unmanaged Skill: {dest}")

    state_root = pathlib.Path.home() / ".local" / "state" / "commerce-ui" / "skill-backups"
    state_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = state_root / f"{SKILL_NAME}-{stamp}"
    if backup.exists():
        raise FileExistsError(f"Backup path already exists: {backup}")
    shutil.move(str(dest), str(backup))
    try:
        with tempfile.TemporaryDirectory(prefix="commerce-ui-skill-") as directory:
            staged = pathlib.Path(directory) / SKILL_NAME
            _install_copy(staged, cli_version)
            shutil.move(str(staged), str(dest))
    except Exception:
        if not dest.exists() and backup.exists():
            shutil.move(str(backup), str(dest))
        raise
    return {**status(root), "action": "updated", "backup": str(backup)}
