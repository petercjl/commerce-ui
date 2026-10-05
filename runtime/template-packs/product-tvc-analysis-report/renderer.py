"""Renderer for the Product TVC Analysis Report template pack."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import pathlib
import re
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent
CONTRACT = "product-tvc-analysis-report@1.0"
EVIDENCE_LEVEL_LABELS = {"direct": "直接证据", "derived": "推导证据", "illustrative": "示意素材"}


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def slug(value: Any) -> str:
    result = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "")).strip("-")
    if not result:
        raise ValueError("identifier cannot be empty")
    return result


def clamp_score(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def image_mime(blob: bytes) -> str:
    if blob.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if blob.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if blob.startswith(b"RIFF") and blob[8:12] == b"WEBP":
        return "image/webp"
    if blob.startswith(b"<svg") or b"<svg" in blob[:256]:
        lowered = blob.lower()
        if b"<script" in lowered or re.search(rb"\son[a-z]+\s*=", lowered):
            raise ValueError("unsafe SVG scripting is forbidden")
        if re.search(rb"(?:href|src)\s*=\s*['\"]https?://", lowered):
            raise ValueError("external SVG dependencies are forbidden")
        return "image/svg+xml"
    raise ValueError("unsupported image format")


def assets_for(raw: Any, base: pathlib.Path) -> dict[str, dict[str, str]]:
    if raw is None:
        return {}
    items = [dict(value, id=key) for key, value in raw.items()] if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("assets must be an object or array")
    result: dict[str, dict[str, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each asset must be an object")
        asset_id, value = str(item.get("id", "")), str(item.get("path", ""))
        if not asset_id or not value:
            raise ValueError("asset requires id and path")
        if asset_id in result:
            raise ValueError(f"duplicate asset id: {asset_id}")
        if re.match(r"https?://", value, re.I):
            raise ValueError(f"remote assets are forbidden: {asset_id}")
        path = pathlib.Path(value).expanduser()
        path = (base / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_file():
            raise ValueError(f"asset not found: {asset_id} -> {path}")
        blob = path.read_bytes()
        mime = image_mime(blob)
        result[asset_id] = {
            "src": f"data:{mime};base64,{base64.b64encode(blob).decode('ascii')}",
            "alt": str(item.get("alt", "")),
            "caption": str(item.get("caption", "")),
            "role": str(item.get("role", "content")),
            "semantic_label": str(item.get("semantic_label", "")),
            "evidence_level": str(item.get("evidence_level", "direct")),
            "sha256": hashlib.sha256(blob).hexdigest(),
        }
    return result


class Renderer:
    def __init__(self, assets: dict[str, dict[str, str]]) -> None:
        self.assets = assets

    def blocks(self, values: Any) -> str:
        if not isinstance(values, list):
            raise ValueError("blocks must be an array")
        return "".join(self.block(value) for value in values)

    def asset(self, asset_id: Any) -> dict[str, str]:
        asset = self.assets.get(str(asset_id))
        if not asset:
            raise ValueError(f"unknown asset_id: {asset_id}")
        return asset

    def media(self, asset_id: Any, caption: str = "", class_name: str = "media") -> str:
        asset = self.asset(asset_id)
        note = caption or asset.get("caption", "")
        note_html = f"<figcaption>{esc(note)}</figcaption>" if note else ""
        level = EVIDENCE_LEVEL_LABELS.get(asset.get("evidence_level", ""), asset.get("evidence_level", ""))
        meta = " · ".join(x for x in [asset.get("role"), level] if x)
        meta_html = f'<span class="media-meta">{esc(meta)}</span>' if meta else ""
        return (
            f'<figure class="{esc(class_name)} searchable">'
            f'<img src="{asset["src"]}" alt="{esc(asset["alt"])}">'
            f"{note_html}{meta_html}</figure>"
        )

    def pills(self, values: Any) -> str:
        if not isinstance(values, list):
            return ""
        return '<div class="pills">' + "".join(f"<span>{esc(value)}</span>" for value in values if value) + "</div>"

    def score(self, value: Any) -> str:
        score = clamp_score(value)
        return f'<div class="score"><span style="width:{score}%"></span></div><b class="score-value">{score}</b>'

    def block(self, value: Any) -> str:
        if not isinstance(value, dict):
            raise ValueError("block must be an object")
        kind = value.get("type")
        if kind == "hero":
            recommendation = value.get("recommendation") or {}
            image = self.media(value.get("asset_id"), value.get("caption", ""), "hero-media") if value.get("asset_id") else ""
            rec = ""
            if recommendation:
                rec = (
                    '<div class="recommendation">'
                    f'<span>{esc(recommendation.get("label", "推荐方向"))}</span>'
                    f'<h2>{esc(recommendation.get("title", ""))}</h2>'
                    f'<p>{esc(recommendation.get("reason", ""))}</p></div>'
                )
            return (
                '<section class="hero searchable"><div class="hero-copy">'
                f'<div class="eyebrow">{esc(value.get("eyebrow", ""))}</div>'
                f'<h2>{esc(value.get("title", ""))}</h2>'
                f'<p>{esc(value.get("subtitle", ""))}</p>'
                f'{self.pills(value.get("badges", []))}{rec}</div>{image}</section>'
            )
        if kind == "text":
            paragraphs = value.get("paragraphs", [value.get("text", "")])
            return '<div class="prose">' + "".join(f'<p class="searchable">{esc(x)}</p>' for x in paragraphs if x) + "</div>"
        if kind == "callout":
            tone = slug(value.get("tone", "info"))
            title = f"<strong>{esc(value.get('title'))}</strong>" if value.get("title") else ""
            return f'<section class="callout tone-{tone} searchable">{title}<p>{esc(value.get("text", ""))}</p></section>'
        if kind == "card":
            return (
                '<article class="card searchable">'
                f'<div class="card-head"><h2>{esc(value.get("title", ""))}</h2><span>{esc(value.get("subtitle", ""))}</span></div>'
                f'<div class="card-body">{self.blocks(value.get("blocks", []))}</div></article>'
            )
        if kind == "grid":
            columns = max(1, min(4, int(value.get("columns", 2))))
            return f'<section class="grid grid-{columns}">' + "".join(self.block(x) for x in value.get("items", [])) + "</section>"
        if kind == "image":
            return self.media(value.get("asset_id", ""), value.get("caption", ""))
        if kind == "gallery":
            title = f'<div class="section-head"><h2>{esc(value.get("title"))}</h2></div>' if value.get("title") else ""
            media = "".join(self.media(x, class_name="gallery-media") for x in value.get("asset_ids", []))
            return f'<section class="section-card">{title}<div class="gallery">{media}</div></section>'
        if kind == "key_values":
            rows = "".join(
                f'<div class="searchable"><span>{esc(x.get("label", ""))}</span><b>{esc(x.get("value", "—"))}</b></div>'
                for x in value.get("items", [])
            )
            return f'<div class="kv">{rows}</div>'
        if kind == "table":
            return self.table(value)
        if kind == "fact_cards":
            cards = "".join(
                '<article class="fact-card searchable">'
                f'<div class="fact-top"><code>{esc(item.get("id", ""))}</code><span>{esc(item.get("evidence_type", ""))}</span></div>'
                f'<p>{esc(item.get("statement", ""))}</p>'
                f'<div class="fact-foot"><b>{esc(item.get("creative_use", ""))}</b><span>置信度 {esc(item.get("confidence", "—"))}</span></div></article>'
                for item in value.get("items", [])
            )
            return self.section(value.get("title", "事实账本"), f'<div class="fact-grid">{cards}</div>')
        if kind == "value_map":
            rows = "".join(
                '<article class="value-row searchable">'
                f'<div><span>产品特征</span><b>{esc(item.get("feature", ""))}</b></div>'
                f'<i>→</i><div><span>实际优势</span><b>{esc(item.get("advantage", ""))}</b></div>'
                f'<i>→</i><div><span>用户收益</span><b>{esc(item.get("benefit", ""))}</b><small>{esc(item.get("emotion", ""))}</small></div>'
                f'<i>→</i><div><span>画面证明</span><b>{esc(item.get("proof", ""))}</b></div></article>'
                for item in value.get("items", [])
            )
            return self.section(value.get("title", "价值翻译"), f'<div class="value-list">{rows}</div>')
        if kind == "audiences":
            cards = "".join(self.audience(item) for item in value.get("items", []))
            return self.section(value.get("title", "目标人群"), f'<div class="strategy-grid">{cards}</div>')
        if kind == "scenes":
            cards = "".join(self.scene(item) for item in value.get("items", []))
            return self.section(value.get("title", "优先场景"), f'<div class="strategy-grid">{cards}</div>')
        if kind == "directions":
            cards = "".join(self.direction(item) for item in value.get("items", []))
            return self.section(value.get("title", "TVC 方向"), f'<div class="direction-list">{cards}</div>')
        if kind == "boundaries":
            items = "".join(f'<li class="searchable">{esc(item)}</li>' for item in value.get("items", []))
            return self.section(value.get("title", "广告表达边界"), f'<ul class="boundary-list">{items}</ul>')
        raise ValueError(f"unsupported block type: {kind}")

    def section(self, title: str, content: str) -> str:
        return f'<section class="section-card"><div class="section-head"><h2>{esc(title)}</h2></div>{content}</section>'

    def table(self, value: dict[str, Any]) -> str:
        columns = value.get("columns", [])
        if not isinstance(columns, list) or not columns:
            raise ValueError("table requires column definitions")
        head = "".join(f'<th>{esc(x.get("label", x.get("key", "")))}</th>' for x in columns)
        rows = "".join(
            '<tr class="searchable">' + "".join(f'<td>{esc(row.get(x.get("key"), "—"))}</td>' for x in columns) + "</tr>"
            for row in value.get("rows", [])
        )
        return f'<section class="section-card"><div class="section-head"><h2>{esc(value.get("title", ""))}</h2></div><div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></section>'

    def audience(self, item: dict[str, Any]) -> str:
        return (
            '<article class="strategy-card searchable"><div class="strategy-title">'
            f'<h3>{esc(item.get("label", ""))}</h3><span>{esc(item.get("basis", ""))}</span></div>'
            f'<p><b>需要：</b>{esc(item.get("need", ""))}</p><p><b>痛点：</b>{esc(item.get("pain", ""))}</p>'
            f'<p><b>渴望：</b>{esc(item.get("desire", ""))}</p><div class="score-line">{self.score(item.get("score"))}</div></article>'
        )

    def scene(self, item: dict[str, Any]) -> str:
        return (
            '<article class="strategy-card scene-card searchable"><div class="strategy-title">'
            f'<h3>{esc(item.get("title", ""))}</h3><span>{esc(item.get("time", ""))}</span></div>'
            f'<div class="scene-place">{esc(item.get("place", ""))}</div><p><b>张力：</b>{esc(item.get("tension", ""))}</p>'
            f'<p><b>产品动作：</b>{esc(item.get("action", ""))}</p><p><b>结果：</b>{esc(item.get("result", ""))}</p>'
            f'<div class="score-line">{self.score(item.get("score"))}</div></article>'
        )

    def direction(self, item: dict[str, Any]) -> str:
        selected = bool(item.get("selected"))
        selected_class = " selected" if selected else ""
        selected_badge = '<span class="selected-badge">推荐</span>' if selected else ""
        return (
            f'<article class="direction-card searchable{selected_class}"><div class="direction-rank">#{esc(item.get("rank", "—"))}</div>'
            f'<div class="direction-main"><div class="strategy-title"><h3>{esc(item.get("title", ""))}</h3>{selected_badge}</div>'
            f'<p class="proposition">{esc(item.get("proposition", ""))}</p><div class="direction-meta">'
            f'<span>人群：{esc(item.get("audience", ""))}</span><span>场景：{esc(item.get("scene", ""))}</span><span>类型：{esc(item.get("type", ""))}</span></div>'
            f'<p><b>记忆钩子：</b>{esc(item.get("hook", ""))}</p><p><b>选择理由：</b>{esc(item.get("reason", ""))}</p></div>'
            f'<div class="direction-score">{self.score(item.get("score"))}</div></article>'
        )


def render_file(input_value, output_value, *, cli_version: str, pack: dict) -> dict:
    input_path = pathlib.Path(input_value).expanduser().resolve()
    output_path = pathlib.Path(output_value).expanduser().resolve()
    if output_path.exists():
        raise ValueError(f"refusing to overwrite existing output: {output_path}")
    document = json.loads(input_path.read_text(encoding="utf-8"))
    if document.get("contract") != CONTRACT:
        raise ValueError(f"contract must be {CONTRACT}")
    views = document.get("views")
    if not isinstance(views, list) or len(views) < 2:
        raise ValueError("at least two views are required")
    renderer = Renderer(assets_for(document.get("assets"), input_path.parent))
    nav, rendered, ids = [], [], []
    for index, view in enumerate(views):
        view_id = slug(view.get("id"))
        if view_id in ids:
            raise ValueError(f"duplicate view id: {view_id}")
        ids.append(view_id)
        nav.append(f'<button type="button" data-view-target="{esc(view_id)}"><span></span>{esc(view.get("label", view_id))}</button>')
        hidden = "" if index == 0 else " hidden"
        badge = f'<span class="view-badge">{esc(view.get("badge"))}</span>' if view.get("badge") else ""
        heading = f'<div class="heading"><div><div class="eyebrow">{esc(view.get("eyebrow", ""))}</div><h1>{esc(view.get("title", ""))}</h1><p>{esc(view.get("subtitle", ""))}</p></div>{badge}</div>'
        rendered.append(f'<section class="view" data-view="{esc(view_id)}" id="view-{esc(view_id)}" tabindex="-1"{hidden}>{heading}{renderer.blocks(view.get("blocks", []))}</section>')
    meta, shell = document.get("meta", {}), document.get("shell", {})
    if not meta.get("title"):
        raise ValueError("meta.title is required")
    status = "".join(f'<div>{esc(x)}</div>' for x in shell.get("status", []))
    search = f'<input class="search" id="search" type="search" aria-label="搜索当前视图" placeholder="{esc(shell.get("search_placeholder", "搜索当前视图"))}">' if shell.get("search", True) else ""
    date = f'<div class="date">{esc(shell.get("date_range"))}</div>' if shell.get("date_range") else ""
    replacements = {
        "__CLI_VERSION__": esc(cli_version),
        "__TITLE__": esc(meta["title"]),
        "__SUBTITLE__": esc(meta.get("subtitle", "")),
        "__BRAND_MARK__": esc(shell.get("brand_mark", "TV")),
        "__BRAND_TITLE__": esc(shell.get("brand_title", meta["title"])),
        "__BRAND_SUBTITLE__": esc(shell.get("brand_subtitle", pack.get("title", ""))),
        "__NAV_LABEL__": esc(shell.get("nav_label", "报告视图")),
        "__NAV__": "".join(nav),
        "__STATUS__": status,
        "__TOOLS__": search + date,
        "__VIEWS__": "".join(rendered),
        "__FOOTER__": esc(meta.get("footer", "")),
        "__VIEW_IDS__": json.dumps(ids, ensure_ascii=False),
    }
    output = (ROOT / "template.html").read_text(encoding="utf-8")
    for marker, replacement in replacements.items():
        if marker not in output:
            raise ValueError(f"template marker missing: {marker}")
        output = output.replace(marker, replacement)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    return {
        "ok": True,
        "output": str(output_path),
        "cli_version": cli_version,
        "contract": CONTRACT,
        "template_pack": pack.get("id"),
        "template_pack_version": pack.get("version"),
        "views": len(views),
        "assets_embedded": len(renderer.assets),
        "bytes": output_path.stat().st_size,
    }
