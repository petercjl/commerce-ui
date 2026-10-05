"""Starter renderer for a commerce-ui template pack."""

from __future__ import annotations

import base64
import html
import json
import pathlib
import re
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent
CONTRACT = "__CONTRACT__"


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def slug(value: Any) -> str:
    result = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "")).strip("-")
    if not result:
        raise ValueError("identifier cannot be empty")
    return result


def mime(blob: bytes) -> str:
    if blob.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if blob.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if blob.startswith((b"GIF87a", b"GIF89a")): return "image/gif"
    if blob.startswith(b"RIFF") and blob[8:12] == b"WEBP": return "image/webp"
    if blob.startswith(b"<svg") or b"<svg" in blob[:256]: return "image/svg+xml"
    raise ValueError("unsupported image format")


def assets_for(raw: Any, base: pathlib.Path) -> dict[str, dict[str, str]]:
    if raw is None: return {}
    items = [dict(value, id=key) for key, value in raw.items()] if isinstance(raw, dict) else raw
    if not isinstance(items, list): raise ValueError("assets must be an object or array")
    result = {}
    for item in items:
        asset_id, value = str(item.get("id", "")), str(item.get("path", ""))
        if not asset_id or not value: raise ValueError("asset requires id and path")
        if re.match(r"https?://", value, re.I): raise ValueError("remote assets are forbidden")
        path = pathlib.Path(value).expanduser()
        path = (base / path).resolve() if not path.is_absolute() else path.resolve()
        blob = path.read_bytes()
        result[asset_id] = {"src": f"data:{mime(blob)};base64,{base64.b64encode(blob).decode()}", "alt": str(item.get("alt", ""))}
    return result


class Renderer:
    def __init__(self, assets: dict[str, dict[str, str]]) -> None:
        self.assets = assets

    def blocks(self, values: Any) -> str:
        if not isinstance(values, list): raise ValueError("blocks must be an array")
        return "".join(self.block(value) for value in values)

    def media(self, asset_id: str, caption: str = "") -> str:
        asset = self.assets.get(str(asset_id))
        if not asset: raise ValueError(f"unknown asset_id: {asset_id}")
        note = f"<figcaption>{esc(caption)}</figcaption>" if caption else ""
        return f'<figure class="media searchable"><img src="{asset["src"]}" alt="{esc(asset["alt"])}">{note}</figure>'

    def block(self, value: Any) -> str:
        if not isinstance(value, dict): raise ValueError("block must be an object")
        kind = value.get("type")
        if kind == "text":
            paragraphs = value.get("paragraphs", [value.get("text", "")])
            return '<div class="prose">' + "".join(f'<p class="searchable">{esc(x)}</p>' for x in paragraphs) + "</div>"
        if kind == "callout": return f'<div class="callout searchable">{esc(value.get("text", ""))}</div>'
        if kind == "card": return f'<article class="card searchable"><div class="card-head">{esc(value.get("title", ""))}</div><div class="card-body">{self.blocks(value.get("blocks", []))}</div></article>'
        if kind == "grid":
            columns = max(1, min(4, int(value.get("columns", 2))))
            return f'<section class="grid grid-{columns}">{"".join(self.block(x) for x in value.get("items", []))}</section>'
        if kind == "image": return self.media(value.get("asset_id", ""), value.get("caption", ""))
        if kind == "gallery": return '<section class="gallery">' + "".join(self.media(x) for x in value.get("asset_ids", [])) + "</section>"
        if kind == "key_values":
            return '<div class="kv">' + "".join(f'<div class="searchable"><span>{esc(x.get("label", ""))}</span><b>{esc(x.get("value", "—"))}</b></div>' for x in value.get("items", [])) + "</div>"
        if kind == "table":
            columns = value.get("columns", [])
            if not columns: raise ValueError("table requires columns")
            head = "".join(f'<th>{esc(x.get("label", x.get("key", "")))}</th>' for x in columns)
            rows = "".join('<tr class="searchable">' + "".join(f'<td>{esc(row.get(x.get("key"), "—"))}</td>' for x in columns) + "</tr>" for row in value.get("rows", []))
            return f'<article class="table-card"><div class="card-head">{esc(value.get("title", ""))}</div><div class="table-wrap"><table class="data"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></article>'
        raise ValueError(f"unsupported block type: {kind}")


def render_file(input_value, output_value, *, cli_version: str, pack: dict) -> dict:
    input_path = pathlib.Path(input_value).expanduser().resolve()
    output_path = pathlib.Path(output_value).expanduser().resolve()
    if output_path.exists(): raise ValueError(f"refusing to overwrite existing output: {output_path}")
    document = json.loads(input_path.read_text(encoding="utf-8"))
    if document.get("contract") != CONTRACT: raise ValueError(f"contract must be {CONTRACT}")
    views = document.get("views")
    if not isinstance(views, list) or len(views) < 2: raise ValueError("at least two views are required")
    renderer = Renderer(assets_for(document.get("assets"), input_path.parent))
    nav, rendered, ids = [], [], []
    for index, view in enumerate(views):
        view_id = slug(view.get("id")); ids.append(view_id)
        nav.append(f'<button type="button" data-view-target="{esc(view_id)}">{esc(view.get("label", view_id))}</button>')
        hidden = "" if index == 0 else " hidden"
        heading = f'<div class="heading"><h1>{esc(view.get("title", ""))}</h1><p>{esc(view.get("subtitle", ""))}</p></div>'
        rendered.append(f'<section class="view" data-view="{esc(view_id)}"{hidden}>{heading}{renderer.blocks(view.get("blocks", []))}</section>')
    meta, shell = document.get("meta", {}), document.get("shell", {})
    if not meta.get("title"): raise ValueError("meta.title is required")
    status = "".join(f'<div>{esc(x)}</div>' for x in shell.get("status", []))
    search = f'<input class="search" id="search" type="search" placeholder="{esc(shell.get("search_placeholder", "搜索当前视图"))}">' if shell.get("search", False) else ""
    date = f'<div class="date">{esc(shell.get("date_range"))}</div>' if shell.get("date_range") else ""
    replacements = {"__CLI_VERSION__": esc(cli_version), "__CONTRACT__": esc(CONTRACT), "__TITLE__": esc(meta["title"]), "__SUBTITLE__": esc(meta.get("subtitle", "")), "__BRAND_MARK__": esc(shell.get("brand_mark", "UI")), "__BRAND_TITLE__": esc(shell.get("brand_title", meta["title"])), "__BRAND_SUBTITLE__": esc(shell.get("brand_subtitle", pack.get("title", ""))), "__NAV_LABEL__": esc(shell.get("nav_label", "报告视图")), "__NAV__": "".join(nav), "__STATUS__": status, "__TOOLS__": search + date, "__VIEWS__": "".join(rendered), "__FOOTER__": esc(meta.get("footer", "")), "__VIEW_IDS__": json.dumps(ids, ensure_ascii=False)}
    output = (ROOT / "template.html").read_text(encoding="utf-8")
    for marker, replacement in replacements.items(): output = output.replace(marker, replacement)
    output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_text(output, encoding="utf-8")
    return {"ok": True, "output": str(output_path), "cli_version": cli_version, "contract": CONTRACT, "template_pack": pack.get("id"), "views": len(views), "assets_embedded": len(renderer.assets), "bytes": output_path.stat().st_size}
