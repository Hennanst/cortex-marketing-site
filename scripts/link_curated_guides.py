#!/usr/bin/env python3
"""Explicitly author buyer journeys into the 14 public guides; no build hook."""
import json
import re
from pathlib import Path
from html import escape

ROOT=Path(__file__).resolve().parents[1]
products={p['id']:p for p in json.loads((ROOT/'data/catalogo-curado.json').read_text())['products']}
photos=json.loads((ROOT/'data/editorial-visuals.json').read_text())['photos']
routes={
 'como-montar-setup-gamer':('setup-games','mouses',['g203','g305']),
 'havit-h2002d-quando-faz-sentido':('setup-games','headsets',['havit-h2002d','cloud-iii']),
 'headset-gamer-com-ou-sem-fio':('setup-games','headsets',['havit-h2002d','g335']),
 'headset-gamer-para-fps':('setup-games','headsets',['havit-h2002d','cloud-iii']),
 'melhor-headset-gamer-custo-beneficio':('setup-games','headsets',['g335','cloud-iii']),
 'melhor-notebook-gamer-custo-beneficio':('setup-games','monitores',[]),
 'melhor-webcam-para-stream':('creator-streaming','webcams',['c920s','brio-100']),
 'notebook-gamer-ou-pc-gamer':('trabalho-estudo','monitores',[]),
 'notebook-gamer-para-estudo-e-jogos':('trabalho-estudo','monitores',[]),
 'setup-gamer-custo-beneficio':('setup-games','monitores',['lg-24gs60f','aoc-24g4']),
 'setup-gamer-home-office-e-jogos':('trabalho-estudo','hubs',['h390','mx-master-3s']),
 'setup-streaming-iniciante':('creator-streaming','microfones',['solocast','fifine-am8']),
 'smart-plug-max-quando-faz-sentido':('casa-inteligente','assistentes',['smart-plug-max','positivo-ir']),
 'webcam-1080p-ou-4k-para-streaming':('creator-streaming','webcams',['c920s','brio-100']),
}
CSS='''<style data-cortex-journey="true">.cortex-next{margin:36px 0;padding:24px;border:1px solid #354451;border-radius:16px;background:#101820}.cortex-next h2{font-size:1.65rem;line-height:1.2}.cortex-next p{font-size:1rem}.cortex-next-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.cortex-next-item{overflow:hidden;border:1px solid #354451;border-radius:12px;background:#111b24}.cortex-next-image{height:195px;display:block;background:white;padding:16px}.cortex-next-image img{height:100%;width:100%;object-fit:contain;display:block}.cortex-next-copy{padding:18px}.cortex-next-copy h3{font-size:1.2rem}.cortex-next-copy a{font-size:1rem;font-weight:700;color:#62f6a5}.cortex-next-context{width:100%;max-height:220px;object-fit:cover;border-radius:10px}.cortex-next-links{display:flex;gap:18px;flex-wrap:wrap;margin-top:20px}.cortex-next-links a{font-size:1rem;color:#62f6a5}.cortex-next-label{font-size:.875rem;color:#b4bec8;display:block;margin:8px 0 14px}@media(max-width:640px){.cortex-next-grid{grid-template-columns:1fr}.cortex-next{padding:18px}}</style>'''
for slug,(niche,pair,ids) in routes.items():
    path=ROOT/f'guia/{slug}.html'
    text=path.read_text()
    text=re.sub(r'<style data-cortex-journey="true">.*?</style>','',text,flags=re.S)
    text=re.sub(r'<!-- CORTEX_JOURNEY_START -->.*?<!-- CORTEX_JOURNEY_END -->','',text,flags=re.S)
    body='<section class="cortex-next" aria-label="Continue sua decisão de compra"><h2>Leve estes critérios para a escolha</h2>'
    if ids:
        intro='Compare duas opções da seleção e abra a análise para conferir a versão, as limitações e quando o preço faz sentido.'
        if slug=='headset-gamer-com-ou-sem-fio': intro='Se a conexão com fio atende seu uso, estas são duas opções da seleção. Confira também os critérios de mobilidade e bateria do guia antes de decidir.'
        if slug=='webcam-1080p-ou-4k-para-streaming': intro='Se Full HD atende o formato final do seu vídeo, compare estas duas opções. Elas não oferecem 4K: a decisão entre resoluções deve vir antes da escolha do modelo.'
        if slug=='smart-plug-max-quando-faz-sentido': intro='Compare a função: o Smart Plug controla energia; o controle universal envia comandos infravermelhos a aparelhos compatíveis.'
        body+='<p>'+intro+'</p><div class="cortex-next-grid">'
        for ident in ids:
            p=products[ident]
            body+=f'<article class="cortex-next-item" data-asin="{p["asin"]}"><a class="cortex-next-image" href="/recomendados/#{ident}"><img src="{escape(p["image"],quote=True)}" alt="{escape(p["name"],quote=True)}" width="600" height="450" loading="lazy"></a><div class="cortex-next-copy"><h3>{escape(p["name"])}</h3><p>{escape(p["role"])}</p><a href="/recomendados/#{ident}">Ler análise e consultar a oferta</a></div></article>'
        body+='</div>'
    else:
        body+='<p>Este guia compara critérios para notebooks gamer. A seleção atual de notebooks da Córtex é voltada à produtividade geral; não recomendamos o IdeaPad 1 como equivalente a uma máquina gamer.</p>'
        body+=f'<img class="cortex-next-context" data-editorial-photo="gaming" src="{escape(photos["gaming"]["url"],quote=True)}" alt="Fotografia editorial de uma estação de jogos; não representa um notebook recomendado" loading="lazy"><small class="cortex-next-label">Fotografia de contexto para planejamento de uma estação de jogos.</small>'
    body+=f'<div class="cortex-next-links"><a href="/{niche}/">Explore as escolhas deste nicho</a><a href="/comparativos/#{pair}">Compare alternativas lado a lado</a><a href="/metodologia.html">Como avaliamos</a></div></section>'
    text=text.replace('</head>',CSS+'</head>',1)
    text=text.replace('</main>','<!-- CORTEX_JOURNEY_START -->'+body.replace('><','>\n<')+'<!-- CORTEX_JOURNEY_END --></main>',1)
    text=text.replace('<li>sem preço estático Amazon</li>','<li>preço final, vendedor e frete</li>')
    path.write_text(text)
print(f'Authored contextual journeys and relevant images in {len(routes)} guides.')
