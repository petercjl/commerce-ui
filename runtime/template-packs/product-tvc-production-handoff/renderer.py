"""Renderer for the product TVC production handoff report."""

from __future__ import annotations

import base64, html, json, pathlib, re
from typing import Any

ROOT=pathlib.Path(__file__).resolve().parent; CONTRACT="product-tvc-script-report@3.0"


def esc(value:Any)->str: return html.escape(str(value if value is not None else ""),quote=True)
def slug(value:Any)->str:
    result=re.sub(r"[^A-Za-z0-9_-]+","-",str(value or "")).strip("-")
    if not result: raise ValueError("identifier cannot be empty")
    return result
def mime(blob:bytes)->str:
    if blob.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if blob.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if blob.startswith((b"GIF87a",b"GIF89a")): return "image/gif"
    if blob.startswith(b"RIFF") and blob[8:12]==b"WEBP": return "image/webp"
    raise ValueError("unsupported image format")
def assets_for(raw:Any,base:pathlib.Path)->dict[str,dict[str,str]]:
    if raw is None:return {}
    items=[dict(value,id=key) for key,value in raw.items()] if isinstance(raw,dict) else raw; result={}
    for item in items:
        asset_id,value=str(item.get("id","")),str(item.get("path",""))
        if not asset_id or not value: raise ValueError("asset requires id and path")
        if re.match(r"https?://",value,re.I): raise ValueError("remote assets are forbidden")
        path=pathlib.Path(value).expanduser(); path=(base/path).resolve() if not path.is_absolute() else path.resolve(); blob=path.read_bytes()
        result[asset_id]={"src":f"data:{mime(blob)};base64,{base64.b64encode(blob).decode()}","alt":str(item.get("alt","产品参考图"))}
    return result


class Renderer:
    def __init__(self,assets): self.assets=assets
    def image(self,asset_id,role):
        asset=self.assets.get(str(asset_id))
        if not asset: raise ValueError(f"unknown asset_id: {asset_id}")
        return f'<figure class="ref-image searchable"><img src="{asset["src"]}" alt="{esc(asset["alt"])}"><figcaption><b>{esc(role)}</b><span>用户参考图</span></figcaption></figure>'
    def reference(self,ref):
        if ref["kind"]=="image": return self.image(ref["asset_id"],ref["role"])
        return f'<div class="generated-ref searchable"><span class="asset-code">{esc(ref["asset_id"])}</span><b>{esc(ref["label"])}</b><small>{esc(ref["role"])} · 来源：{esc(ref["source_storyboard"])}</small></div>'
    def refs(self,refs): return '<div class="reference-grid">'+''.join(self.reference(x) for x in refs)+'</div>' if refs else '<div class="empty-note">无需输入参考图，按生图内容从零生成。</div>'
    def asset(self,item):
        return f'''<article class="asset-item searchable"><div class="asset-title"><span class="asset-code">{esc(item['asset_id'])}</span><div><b>{esc(item['label'])}</b><small>{esc(item['video_use'])} · {esc(item['frame_moment'])} · {esc(item['aspect_ratio'])}</small></div></div><div class="field-label">输入参考图</div>{self.refs(item['references'])}<div class="field-label">生图内容</div><div class="intent">{esc(item['image_intent'])}</div></article>'''
    def storyboard(self,item):
        new_assets=''.join(self.asset(x) for x in item['new_assets']) if item['new_assets'] else '<div class="empty-note">本分镜不新增资产图，直接复用已有资产。</div>'
        reuse=''.join(f'<div class="reuse-row searchable"><span class="asset-code">{esc(x["asset_id"])}</span><b>{esc(x["label"])}</b><span>{esc(x["role"])} · 在{esc(x["source_storyboard"])}生成</span></div>' for x in item['reused_assets'])
        reuse_block=f'<div class="reuse-box"><div class="field-label">复用已有资产</div>{reuse}</div>' if reuse else ''
        audio=f'<div class="audio-note"><b>声音：</b>{esc(item["video"]["audio_intent"] or "不生成声音")}</div>' if item['video']['generate_audio'] else '<div class="audio-note"><b>声音：</b>本镜头不生成声音</div>'
        return f'''<article class="storyboard searchable"><header class="story-head"><div><span>{esc(item['number'])}</span><h2>{esc(item['title'])}</h2></div><b>{esc(item['time'])}</b></header><section class="step image-step"><div class="step-marker">1</div><div class="step-content"><h3>准备资产图</h3>{new_assets}{reuse_block}</div></section><section class="step video-step"><div class="step-marker">2</div><div class="step-content"><h3>生成短视频</h3><div class="field-label">输入参考图</div>{self.refs(item['video']['references'])}<div class="field-label">视频内容</div><div class="intent video-intent">{esc(item['video']['video_intent'])}</div><div class="video-meta"><span>{esc(item['video']['duration'])}</span><span>{esc(item['video']['aspect_ratio'])}</span></div>{audio}</div></section></article>'''
    def block(self,value):
        kind=value.get('type')
        if kind=='plan_compare':
            cards=''.join(f'<article class="plan-card searchable {"recommended" if x.get("recommended") else ""}"><div class="plan-top"><span>{esc(x["number"])}</span><b>{"优先" if x.get("recommended") else esc(x["rank"])}</b></div><h2>{esc(x["title"])}</h2><p>{esc(x["proposition"])}</p><small>{esc(x["hook"])}</small><div class="plan-stats"><span>{esc(x["duration"])}</span><span>{x["storyboard_count"]} 个分镜</span><span>{x.get("fixed_asset_count",0)} 张固定资产</span><span>{x["asset_count"]} 张全部资产</span></div></article>' for x in value['items'])
            return f'<section class="plan-compare">{cards}</section>'
        if kind=='key_values': return '<div class="kv">'+''.join(f'<div><span>{esc(x["label"])}</span><b>{esc(x["value"])}</b></div>' for x in value['items'])+'</div>'
        if kind=='callout': return f'<div class="callout"><b>{esc(value.get("title","提示"))}</b><p>{esc(value["text"])}</p></div>'
        if kind=='plan_intro': return f'<section class="plan-intro"><span>{esc(value["eyebrow"])}</span><h2>{esc(value["title"])}</h2><p>{esc(value["text"])}</p><div>{"".join(f"<b>{esc(x)}</b>" for x in value["badges"])}</div></section>'
        if kind=='fixed_asset_handoff': return f'<section class="fixed-assets"><header><span>生成顺序 01</span><h2>{esc(value["title"])}</h2><p>{esc(value["text"])}</p></header><div class="fixed-asset-grid">{"".join(self.asset(x) for x in value["items"])}</div></section>'
        if kind=='storyboard_handoffs': return '<section class="storyboard-list">'+''.join(self.storyboard(x) for x in value['items'])+'</section>'
        if kind=='checklist': return '<section class="checklist">'+''.join(f'<div class="check {esc(x["status"])}"><b>{esc(x["label"])}</b><span>{esc(x["note"])}</span></div>' for x in value['items'])+'</section>'
        raise ValueError(f"unsupported block type: {kind}")
    def blocks(self,items): return ''.join(self.block(x) for x in items)


def render_file(input_value,output_value,*,cli_version:str,pack:dict)->dict:
    input_path=pathlib.Path(input_value).expanduser().resolve(); output_path=pathlib.Path(output_value).expanduser().resolve()
    if output_path.exists(): raise ValueError(f"refusing to overwrite existing output: {output_path}")
    document=json.loads(input_path.read_text(encoding='utf-8'))
    if document.get('contract')!=CONTRACT: raise ValueError(f"contract must be {CONTRACT}")
    views=document.get('views'); renderer=Renderer(assets_for(document.get('assets'),input_path.parent)); nav=[]; rendered=[]; ids=[]
    for index,view in enumerate(views):
        view_id=slug(view['id']); ids.append(view_id); nav.append(f'<button type="button" data-view-target="{view_id}">{esc(view["label"])}</button>'); hidden='' if index==0 else ' hidden'; rendered.append(f'<section class="view" data-view="{view_id}"{hidden}><div class="heading"><h1>{esc(view["title"])}</h1><p>{esc(view.get("subtitle",""))}</p></div>{renderer.blocks(view["blocks"])}</section>')
    meta,shell=document['meta'],document.get('shell',{}); replacements={'__CLI_VERSION__':esc(cli_version),'__TITLE__':esc(meta['title']),'__SUBTITLE__':esc(meta.get('subtitle','')),'__BRAND_MARK__':esc(shell.get('brand_mark','镜')),'__BRAND_TITLE__':esc(shell.get('brand_title',meta['title'])),'__BRAND_SUBTITLE__':esc(shell.get('brand_subtitle','')),'__NAV_LABEL__':esc(shell.get('nav_label','报告视图')),'__NAV__':''.join(nav),'__STATUS__':''.join(f'<div>{esc(x)}</div>' for x in shell.get('status',[])),'__TOOLS__':f'<input class="search" id="search" type="search" placeholder="{esc(shell.get("search_placeholder","搜索当前视图"))}">' if shell.get('search') else '','__VIEWS__':''.join(rendered),'__FOOTER__':esc(meta.get('footer','')),'__VIEW_IDS__':json.dumps(ids,ensure_ascii=False)}
    output=(ROOT/'template.html').read_text(encoding='utf-8')
    for marker,replacement in replacements.items(): output=output.replace(marker,replacement)
    output_path.parent.mkdir(parents=True,exist_ok=True); output_path.write_text(output,encoding='utf-8')
    return {'ok':True,'output':str(output_path),'cli_version':cli_version,'contract':CONTRACT,'template_pack':pack.get('id'),'views':len(views),'assets_embedded':len(renderer.assets),'bytes':output_path.stat().st_size}
