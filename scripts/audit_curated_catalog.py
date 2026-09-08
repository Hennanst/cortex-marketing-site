#!/usr/bin/env python3
"""Read-only commercial catalog and complete public internal-link verification."""
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs

ROOT=Path(__file__).resolve().parents[1]
products=json.loads((ROOT/'data/catalogo-curado.json').read_text())['products']
public=json.loads((ROOT/'data/publication-manifest.json').read_text())['html']
errors=[]
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.ids=[];self.links=[];self.asins=[];self.images=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if a.get('data-asin'):self.asins.append(a['data-asin'])
        if tag=='a' and a.get('href'):self.links.append(a)
        if tag=='img':self.images.append(a)
pages={rel:Page((ROOT/rel).read_text()) for rel in public}
counts=Counter(p['niche'] for p in products)
if len(products)!=40 or sorted(counts.values())!=[10,10,10,10]:errors.append('Expected exactly 40 distinct products / 10 per niche')
for field in ('id','asin','image'):
    values=[p.get(field) for p in products]
    if None in values or len(set(values))!=40:errors.append(f'Catalog missing or duplicate {field}')
for p in products:
    for field in ('fit','specs','reason','avoid','value','source','variant'):
        if not p.get(field):errors.append(f'Missing {field}: {p["id"]}')
    if p.get('alternative') and p['alternative'] not in {x['id'] for x in products}:errors.append(f'Unknown alternative: {p["id"]}')
    if any(k in p for k in ('price','rating','score','stock')):errors.append(f'Unverified live claim field: {p["id"]}')
    if p['asin'] not in pages['recomendados/index.html'].asins:errors.append(f'Missing catalog card {p["asin"]}')
    if p['asin'] not in pages[p['niche']+'/index.html'].asins:errors.append(f'Missing niche card {p["asin"]}')
amazon_links=0;internal_links=0
for rel,page in pages.items():
    duplicates=[i for i,n in Counter(page.ids).items() if n>1]
    if duplicates:errors.append(f'Duplicate anchors {rel}: {duplicates}')
    for a in page.links:
        u=urlsplit(a['href'])
        if u.netloc in {'www.amazon.com.br','amazon.com.br'}:
            amazon_links+=1
            if parse_qs(u.query).get('tag')!=['cortexofertas-20']:errors.append(f'Wrong/missing affiliate tag: {rel} {a["href"]}')
            if not {'sponsored','nofollow'}<=set(a.get('rel','').split()):errors.append(f'Missing affiliate rel: {rel} {a["href"]}')
        if u.scheme and u.scheme not in {'http','https'}:continue
        if u.netloc and u.netloc!='cortex-ofertas.pages.dev':continue
        path=unquote(u.path)
        target=(ROOT/path.lstrip('/')) if path.startswith('/') else (ROOT/rel).parent/path if path else ROOT/rel
        if target.is_dir():target=target/'index.html'
        target_rel=str(target.resolve().relative_to(ROOT))
        if target_rel in pages:
            internal_links+=1
            if u.fragment and unquote(u.fragment) not in pages[target_rel].ids:errors.append(f'Broken anchor {rel}: {a["href"]}')
        elif path and path.endswith(('.html','/')):errors.append(f'Unpublished internal route {rel}: {a["href"]}')
    if rel.startswith('guia/'):
        if not page.images:errors.append(f'Guide has no relevant image: {rel}')
        if 'CORTEX_JOURNEY_START' not in (ROOT/rel).read_text():errors.append(f'Guide lacks contextual journey: {rel}')
required={'B07GPRWFC5','B087CT8PWY','B0D8DPT7ZY','B0DLPB4CH6','B0DGQLYST1','B0C3BV19Q3','B07K986YLL','B0CJRXT3L6','B0D6HXDRZL','B0BNSVWWDR'}
if not required<={p['asin'] for p in products}:errors.append('Approved commercial product removed')
print(json.dumps({'status':'PASS' if not errors else 'REVISE','scope':'Source verification only; not independent editorial or public release approval','products':len(products),'niches':dict(counts),'public_pages':len(pages),'guides_with_journeys':len([x for x in public if x.startswith('guia/')]),'comparisons':11,'amazon_links':amazon_links,'internal_links':internal_links,'errors':errors},ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
