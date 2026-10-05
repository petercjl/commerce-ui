"""Render product-tvc-script-report@2.0."""

from __future__ import annotations
import base64, html, json, mimetypes, pathlib, re

ROOT=pathlib.Path(__file__).resolve().parent
CONTRACT="product-tvc-script-report@2.0"

def esc(value): return html.escape("" if value is None else str(value),quote=True)
def slug(value): return re.sub(r"[^A-Za-z0-9_-]+","-",str(value)).strip("-") or "item"

def assets_for(raw,base):
    result={}
    for asset_id,item in (raw or {}).items():
        path=(base/item["path"]).resolve()
        if not path.is_file(): raise ValueError(f"asset file missing: {asset_id}")
        mime=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if not mime.startswith("image/"): raise ValueError(f"asset is not an image: {asset_id}")
        result[asset_id]={**item,"src":f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"}
    return result

class Renderer:
    def __init__(self,assets): self.assets=assets
    def media(self,asset_id,role="参考图",description=""):
        item=self.assets.get(asset_id)
        if not item: return '<div class="image-missing">参考图片未能载入</div>'
        caption=description or item.get("caption","")
        return f'<figure class="media"><div class="image-wrap"><img src="{item["src"]}" alt="{esc(item.get("alt","参考图"))}"><span>{esc(role)}</span></div><figcaption>{esc(caption)}</figcaption></figure>'
    def block(self,b):
        kind=b["type"]
        if kind=="plan_compare":
            cards=[]
            for x in b.get("items",[]):
                flag='<span class="recommended">上游推荐</span>' if x.get("recommended") else '<span class="alternative">备选方向</span>'
                cards.append(f'<article class="plan-card searchable"><div class="plan-card-top"><b>{esc(x.get("number"))}</b>{flag}</div><h2>{esc(x.get("title"))}</h2><p class="proposition">{esc(x.get("proposition"))}</p><div class="hook"><span>记忆钩子</span>{esc(x.get("hook"))}</div><div class="plan-stats"><span>{esc(x.get("duration"))}</span><span>{esc(x.get("storyboard_count"))} 个分镜</span><span>{esc(x.get("rank"))}</span></div></article>')
            return '<section class="plan-grid">'+''.join(cards)+'</section>'
        if kind=="plan_intro":
            badges=''.join(f'<span>{esc(x)}</span>' for x in b.get("badges",[]))
            return f'<section class="plan-intro searchable"><div class="eyebrow">{esc(b.get("eyebrow"))}</div><h2>{esc(b.get("title"))}</h2><p>{esc(b.get("text"))}</p><div class="badges">{badges}</div></section>'
        if kind=="key_values":
            return '<section class="kv">'+''.join(f'<div class="searchable"><span>{esc(x.get("label"))}</span><b>{esc(x.get("value"))}</b></div>' for x in b.get("items",[]))+'</section>'
        if kind=="storyboards":
            return '<section class="storyboard-list">'+''.join(self.storyboard(x) for x in b.get("items",[]))+'</section>'
        if kind=="audio_edit":
            cards=''.join(f'<article class="audio-card searchable"><span>{esc(x.get("label"))}</span><b>{esc(x.get("value"))}</b><p>{esc(x.get("note"))}</p></article>' for x in b.get("items",[]))
            return f'<section class="section-card"><h2>{esc(b.get("title","声音与剪辑"))}</h2><div class="audio-grid">{cards}</div></section>'
        if kind=="callout": return f'<div class="callout tone-{slug(b.get("tone","info"))} searchable"><b>{esc(b.get("title"))}</b><p>{esc(b.get("text"))}</p></div>'
        if kind=="checklist":
            rows=''.join(f'<li class="searchable status-{slug(x.get("status","info"))}"><b>{esc(x.get("label"))}</b><span>{esc(x.get("note"))}</span></li>' for x in b.get("items",[]))
            return f'<section class="section-card"><ul class="checklist">{rows}</ul></section>'
        raise ValueError(f"unsupported block type: {kind}")
    def storyboard(self,x):
        refs=''.join(self.media(r.get("asset_id"),r.get("role","现有参考图"),r.get("description","")) for r in x.get("reference_images",[]))
        if not refs: refs='<div class="empty-note">本分镜没有可直接使用的现有场景图，查看下方待生成资产。</div>'
        missing=[]
        for item in x.get("missing_assets",[]):
            inputs=''.join(self.media(asset_id,"生成资产输入参考","") for asset_id in item.get("input_asset_ids",[]))
            if not inputs: inputs='<div class="empty-note">没有可用的用户图片作为输入参考；生成时仍需遵循产品身份基准图。</div>'
            missing.append(f'<article class="asset-need searchable"><div class="need-head"><b>{esc(item.get("label"))}</b></div><p><strong>用途：</strong>{esc(item.get("purpose"))}</p><p><strong>生成说明：</strong>{esc(item.get("generation_notes"))}</p><p><strong>验收：</strong>{esc(item.get("acceptance"))}</p><div class="input-label">可用的输入参考图</div><div class="reference-grid input-grid">{inputs}</div></article>')
        missing_html=''.join(missing) if missing else '<div class="no-need">本分镜不缺少前置资产，可直接使用现有参考图进入视频生成。</div>'
        return f'''<article class="storyboard searchable">
          <header class="storyboard-head"><div><span>{esc(x.get("number"))}</span><h2>{esc(x.get("title"))}</h2></div><div class="time"><b>{esc(x.get("time"))}</b><span>生成单元 {esc(x.get("duration"))}</span></div></header>
          <div class="beat-label">叙事阶段：{esc(x.get("beat"))}</div>
          <div class="script-grid"><section><h3>画面脚本</h3><p>{esc(x.get("visual"))}</p></section><section><h3>运镜</h3><p>{esc(x.get("camera"))}</p></section><section><h3>声音与字幕</h3><p>{esc(x.get("audio"))}</p><small>画面文字：{esc(x.get("on_screen_text"))}</small></section><section><h3>连续性</h3><p>{esc(x.get("continuity"))}</p><small>表达边界：{esc(x.get("claim_status"))}</small></section></div>
          <section class="prompt-box"><div class="prompt-title">视频生成提示词</div><p>{esc(x.get("prompt"))}</p><div><b>参考锁定：</b>{esc(x.get("reference_lock"))}</div><div><b>禁止变化：</b>{esc(x.get("negative_limits"))}</div></section>
          <section class="reference-section"><h3>本分镜直接使用的参考图</h3><div class="reference-grid">{refs}</div></section>
          <section class="missing-section"><h3>本分镜待生成资产</h3>{missing_html}</section>
        </article>'''
    def blocks(self,items): return ''.join(self.block(x) for x in items)

def render_file(input_value,output_value,*,cli_version:str,pack:dict)->dict:
    input_path=pathlib.Path(input_value).expanduser().resolve(); output_path=pathlib.Path(output_value).expanduser().resolve()
    if output_path.exists(): raise ValueError(f"refusing to overwrite existing output: {output_path}")
    doc=json.loads(input_path.read_text(encoding="utf-8"))
    if doc.get("contract")!=CONTRACT: raise ValueError(f"contract must be {CONTRACT}")
    views=doc.get("views",[])
    if len(views)<3: raise ValueError("at least three views are required")
    renderer=Renderer(assets_for(doc.get("assets"),input_path.parent)); nav=[]; rendered=[]; ids=[]
    for index,view in enumerate(views):
        view_id=slug(view["id"]); ids.append(view_id); nav.append(f'<button type="button" data-view-target="{esc(view_id)}">{esc(view.get("label",view_id))}</button>'); hidden="" if index==0 else " hidden"
        heading=f'<div class="heading"><h1>{esc(view.get("title"))}</h1><p>{esc(view.get("subtitle"))}</p></div>'
        rendered.append(f'<section class="view" data-view="{esc(view_id)}"{hidden}>{heading}{renderer.blocks(view.get("blocks",[]))}</section>')
    meta=doc["meta"]; shell=doc.get("shell",{}); status=''.join(f'<div>{esc(x)}</div>' for x in shell.get("status",[])); search=f'<input class="search" id="search" type="search" placeholder="{esc(shell.get("search_placeholder","搜索当前视图"))}">' if shell.get("search") else ""
    replacements={"__CLI_VERSION__":esc(cli_version),"__TITLE__":esc(meta["title"]),"__SUBTITLE__":esc(meta.get("subtitle","")),"__BRAND_MARK__":esc(shell.get("brand_mark","镜")),"__BRAND_TITLE__":esc(shell.get("brand_title",meta["title"])),"__BRAND_SUBTITLE__":esc(shell.get("brand_subtitle",pack.get("title",""))),"__NAV_LABEL__":esc(shell.get("nav_label","报告视图")),"__NAV__":''.join(nav),"__STATUS__":status,"__TOOLS__":search,"__VIEWS__":''.join(rendered),"__FOOTER__":esc(meta.get("footer","")),"__VIEW_IDS__":json.dumps(ids,ensure_ascii=False)}
    output=(ROOT/"template.html").read_text(encoding="utf-8")
    for marker,replacement in replacements.items(): output=output.replace(marker,replacement)
    output_path.parent.mkdir(parents=True,exist_ok=True); output_path.write_text(output,encoding="utf-8")
    return {"ok":True,"output":str(output_path),"cli_version":cli_version,"contract":CONTRACT,"template_pack":pack.get("id"),"views":len(views),"assets_embedded":len(renderer.assets),"bytes":output_path.stat().st_size}
