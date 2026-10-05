"""Deterministic validator for monthly profit review reports."""
from __future__ import annotations

import pathlib
import re

CONTRACT = "monthly-profit-review@1.0"

def validate_file(path_value, *, pack: dict) -> dict:
    path = pathlib.Path(path_value).expanduser().resolve()
    if not path.is_file():
        return {"ok": False, "path": str(path), "errors": ["file not found"]}
    text, errors = path.read_text(encoding="utf-8"), []
    required = {
        "viewport": r'<meta\s+name="viewport"',
        "contract": rf'commerce-ui-contract"\s+content="{re.escape(CONTRACT)}"',
        "owner comparison": r'data-view="owner-comparison"',
        "unowned view": r'data-view="unowned"',
        "all products view": r'data-view="products"',
        "sticky context title": r'\.context-title\{[^}}]*position:sticky',
        "product tables": r'class="panel product-table"',
        "floating product table header": r'className=["\']floating-table-head["\']',
        "floating header scroll listener": r"addEventListener\('scroll'.*controller\.update",
        "dynamic sticky offset": r"setProperty\('--table-sticky-top'",
        "product search": r'placeholder="搜索商品名称或商品ID"',
        "post-refund paid ratio after owner": r"\['owner','负责人'\],\['post_refund_paid_ratio','退款后付费占比'\]",
        "product original and cancelled payment columns": r"\['all_order_original_payment','全部订单原支付额'\],\['cancelled_order_original_payment','取消订单金额'\]",
        "global sort before page": r'rows=\[\.\.\.rows\]\.sort[\s\S]*rows\.slice\(\(page-1\)\*pageSize,page\*pageSize\)',
        "page size": r'pageSize=50',
        "lazy remote images": r'loading="lazy"',
        "mobile": r'@media\(max-width:',
        "print": r'@media print',
    }
    for label, pattern in required.items():
        if not re.search(pattern, text, re.I):
            errors.append(f"missing {label}")
    if re.search(r'<(?:script|link)[^>]+(?:src|href)=["\']https?://', text, re.I):
        errors.append("external script or stylesheet dependency")
    if re.search(r'/Users/[^/]+/|[A-Za-z]:\\Users\\[^\\]+\\', text):
        errors.append("private home path")
    if re.search(r'__[A-Z][A-Z0-9_]+__', text):
        errors.append("unresolved template marker")
    if '"external_images":"allow_https"' not in text:
        errors.append("remote product images were not explicitly approved")
    if '"payment_flow":{' in text and '旺店通全部订单还原支付原额' not in text:
        errors.append("payment bridge is missing from overview")
    sizes = [float(x) for x in re.findall(r'font-size\s*:\s*(\d+(?:\.\d+)?)px', text, re.I)]
    if sizes and min(sizes) < 12:
        errors.append(f"font size below 12px: {min(sizes):g}px")
    views = re.findall(r'<section\s+class="view"\s+data-view="([^"]+)"', text, re.I)
    visible = len(re.findall(r'<section\s+class="view"\s+data-view="[^"]+"(?![^>]*\bhidden\b)[^>]*>', text, re.I))
    if len(views) < 6:
        errors.append("fewer than six report views")
    if len(views) != len(set(views)):
        errors.append("duplicate view id")
    if visible != 1:
        errors.append(f"expected one initially visible view, found {visible}")
    image_urls = re.findall(r'"image_url":"(https://[^"<>\s]+)"', text)
    return {"ok": not errors, "path": str(path), "contract": CONTRACT, "template_pack": pack.get("id"), "view_count": len(views), "remote_product_image_count": len(image_urls), "page_size": 50, "errors": errors}
