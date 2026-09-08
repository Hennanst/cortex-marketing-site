#!/usr/bin/env python3
"""Explicit source authoring; never invoked by the build or deployment pipeline.

Writes reviewed static HTML from the curated data. Generated source is committed
and then packaged byte-for-byte by the existing Cloudflare build.
"""
import json
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/catalogo-curado.json').read_text())
PRODUCTS = [p for p in DATA['products'] if p['status'] == 'published']
BY_ID = {p['id']: p for p in PRODUCTS}
NICHES = {
    'setup-games': ('Setup & Games', 'Um setup melhor começa pelo que atrapalha seu jogo.', 'Compare periféricos, áudio e tela pelo uso. A recomendação explica o benefício que justifica cada compra e a limitação que você aceita.', 'gaming'),
    'trabalho-estudo': ('Trabalho & Estudo', 'Escolhas para trabalhar e estudar com menos interrupções.', 'Notebook, conexão e periféricos precisam atender seus programas e sua rotina. Compare o conjunto, incluindo acessórios e adaptações necessários.', 'work'),
    'creator-streaming': ('Creator & Streaming', 'Invista no que seu público vai perceber.', 'Áudio inteligível, imagem adequada e um fluxo simples de gravação vêm antes de recursos que você não vai usar. Compare cada upgrade pelo seu papel.', 'creator'),
    'casa-inteligente': ('Casa Inteligente', 'Automação que resolve uma tarefa da sua casa.', 'Escolha por compatibilidade, instalação e função: controlar um aparelho, melhorar a rede, acompanhar um ambiente ou ouvir seus conteúdos.', 'home_automation'),
}
GUIDES = {
 'setup-games': [('setup-gamer-custo-beneficio','Setup gamer: onde investir primeiro','Organize o orçamento por gargalo.'),('melhor-headset-gamer-custo-beneficio','Como escolher um headset','Conexão, uso e limites de cada opção.'),('headset-gamer-para-fps','Headset para FPS','O que especificações não dizem sobre o som.'),('headset-gamer-com-ou-sem-fio','Com fio ou sem fio?','Entenda o custo da mobilidade.'),('como-montar-setup-gamer','Como montar seu setup','Planeje as peças como um conjunto.')],
 'trabalho-estudo': [('setup-gamer-home-office-e-jogos','Uma mesa para trabalho e jogos','Equilibre os dois usos.'),('notebook-gamer-para-estudo-e-jogos','Notebook para estudar e jogar','Peso, memória e desempenho na decisão.'),('notebook-gamer-ou-pc-gamer','Notebook ou computador de mesa?','Compare mobilidade e possibilidade de upgrades.'),('melhor-notebook-gamer-custo-beneficio','Como comparar notebooks gamer','Confira a configuração completa.')],
 'creator-streaming': [('setup-streaming-iniciante','Streaming para iniciantes','Uma ordem de investimentos.'),('melhor-webcam-para-stream','Como escolher uma webcam','Enquadramento, foco e luz.'),('webcam-1080p-ou-4k-para-streaming','Webcam 1080p ou 4K?','Quando resolução extra ajuda.')],
 'casa-inteligente': [('smart-plug-max-quando-faz-sentido','Smart Plug Max: quando faz sentido','Confira instalação, carga e compatibilidade.')],
}
PAIR_DATA = [
 ('mouses','Mouse: G203 ou G305?','g203','g305', [('Conexão','USB com fio','LIGHTSPEED com receptor USB'),('Alimentação','Pelo cabo USB','Pilha AA'),('Motivo para escolher','Cabo aceitável e compra mais simples','Liberdade sem fio como prioridade'),('Quando pagar mais','Não pague pelo RGB se ele não muda seu uso','Quando tirar o cabo resolve uma limitação real')], 'Se o formato servir à sua mão e o cabo não atrapalhar, o G203 pode ser a compra mais racional. O G305 muda a conexão e a alimentação; isso não o torna automaticamente superior em todos os usos.'),
 ('monitores','Monitor: LG UltraGear ou AOC 24G4/P?','lg-24gs60f','aoc-24g4', [('Recorte de uso','Full HD IPS, até 180 Hz','Full HD IPS, até 180 Hz'),('Base','Ajuste de inclinação','Inclui ajuste de altura'),('Custo a considerar','Monitor e eventual suporte separado','Monitor com base ajustável'),('Limite da comparação','Não há medição própria de resposta','Mesmos Hz não provam a mesma resposta')], 'A base é a diferença decisiva documentada aqui. Some o custo de um suporte se precisar dele. Frequência nominal não basta para declarar um painel melhor: resposta, movimento e compatibilidade exigem análise específica.'),
 ('headsets','Headset: Havit H2002D ou Cloud III?','havit-h2002d','cloud-iii', [('Conexão','3,5 mm analógica','3,5 mm, USB-C e USB-A'),('Microfone','Destacável','Destacável'),('Motivo para escolher','Entrada analógica já resolve seu uso','Você precisa alternar rotas de conexão'),('Cuidado','Conferir entradas e adaptadores','Não confundir Wired com Wireless')], 'O Havit atende a uma proposta analógica direta. O Cloud III ganha espaço quando USB faz diferença no seu conjunto de aparelhos. Não atribuimos vantagem sonora apenas ao tamanho do driver, e não realizamos teste próprio de conforto.'),
 ('webcams','Webcam: Brio 100 ou C920s?','brio-100','c920s', [('Vídeo Full HD','Até 30 fps','Até 30 fps'),('Foco','Fixo','Automático'),('Privacidade','Obturador integrado','Obturador físico'),('Motivo para escolher','Você fica à mesma distância','A distância à câmera varia')], 'Em chamadas com posição estável, a Brio 100 pode resolver a necessidade por menos, se o preço final confirmar essa vantagem. A C920s acrescenta autofocus. Nenhuma das duas oferece 4K; cuide da iluminação antes de esperar uma melhora só com a troca de câmera.'),
]
PAIR_DATA += [
 ('cameras','Câmera: Tapo C200 ou C210?','tapo-c200','tapo-c210',[('Resolução','Full HD 1080p','2K, 3 MP'),('Uso','Monitoramento interno','Monitoramento interno'),('O que comparar','Enquadramento, instalação e gravação','Detalhe adicional e custo de gravação'),('Limite','Rotação não mostra tudo ao mesmo tempo','Mais pixels não garantem melhor visão em pouca luz')],'A C210 traz mais resolução documentada. A C200 continua sendo uma alternativa quando Full HD atende e o preço final é menor. Confira a revisão do hardware e o custo do armazenamento antes de decidir.'),
 ('assistentes','Alexa: Echo Pop ou Echo Dot?','echo-pop','echo-dot',[('Uso comum','Voz, música e comandos compatíveis','Voz, música e comandos compatíveis'),('Diferencial nesta seleção','Formato compacto para uma rotina simples','Sensor interno de temperatura'),('Antes de comprar','Verifique serviços e dispositivos','Verifique as rotinas que usariam o sensor'),('Critério de valor','Pagar menos pelas funções necessárias','Pagar mais por funções que você vai usar')],'O sensor de temperatura é um motivo objetivo para considerar o Dot. Se ele não entrar nas suas rotinas, compare o custo com o Pop. Não declaramos um vencedor de qualidade sonora sem uma comparação de escuta adequada.'),
 ('hubs','Hub: TP-Link UH400 ou Anker 332?','uh400','anker-332',[('Conector do computador','USB-A','USB-C'),('Função','Mais portas USB-A para dados','Dados, HDMI e passagem de energia compatível'),('Vídeo','Não oferece HDMI','HDMI até 4K a 30 Hz'),('Cuidado','Demanda de energia dos periféricos','USB-C precisa suportar as funções desejadas')],'Eles resolvem necessidades diferentes. O UH400 amplia portas USB-A. O Anker acrescenta funções de vídeo e energia sob condições de compatibilidade. Para usar HDMI, confirme suporte de vídeo na porta do notebook antes de pagar pelo hub.'),
 ('microfones','Microfone: SoloCast ou FIFINE AM8?','solocast','fifine-am8',[('Conexão','USB','USB e XLR'),('Proposta','Uso direto no computador','Uso USB com possibilidade de cadeia XLR'),('Captação','Cardioide','Dinâmico cardioide'),('Custo adicional','Confira suporte necessário','Interface e cabo se usar XLR')],'Para começar em USB, simplicidade e custo do conjunto pesam. O AM8 oferece XLR, mas essa rota exige outros componentes e altera o funcionamento de controles. Nenhum deles dispensa posicionamento e atenção ao ambiente.'),
 ('quadcast','Microfone: QuadCast 2 ou 2 S?','quadcast-2','quadcast-2s',[('Padrões de captação','Quatro selecionáveis','Quatro selecionáveis'),('Conexão','USB-C e saída para fones','USB-C e saída para fones'),('Áudio digital anunciado','Até 24 bits / 96 kHz','Até 32 bits / 192 kHz'),('Motivo para pagar mais','Recursos principais de captação','Personalização aRGB e recursos adicionais')],'Para voz transmitida, mais bits e kHz não são prova de melhora perceptível. O QuadCast 2 pode oferecer os padrões de captação necessários; a escolha do 2 S pede utilidade concreta para seus extras.'),
 ('atalhos','Controle: Stream Deck Mini ou MK.2?','stream-deck-mini','stream-deck-mk2',[('Teclas LCD','6','15'),('Uso','Poucas ações repetidas','Mais comandos visíveis ao mesmo tempo'),('Rotina','Pode exigir troca entre páginas','Mais ações em uma única página'),('Antes de investir','Mapeie os comandos que repete','Confira se precisa de mais que seis teclas')],'Conte quantas ações você quer ter à vista. O MK.2 se justifica quando a troca de páginas atrapalha; o Mini atende uma rotina mais curta. Os dois exigem configuração e integrações compatíveis.'),
 ('armazenamento','Armazenamento: interno ou portátil?','kingston-a400','sandisk-portable',[('Instalação','Interna, SATA de 2,5 polegadas','Externa, USB'),('Capacidade selecionada','480 GB','1 TB'),('Necessidade','Upgrade de computador compatível','Levar arquivos entre aparelhos'),('Custo completo','Unidade, instalação e migração','Unidade e conexão compatível')],'São propostas e capacidades diferentes, portanto comparar apenas o preço seria enganoso. Escolha primeiro entre instalar armazenamento no computador ou carregar arquivos com você. Em ambos os casos, mantenha uma cópia adicional dos dados importantes.'),
]

def esc(v): return escape(str(v), quote=True)
def merchant(p): return f"https://www.amazon.com.br/dp/{p['asin']}?tag=cortexofertas-20"
def nav():
    links = '<a href="/recomendados/">Produtos</a><a href="/comparativos/">Comparativos</a><a href="/guias/">Guias</a><a href="/metodologia.html">Como avaliamos</a>'
    return f'<header><div class="nav"><a class="brand" href="/">Córtex Ofertas</a><nav aria-label="Principal">{links}</nav><details class="mobile-menu"><summary>Menu</summary><nav aria-label="Menu móvel">{links}</nav></details></div></header>'

def page(path, title, description, body):
    route = '/' + path.replace('index.html','')
    html = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | Córtex Ofertas</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://cortex-ofertas.pages.dev{route}">
<meta property="og:title" content="{esc(title)} | Córtex Ofertas"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="https://cortex-ofertas.pages.dev{route}">
<link rel="stylesheet" href="/assets/cortex/catalogo.css"></head><body>{nav()}<main class="wrap">{body}</main>
<footer><div class="wrap"><nav aria-label="Rodapé"><a href="/sobre.html">Sobre a Córtex</a><a href="/metodologia.html">Como avaliamos</a><a href="/transparencia.html">Transparência</a><a href="/politica-de-privacidade.html">Privacidade</a><a href="/termos-de-uso.html">Termos</a></nav><p>Como associado da Amazon, eu ganho com compras qualificadas. Os links comerciais estão identificados. Preço, disponibilidade, frete e vendedor devem ser confirmados na Amazon.</p></div></footer></body></html>'''
    (ROOT / path).write_text(html.replace('><', '>\n<')+'\n', encoding='utf-8')

def card(p, compact=False, alias=None):
    photo = f'<a class="product-photo" href="{merchant(p)}" rel="sponsored nofollow noopener" target="_blank" aria-label="Ver {esc(p["name"])} na Amazon"><img src="{esc(p["image"])}" alt="{esc(p["name"] + ": " + p["variant"])}" loading="lazy" width="600" height="450"></a>' if p.get('image') else ''
    alt = BY_ID.get(p.get('alternative'))
    alternate = f'<p><strong>Compare também:</strong> <a href="/recomendados/#{alt["id"]}">{esc(alt["name"])}</a>.</p>' if alt else ''
    source_url = merchant(p) if 'amazon.' in p['source'] else p['source']
    source_rel = 'sponsored nofollow noopener' if 'amazon.' in p['source'] else 'noopener'
    details = '' if compact else f'''<details><summary>Por que escolhemos e quando evitar</summary><div class="detail-body"><h4>Nossa análise</h4><p>{esc(p['reason'])}</p><h4>Quando não escolher</h4><p>{esc(p['avoid'])}</p><h4>Quando o preço compensa</h4><p>{esc(p['value'])}</p>{alternate}<p class="variant"><strong>Versão desta seleção:</strong> {esc(p['variant'])}.</p><p class="source-links"><a href="{esc(source_url)}" target="_blank" rel="{source_rel}">Fonte do produto</a><a href="/metodologia.html">Entenda nossa avaliação</a></p><small class="disclosure">Curadoria documental revista em 08/09/2026. Sem teste próprio deste produto. A oferta atual é confirmada no varejista.</small></div></details>'''
    anchor=f'<span id="{alias}"></span>' if alias else ''
    return f'''<article class="product-card" id="{p['id']}" data-asin="{p['asin']}" data-merchant-state="active">{anchor}{photo}<div class="product-copy"><span class="role">{esc(p['role'])}</span><h3>{esc(p['name'])}</h3><p>{esc(p['fit'])}</p><ul class="specs">{''.join('<li>'+esc(s)+'</li>' for s in p['specs'])}</ul><p class="verdict"><b>Atenção:</b> {esc(p['avoid'])}</p><a class="cta" href="{merchant(p)}" rel="sponsored nofollow noopener" target="_blank">Consultar preço na Amazon</a><small class="disclosure">Publicidade · link de afiliado. Confira preço, variante, frete e vendedor.</small>{details}</div></article>'''

def niche_nav(current=None, anchors=False):
    return '<nav class="niche-nav" aria-label="Escolha por uso">' + ''.join(f'<a href="{("#" + k) if anchors else ("/"+k+"/")}"'+(' aria-current="page"' if current==k else '')+f'>{esc(v[0])}</a>' for k,v in NICHES.items()) + '</nav>'

def readings(key):
    return '<div class="reading">'+''.join(f'<a href="/guia/{slug}.html">{esc(title)}<span>{esc(desc)}</span></a>' for slug,title,desc in GUIDES[key])+'</div>'

def context_photos(keys):
    photos=json.loads((ROOT/'data/editorial-visuals.json').read_text())['photos']
    destinations={'home':('/guias/','Planeje antes de comprar'),'gaming':('/setup-games/','Jogos e periféricos'),'work':('/trabalho-estudo/','Trabalho e estudo'),'creator':('/creator-streaming/','Criação de conteúdo'),'home_automation':('/casa-inteligente/','Casa inteligente')}
    return '<section class="section"><h2>Continue a pesquisa por uso</h2><div class="reading">'+''.join(f'<a href="{destinations[k][0]}"><img class="context-photo" data-editorial-photo="{k}" src="{esc(photos[k]["url"])}" alt="Fotografia editorial de contexto: {esc(destinations[k][1])}" loading="lazy">{esc(destinations[k][1])}<span>Leia os critérios e explore as escolhas.</span></a>' for k in keys)+'</div></section>'

def niche_items(key):
    order=['mouses','teclados','mousepads','headsets','monitores','notebooks','hubs','webcams','armazenamento','microfones','captura','controles','tomadas','cameras','iluminacao','rede','assistentes']
    return sorted([p for p in PRODUCTS if p['niche']==key],key=lambda p:order.index(p['group']))

def render_catalog():
    body = f'<section class="intro catalog-intro"><div class="eyebrow">Curadoria Córtex</div><h1>Escolhas para você.</h1><p class="lead">Compare o que muda no uso e quando pagar mais faz sentido. Confira as ofertas na Amazon.</p><p class="method-note">{len(PRODUCTS)} produtos · 4 nichos · <a href="/metodologia.html">Como avaliamos</a></p></section><div id="shortlists">{niche_nav(anchors=True)}'
    categories={'setup-games':'Mouses, teclado, mousepad, headsets e monitores.','trabalho-estudo':'Notebook, periféricos, chamadas, hubs e armazenamento.','creator-streaming':'Webcams, microfones, captura e atalhos.','casa-inteligente':'Tomada, câmeras, iluminação, rede e Alexa.'}
    for key,(name,headline,intro,_) in NICHES.items():
        items=niche_items(key)
        body+=f'<section class="section" id="{key}"><div class="section-head"><div><div class="eyebrow">{len(items)} produtos</div><h2>{esc(name)}</h2><p>{esc(categories[key])}</p></div><a href="/{key}/">Como escolher neste nicho</a></div>'
        aliases={'g305':'mouses','lg-24gs60f':'monitores','havit-h2002d':'headsets','c920s':'webcams'}
        if key=='trabalho-estudo': body+='<span id="trabalho"></span>'
        body+='<div class="product-grid">'+''.join(card(p,alias=aliases.get(p['id'])) for p in items)+'</div></section>'
    body+='</div><section class="section"><h2>Está em dúvida entre duas opções?</h2><p>Veja o que muda no uso, a limitação de cada modelo e quando o adicional de preço se justifica.</p><a href="/comparativos/">Abrir comparações lado a lado</a></section>'
    body+=context_photos(['home','gaming','home_automation'])
    page('recomendados/index.html','Produtos recomendados',f'{len(PRODUCTS)} produtos de tecnologia com fotos, razões de escolha, limitações, alternativas e links para consultar preços na Amazon.',body)

def render_pairs():
    labels={'microfones':'USB ou XLR','quadcast':'QuadCast 2 ou 2 S','atalhos':'Stream Deck'}
    body='<section class="intro"><div class="eyebrow">Comparações da Córtex</div><h1>O que você ganha ao pagar mais?</h1><p class="lead">Compare diferenças que mudam o uso. Cada confronto mostra em que situação uma escolha faz mais sentido.</p><p class="method-note">As tabelas comparam características documentadas. Os preços mudam; confira o total das duas ofertas na Amazon antes de decidir.</p></section><nav class="niche-nav" aria-label="Comparações">'+''.join(f'<a href="#{pair[0]}">{esc(labels.get(pair[0],pair[1].split(":")[0]))}</a>' for pair in PAIR_DATA)+'</nav>'
    for anchor,title,a,b,rows,conclusion in PAIR_DATA:
        p,q=BY_ID[a],BY_ID[b]
        table='<div class="table-wrap"><table><thead><tr><th>Critério</th><th>'+esc(p['name'])+'</th><th>'+esc(q['name'])+'</th></tr></thead><tbody>'+''.join(f'<tr><td data-label="Critério">{esc(r[0])}</td><td data-label="{esc(p["name"])}">{esc(r[1])}</td><td data-label="{esc(q["name"])}">{esc(r[2])}</td></tr>' for r in rows)+'</tbody></table></div>'
        body+=f'<section class="section" id="{anchor}"><h2>{esc(title)}</h2><p>{esc(conclusion)}</p>{table}<div class="pair">{card(p,True)}{card(q,True)}</div><div class="aside-note"><p><strong>Leitura da Córtex:</strong> {esc(p["value"])}</p><p><a href="/recomendados/#{a}">Ler análise de {esc(p["name"])}</a> · <a href="/recomendados/#{b}">Ler análise de {esc(q["name"])}</a></p></div></section>'
    body+=context_photos(['home','gaming','creator'])
    page('comparativos/index.html','Compare antes de comprar','Comparações com fotos e critérios de compra: periféricos, áudio, vídeo, armazenamento e casa inteligente. Saiba quando pagar mais faz sentido.',body)

def render_hubs():
    decisions={
      'setup-games':[('Defina o problema','Mais botões, liberdade sem fio, ajuste de altura ou conexão de áudio: escolha primeiro o que precisa mudar.'),('Confira o conjunto','Verifique portas, espaço na mesa e capacidade do computador antes de escolher pelo número de Hz ou DPI.'),('Compare o custo completo','Inclua suporte, adaptador e frete. Um preço menor no anúncio pode exigir uma compra adicional.')],
      'trabalho-estudo':[('Comece pelos programas','Sistema operacional, memória e conexões precisam atender aos programas que você usa todos os dias.'),('Escolha pelo desconforto real','Tela, teclado, mouse ou chamadas podem ser um investimento mais útil do que trocar um computador que ainda atende.'),('Confira os acessórios','Um hub amplia portas, mas não necessariamente carrega o notebook ou transmite vídeo. Verifique a função exata.')],
      'creator-streaming':[('Áudio antes de extras','Confira conexão e posicionamento do microfone. Recursos de iluminação ou controle não corrigem áudio inadequado.'),('Imagem depende da cena','Enquadramento, iluminação e distância da câmera importam junto de resolução e foco.'),('Compre por etapa','Identifique a limitação atual, corrija-a e avalie o resultado antes de montar um kit inteiro.')],
      'casa-inteligente':[('Defina uma tarefa','Controlar energia, melhorar cobertura de rede e monitorar um ambiente pedem produtos diferentes.'),('Cheque a compatibilidade','Wi-Fi, aplicativo, assistente, encaixe e alimentação devem ser conferidos para o modelo e a instalação.'),('Considere custos adicionais','Armazenamento, serviços de nuvem, unidades extras e instalação podem mudar o custo total.')],
    }
    for key,(name,title,intro,photo_key) in NICHES.items():
        items=niche_items(key)
        body=f'<section class="intro"><div class="eyebrow">{esc(name)}</div><h1>{esc(title)}</h1><p class="lead">{esc(intro)}</p><p class="method-note">Curadoria documental · {len(items)} produtos nesta seleção · <a href="/metodologia.html">Como avaliamos</a></p></section>{niche_nav(key)}<section class="section" id="produtos"><h2>Escolhas para sua rotina</h2><p>Abra a análise de cada produto para entender a recomendação, a versão selecionada e quando o preço compensa.</p><div class="product-grid">'+''.join(card(p) for p in items)+'</div></section>'
        body+='<section class="section"><h2>Três decisões antes da compra</h2><div class="decision-grid">'+''.join('<article class="decision"><h3>'+esc(h)+'</h3><p>'+esc(p)+'</p></article>' for h,p in decisions[key])+'</div></section>'
        body+=f'<section class="section"><h2>Aprofunde sua escolha</h2>{readings(key)}</section>'
        if key=='setup-games':body+='<p class="anchors"><a href="/comparativos/#mouses">G203 ou G305?</a><a href="/comparativos/#monitores">LG ou AOC?</a><a href="/comparativos/#headsets">Havit ou Cloud III?</a></p>'
        if key=='creator-streaming':body+='<p><a href="/comparativos/#webcams">Compare Brio 100 e C920s lado a lado</a></p>'
        roles={'setup-games':['gaming'],'trabalho-estudo':['work','home','gaming'],'creator-streaming':['creator','home','work'],'casa-inteligente':['home_automation','home','work']}
        body+=context_photos(roles[key])
        page(key+'/index.html',name,intro,body)

def render_method():
    body='''<section class="intro"><div class="eyebrow">Como avaliamos</div><h1>A recomendação precisa ter um motivo.</h1><p class="lead">A Córtex pesquisa produtos para ajudar você a decidir o que comprar na Amazon — e quando uma compra não vale a pena para o seu uso.</p></section><div class="prose">
<section><h2>O que fazemos hoje</h2><p>Nossas avaliações são <strong>curadorias documentais</strong>: analisamos fichas técnicas, documentação do fabricante, identidade do produto e diferenças entre alternativas. Não apresentamos este trabalho como teste físico próprio.</p><p>Quando uma conclusão depende de desempenho medido — como resposta de monitor, qualidade de microfone ou autonomia real — uma ficha técnica não basta. Sem evidência adequada, explicitamos o limite e não atribuímos uma vantagem comprovada.</p></section>
<section><h2>Como um produto entra na seleção</h2><ol><li><strong>Necessidade:</strong> definimos o problema de uso e os critérios que podem mudar a decisão.</li><li><strong>Identidade:</strong> conferimos modelo, versão e especificações relevantes. Nomes parecidos podem indicar configurações diferentes.</li><li><strong>Comparação:</strong> explicamos o benefício concreto, a limitação e a alternativa que atende a outra prioridade.</li><li><strong>Valor:</strong> mostramos em que condição um preço maior se justifica, considerando acessórios, frete e custos adicionais.</li><li><strong>Fontes:</strong> indicamos a documentação utilizada e a data da revisão documental.</li></ol></section>
<section><h2>Como tratamos qualidade e preço</h2><p>Qualidade depende do uso. Uma base de monitor ajustável é uma característica verificável; conforto e qualidade sonora precisam de evidências próprias e também variam entre pessoas. Diferenciamos especificação, interpretação editorial e resultado de teste.</p><p>O site não acompanha preços em tempo real nem promete o menor preço do mercado. O botão de cada produto abre o anúncio para você conferir preço, vendedor, frete, variante e disponibilidade. Nossa comparação de custo-benefício explica <strong>quando pagar mais faz sentido</strong>; ela não substitui a consulta das ofertas atuais.</p><p>Não publicamos notas inventadas, estrelas sem origem, descontos sem referência ou relatos de experiência que não tivemos. Uma indicação documental não é garantia de desempenho, durabilidade ou satisfação individual.</p></section>
<section><h2>Comissão e independência</h2><p>Como associado da Amazon, eu ganho com compras qualificadas. Os links comerciais são identificados perto do botão. A possibilidade de comissão não é uma evidência de qualidade e não substitui os critérios de seleção.</p><p>Uma recomendação deve continuar compreensível mesmo sem o botão de compra: você precisa saber para quem o produto serve, quando evitar e o que comparar.</p></section>
<section><h2>O que você deve conferir antes de comprar</h2><p>Compare o mesmo modelo e a mesma configuração. Verifique o valor final, prazo, vendedor, garantia anunciada e compatibilidade com seus aparelhos. A data de revisão do texto não significa que preço e estoque tenham sido atualizados naquele momento.</p><p><a href="/comparativos/">Veja os critérios aplicados nas comparações</a> · <a href="/recomendados/">Explore os produtos selecionados</a></p></section></div>'''
    page('metodologia.html','Como avaliamos produtos','Entenda as fontes, os critérios e os limites da curadoria da Córtex. Sem testes próprios fictícios ou preços apresentados como atuais.',body)

def render_about():
    body='''<section class="intro"><div class="eyebrow">Sobre a Córtex</div><h1>Menos pesquisa solta.<br>Mais clareza para comprar.</h1><p class="lead">A Córtex Ofertas é uma curadoria de tecnologia para quem quer entender o que muda entre produtos antes de gastar.</p></section><div class="prose"><section><h2>A ideia por trás da seleção</h2><p>Uma lista de especificações pode dizer muito sobre um produto e pouco sobre a sua escolha. Nosso papel é ligar essas informações à sua rotina: o que resolve um problema, qual limitação permanece e quando uma alternativa merece atenção.</p><p>Organizamos o catálogo em quatro contextos: jogos, trabalho e estudo, criação de conteúdo e casa inteligente. Em cada um, buscamos escolhas com funções claras, evitando tratar um mesmo produto como resposta para todas as pessoas.</p></section><section><h2>O que esperar de uma avaliação</h2><p>Você encontra razões de escolha, pontos de atenção, comparação de recursos e orientações para avaliar o preço pedido. Trata-se de pesquisa documental, com fontes indicadas; não afirmamos ter usado ou testado fisicamente os produtos desta seleção.</p><p>Os botões levam à Amazon, onde a compra é realizada. A Córtex não é a loja vendedora e não recebe o pagamento pelo produto. Podemos receber comissão por compras qualificadas feitas pelos links de afiliado.</p></section><section><h2>Comece por uma dúvida concreta</h2><p>Precisa tirar o cabo da mesa, melhorar uma chamada ou controlar um aparelho da casa? Esse é um ponto de partida mais útil que escolher somente pela maior especificação.</p><p><a href="/recomendados/">Encontre produtos para o seu uso</a> · <a href="/comparativos/">Compare duas alternativas</a> · <a href="/metodologia.html">Conheça nossa metodologia</a></p></section></div>'''
    page('sobre.html','Sobre a Córtex','Curadoria de tecnologia com motivos de escolha, fontes e comparações para decidir o que comprar na Amazon.',body)

if __name__ == '__main__':
    render_catalog()
    render_pairs()
    render_hubs()
    render_method()
    render_about()
    print(f'Authored 8 source pages from {len(PRODUCTS)} products. Build remains packaging-only.')
