"""Starter validator for a commerce-ui template pack."""

from __future__ import annotations

import pathlib
import re


CONTRACT = "product-tvc-script-report@1.0"


def validate_file(path_value, *, pack: dict) -> dict:
    path = pathlib.Path(path_value).expanduser().resolve()
    if not path.is_file(): return {"ok": False, "path": str(path), "errors": ["file not found"]}
    text, errors = path.read_text(encoding="utf-8"), []
    required = {"viewport": r'<meta\s+name="viewport"', "contract": rf'commerce-ui-contract"\s+content="{re.escape(CONTRACT)}"', "navigation": r'data-view-target=', "views": r'data-view=', "mobile": r'@media\(max-width:', "print": r'@media print', "timeline": r'class="timeline"', "shots": r'class="shot-list"'}
    for label, pattern in required.items():
        if not re.search(pattern, text, re.I): errors.append(f"missing {label}")
    if re.search(r'(?:src|href)=["\']https?://', text, re.I): errors.append("external rendering dependency")
    if re.search(r'/Users/[^/]+/|[A-Za-z]:\\Users\\[^\\]+\\', text): errors.append("private home path")
    if re.search(r'__[A-Z][A-Z0-9_]+__', text): errors.append("unresolved template marker")
    sizes = [float(x) for x in re.findall(r'font-size\s*:\s*(\d+(?:\.\d+)?)px', text, re.I)]
    if sizes and min(sizes) < 12: errors.append(f"font size below 12px: {min(sizes):g}px")
    views = re.findall(r'<section\s+class="view"\s+data-view="([^"]+)"', text, re.I)
    visible = len(re.findall(r'<section\s+class="view"\s+data-view="[^"]+"(?![^>]*\bhidden\b)[^>]*>', text, re.I))
    if len(views) < 2: errors.append("fewer than two views")
    if visible != 1: errors.append(f"expected one initially visible view, found {visible}")
    if "window.commerceUI" not in text: errors.append("missing public interaction state")
    return {"ok": not errors, "path": str(path), "contract": CONTRACT, "template_pack": pack.get("id"), "template_pack_version": pack.get("version"), "view_count": len(views), "errors": errors}
