"""Renderer for the monthly profit review contract."""
from __future__ import annotations

import html
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent
CONTRACT = "monthly-profit-review@1.0"

def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)

def money(value: Any) -> str:
    return f"¥{float(value or 0):,.2f}"

def percent(value: Any) -> str:
    return "—" if value is None else f"{float(value) * 100:.2f}%"

def metric(label: str, value: str, note: str = "", css: str = "") -> str:
    return f'<article class="metric"><span>{esc(label)}</span><b class="{css}">{esc(value)}</b><small>{esc(note)}</small></article>'

def summary_metrics(row: dict) -> str:
    profit_css = "positive" if float(row.get("actual_profit", 0)) >= 0 else "negative"
    return '<section class="metrics">' + "".join([
        metric("已发货销售原额", money(row.get("gross_revenue")), "纳入利润的订单"),
        metric("净销售额", money(row.get("net_sales")), f'退款 {money(row.get("refund_amount"))}'),
        metric("实际利润", money(row.get("actual_profit")), f'利润率 {percent(row.get("profit_margin"))}', profit_css),
        metric("推广费", money(row.get("ad_spend")), f'{int(row.get("product_count", 0))} 个商品'),
    ]) + '</section>'

def payment_bridge(flow: dict, scope_label: str = "旺店通全部订单") -> str:
    rows = [
        (f"{scope_label}还原支付原额", flow["all_order_original_payment"]),
        ("减：取消订单还原支付原额", flow["cancelled_order_original_payment"]),
        ("已发货订单销售原额", flow["shipped_order_original_payment"]),
        ("减：已发货订单已结算退款", flow["shipped_order_settled_refund"]),
        ("利润使用的净销售额", flow["net_sales"]),
    ]
    body = "".join(f'<tr><td>{esc(label)}</td><td class="num">{esc(money(value))}</td></tr>' for label, value in rows)
    audit = (f'取消订单结算退款 {money(flow["cancelled_order_settled_refund"])}；'
             f'支付退款残差 {money(flow["cancelled_order_refund_residual"])}，单独审计。')
    return f'<section class="panel payment-bridge"><div class="panel-head"><h2>支付金额如何进入利润</h2><span>旺店通支付月口径</span></div><div class="table-wrap"><table><thead><tr><th>项目</th><th>金额</th></tr></thead><tbody>{body}</tbody></table></div><p class="note">{esc(audit)}</p></section>'

def context(title: str, subtitle: str, kicker: str) -> str:
    return f'<header class="context-title"><div class="kicker">{esc(kicker)}</div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></header>'

def statement(row: dict) -> str:
    columns = ["已发货销售原额", "退款", "净销售额", "商品成本", "运费", "推广费", "平台费", "税费", "实际利润", "利润率"]
    values = [money(row.get("gross_revenue")), money(row.get("refund_amount")), money(row.get("net_sales")), money(row.get("goods_cost")), money(row.get("freight_cost")), money(row.get("ad_spend")), money(row.get("platform_fee")), money(row.get("tax_cost")), money(row.get("actual_profit")), percent(row.get("profit_margin"))]
    return f'<section class="panel"><div class="panel-head"><h2>利润表</h2><span>权威汇总</span></div><div class="table-wrap"><table><thead><tr>{"".join(f"<th>{x}</th>" for x in columns)}</tr></thead><tbody><tr>{"".join(f"<td class=\"num\">{esc(x)}</td>" for x in values)}</tr></tbody></table></div></section>'

def product_table(source: str, count: int, title: str = "全部商品明细") -> str:
    return f'''<section class="panel product-table" data-source="{esc(source)}"><div class="panel-head"><h2>{esc(title)}</h2><span>{count} 个商品</span></div><div class="table-tools"><input class="table-search" type="search" placeholder="搜索商品名称或商品ID"><span>点击表头可按完整结果排序</span></div><div class="table-wrap"><table><thead><tr></tr></thead><tbody></tbody></table></div><div class="pager"><span class="pager-info"></span><span><button class="prev" type="button">上一页</button> <button class="next" type="button">下一页</button></span></div></section>'''

def view(view_id: str, body: str, visible: bool = False) -> str:
    hidden = "" if visible else " hidden"
    return f'<section class="view" data-view="{esc(view_id)}" id="view-{esc(view_id)}"{hidden}>{body}</section>'

def owner_comparison(owners: list[dict]) -> str:
    columns = ["负责人", "全部订单原支付", "取消订单金额", "已发货销售原额", "退款", "净销售额", "商品成本", "运费", "推广费", "实际利润", "利润率", "商品数"]
    rows = []
    for owner in sorted(owners, key=lambda x: float(x["summary"].get("actual_profit", 0)), reverse=True):
        row = owner["summary"]
        flow = row["payment_flow"]
        values = [owner["name"], money(flow["all_order_original_payment"]), money(flow["cancelled_order_original_payment"]), money(row.get("gross_revenue")), money(row.get("refund_amount")), money(row.get("net_sales")), money(row.get("goods_cost")), money(row.get("freight_cost")), money(row.get("ad_spend")), money(row.get("actual_profit")), percent(row.get("profit_margin")), str(row.get("product_count", 0))]
        rows.append("<tr>" + "".join(f'<td class="{"num" if i else ""}">{esc(value)}</td>' for i, value in enumerate(values)) + "</tr>")
    return f'<section class="panel"><div class="panel-head"><h2>负责人对比</h2><span>{len(owners)} 位负责人</span></div><div class="table-wrap"><table><thead><tr>{"".join(f"<th>{x}</th>" for x in columns)}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'

def render_file(input_value, output_value, *, cli_version: str, pack: dict) -> dict:
    input_path = pathlib.Path(input_value).expanduser().resolve()
    output_path = pathlib.Path(output_value).expanduser().resolve()
    if output_path.exists():
        raise ValueError(f"refusing to overwrite existing output: {output_path}")
    document = json.loads(input_path.read_text(encoding="utf-8"))
    if document.get("contract") != CONTRACT:
        raise ValueError(f"contract must be {CONTRACT}")
    meta, shop, owners, unowned, products = document["meta"], document["shop"], document["owners"], document["unowned"], document["products"]
    nav = [
        '<button type="button" data-view-target="overview">全店总览</button>',
        '<button type="button" data-view-target="owner-comparison">负责人对比</button>',
        '<div class="nav-group-title">负责人详情</div>',
    ]
    for owner in owners:
        nav.append(f'<button type="button" class="nav-child" data-view-target="{esc(owner["id"])}"><span>{esc(owner["name"])}</span><span>{esc(money(owner["summary"].get("actual_profit")))}</span></button>')
    nav += [
        '<div class="nav-group-title">其他数据</div>',
        '<button type="button" data-view-target="unowned">非负责人数据</button>',
        '<button type="button" data-view-target="products">全店商品</button>',
        '<button type="button" data-view-target="quality">质量与口径</button>',
    ]
    views = []
    overview = context("全店利润总览", "先看全部订单支付额如何桥接到利润，再进入负责人和商品归因。", "全店") + (payment_bridge(document["payment_flow"]) if document.get("payment_flow") else "") + summary_metrics(shop) + statement(shop)
    views.append(view("overview", overview, True))
    compare = context("负责人利润对比", "这里只比较实际负责人；无归属、未分配和已下架数据在独立页面查看。", "负责人") + owner_comparison(owners)
    views.append(view("owner-comparison", compare))
    for owner in owners:
        body = context(f'负责人：{owner["name"]}', "当前页面展示该负责人的支付桥接、利润汇总和全部商品。标题在滚动时保持可见。", "负责人详情") + payment_bridge(owner["summary"]["payment_flow"], f'{owner["name"]}全部订单') + summary_metrics(owner["summary"]) + statement(owner["summary"]) + product_table(owner["id"], len(owner["products"]), f'{owner["name"]}的全部商品')
        views.append(view(owner["id"], body))
    group_rows = "".join(f'<tr><td>{esc(row["name"])}</td><td class="num">{esc(money(row["payment_flow"]["all_order_original_payment"]))}</td><td class="num">{esc(money(row["payment_flow"]["cancelled_order_original_payment"]))}</td><td class="num">{esc(money(row.get("gross_revenue")))}</td><td class="num">{esc(money(row.get("refund_amount")))}</td><td class="num">{esc(money(row.get("actual_profit")))}</td><td class="num">{esc(percent(row.get("profit_margin")))}</td><td class="num">{int(row.get("product_count",0))}</td></tr>' for row in unowned["groups"])
    unowned_table = f'<section class="panel"><div class="panel-head"><h2>非负责人分组</h2><span>{len(unowned["groups"])} 个分组</span></div><div class="table-wrap"><table><thead><tr><th>分组</th><th>全部订单原支付</th><th>取消订单金额</th><th>已发货销售原额</th><th>退款</th><th>实际利润</th><th>利润率</th><th>商品数</th></tr></thead><tbody>{group_rows}</tbody></table></div></section>'
    views.append(view("unowned", context("非负责人数据", "无法归属、未分配负责人、已下架未分配及不归属负责人数据集中展示。", "独立页面") + unowned_table + product_table("unowned", len(unowned["products"]))))
    views.append(view("products", context("全店商品利润分析", "覆盖全店全部商品，包含负责人列；排序作用于完整结果后再分页。", "全店商品") + product_table("all", len(products))))
    quality = document["quality"]
    quality_body = context("数据质量与计算口径", "估算、异常归属与利润方法集中披露。", "质量与口径") + f'<section class="panel"><div class="panel-head"><h2>数据质量提示</h2><span>{len(quality["items"])} 项</span></div><ul class="notes">{"".join(f"<li>{esc(x)}</li>" for x in quality["items"])}</ul></section><section class="panel"><div class="panel-head"><h2>计算方法</h2></div><ul class="notes">{"".join(f"<li>{esc(x)}</li>" for x in quality["method"])}</ul></section>'
    views.append(view("quality", quality_body))
    safe_data = json.dumps(document, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    replacements = {"__CLI_VERSION__": esc(cli_version), "__TITLE__": esc(meta["title"]), "__SHOP_NAME__": esc(meta["shop_name"]), "__DATE_RANGE__": esc(meta["date_range"]), "__NAV__": "".join(nav), "__VIEWS__": "".join(views), "__FOOTER__": esc(meta.get("footer", "")), "__DATA__": safe_data}
    output = (ROOT / "template.html").read_text(encoding="utf-8")
    for marker, replacement in replacements.items():
        output = output.replace(marker, replacement)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    return {"ok": True, "output": str(output_path), "cli_version": cli_version, "contract": CONTRACT, "template_pack": pack.get("id"), "views": len(views), "remote_product_images": sum(1 for row in products if row.get("image_url")), "bytes": output_path.stat().st_size}
