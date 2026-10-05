"""Deterministic validator for Product TVC Analysis Report HTML."""

from __future__ import annotations

import pathlib
import re


CONTRACT = "product-tvc-analysis-report@2.0"


def validate_file(path_value, *, pack: dict) -> dict:
    path = pathlib.Path(path_value).expanduser().resolve()
    if not path.is_file():
        return {"ok": False, "path": str(path), "errors": ["file not found"]}
    text, errors = path.read_text(encoding="utf-8"), []
    required = {
        "viewport": r'<meta\s+name="viewport"',
        "contract": rf'commerce-ui-contract"\s+content="{re.escape(CONTRACT)}"',
        "template pack": r'commerce-ui-template-pack"\s+content="product-tvc-creative-report@2\.0\.0"',
        "navigation group": r'data-nav-group=',
        "navigation": r'data-view-target=',
        "views": r'data-view=',
        "mobile": r'@media\s*\(max-width:',
        "print": r'@media\s+print',
        "history": r'popstate',
        "hero component": r'class="hero\s',
    }
    for label, pattern in required.items():
        if not re.search(pattern, text, re.I):
            errors.append(f"missing {label}")
    if re.search(r'(?:src|href)=["\']https?://', text, re.I):
        errors.append("external rendering dependency")
    image_sources = re.findall(r'<img[^>]+src=["\']([^"\']+)', text, re.I)
    non_embedded = [source for source in image_sources if not source.startswith("data:image/")]
    if non_embedded:
        errors.append(f"found {len(non_embedded)} non-embedded image asset(s)")
    if re.search(r'/Users/[^/]+/|[A-Za-z]:\\Users\\[^\\]+\\', text):
        errors.append("private home path")
    if re.search(r'__[A-Z][A-Z0-9_]+__', text):
        errors.append("unresolved template marker")
    sizes = [float(x) for x in re.findall(r'font-size\s*:\s*(\d+(?:\.\d+)?)px', text, re.I)]
    if sizes and min(sizes) < 12:
        errors.append(f"font size below 12px: {min(sizes):g}px")
    views = re.findall(r'<section\s+class="view"\s+data-view="([^"]+)"', text, re.I)
    if len(views) != len(set(views)):
        errors.append("duplicate view ids")
    visible = len(re.findall(r'<section\s+class="view"\s+data-view="[^"]+"(?![^>]*\bhidden\b)[^>]*>', text, re.I))
    if len(views) < 2:
        errors.append("fewer than two views")
    if visible != 1:
        errors.append(f"expected one initially visible view, found {visible}")
    nav_targets = re.findall(r'data-view-target="([^"]+)"', text, re.I)
    if nav_targets != views:
        errors.append("navigation and view order do not match")
    return {
        "ok": not errors,
        "path": str(path),
        "contract": CONTRACT,
        "template_pack": pack.get("id"),
        "template_pack_version": pack.get("version"),
        "view_count": len(views),
        "image_count": len(image_sources),
        "errors": errors,
    }
