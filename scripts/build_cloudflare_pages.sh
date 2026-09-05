#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
PUBLIC_ORIGIN="https://cortex-ofertas.pages.dev"
LEGACY_ORIGIN="https://cortex-public.vercel.app"

rm -rf "$DIST"
mkdir -p "$DIST"

rsync -a --delete \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='.vercel/' \
  --exclude='dist/' \
  --exclude='scripts/' \
  --exclude='CLOUDFLARE_MIGRATION.md' \
  --exclude='release-state.json' \
  "$ROOT/" "$DIST/"

while IFS= read -r -d '' file; do
  sed -i "s#${LEGACY_ORIGIN}#${PUBLIC_ORIGIN}#g" "$file"
done < <(grep -rlZ --binary-files=without-match -- "$LEGACY_ORIGIN" "$DIST" || true)

primary_routes=(
  "$DIST/index.html"
  "$DIST/setup-games/index.html"
  "$DIST/trabalho-estudo/index.html"
  "$DIST/creator-streaming/index.html"
  "$DIST/casa-inteligente/index.html"
  "$DIST/guias/index.html"
  "$DIST/comparativos/index.html"
  "$DIST/recomendados/index.html"
)
for file in "${primary_routes[@]}"; do
  test -f "$file"
  sed -i 's/hennanst-20/cortexofertas-20/g' "$file"
  sed -i 's#</head>#<style id="cortex-mobile-width-guard">html,body{max-width:100%;overflow-x:hidden}main,section,article,nav,.card,.comparison-grid,.pillar-grid,.product-card{min-width:0;max-width:100%}img,svg,video,iframe{max-width:100%;height:auto}a,p,h1,h2,h3,li,span{overflow-wrap:anywhere;word-break:normal}@media(max-width:760px){.comparison-grid,.pillar-grid{grid-template-columns:minmax(0,1fr)!important}.card,.product-card,.product-module{max-width:100%!important}header nav{max-width:100vw!important}}</style></head>#' "$file"
done

CRO_STYLE='<style id="cortex-g8-cro">.g8-hero{display:grid;grid-template-columns:1.15fr .85fr;gap:18px;margin:0 0 34px;align-items:stretch}.g8-hero img,.g8-tile img{display:block;width:100%;height:100%;object-fit:cover;border-radius:22px;border:1px solid rgba(255,255,255,.09);background:#10151c}.g8-copy{padding:28px;border:1px solid rgba(255,255,255,.09);border-radius:22px;background:linear-gradient(145deg,rgba(25,31,40,.94),rgba(14,18,24,.96));display:flex;flex-direction:column;justify-content:center}.g8-copy h2{font-size:clamp(1.7rem,4vw,3rem);margin:.25em 0}.g8-copy p{color:#b7c0cb;max-width:650px}.g8-link{display:inline-flex;width:max-content;margin-top:8px;padding:12px 18px;border-radius:999px;background:#62f6a5;color:#07110c!important;text-decoration:none;font-weight:850}.g8-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin:24px 0 38px}.g8-tile{min-width:0}.g8-tile img{aspect-ratio:16/10}.g8-tile a{text-decoration:none}.g8-caption{padding:12px 2px 0;color:#c9d1db;font-size:.9rem}@media(max-width:760px){.g8-hero,.g8-grid{grid-template-columns:minmax(0,1fr)}.g8-copy{padding:21px}.g8-hero{margin-bottom:26px}.g8-link{width:100%;justify-content:center}}</style>'
for file in "$DIST/trabalho-estudo/index.html" "$DIST/creator-streaming/index.html" "$DIST/casa-inteligente/index.html" "$DIST/guias/index.html" "$DIST/comparativos/index.html" "$DIST/recomendados/index.html"; do
  sed -i "s|</head>|${CRO_STYLE}</head>|" "$file"
done

# Remove visibly unfinished merchant modules from public primary routes until
# Product/Destination validation supplies a live destination. Setup & Games is
# excluded because its two merchant CTAs are already validated.
BLOCKED_STYLE='<style id="cortex-g9-blocked-cleanup">.product-module:has([data-merchant-state="blocked"]){display:none!important}</style>'
for file in "$DIST/trabalho-estudo/index.html" "$DIST/creator-streaming/index.html" "$DIST/casa-inteligente/index.html" "$DIST/comparativos/index.html" "$DIST/recomendados/index.html"; do
  sed -i "s|</head>|${BLOCKED_STYLE}</head>|" "$file"
done

WORK_HERO='<section class="g8-hero" aria-label="Destaque Trabalho e Estudo"><img src="../assets/cortex/category-work-v1.svg" alt="Seleção editorial Córtex para trabalho e estudo"><div class="g8-copy"><div class="eyebrow">Trabalho &amp; Estudo</div><h2>Monte a rotina pelo gargalo real.</h2><p>Notebook, tela e periféricos entram pela função: mobilidade, leitura, chamadas e produtividade — não por uma lista genérica de especificações.</p><a class="g8-link" href="#guias-para-decidir">Ver critérios de escolha →</a></div></section><div class="g8-grid"><div class="g8-tile"><img src="../assets/cortex/product-ideapad-editorial-v1.svg" alt="Ilustração editorial do Lenovo IdeaPad 1"><div class="g8-caption">Notebook já presente na curadoria ativa, com contexto de uso e trade-off explícito.</div></div><div class="g8-tile"><img src="../assets/cortex/category-work-v1.svg" alt="Tecnologia para produtividade e estudo"><div class="g8-caption">Prioridade em conforto, portabilidade e produtividade cotidiana.</div></div></div>'
sed -i "0,/<main>/s|<main>|<main>${WORK_HERO}|" "$DIST/trabalho-estudo/index.html"
sed -i 's|<section><h2>Guias para decidir</h2>|<section id="guias-para-decidir"><h2>Guias para decidir</h2>|' "$DIST/trabalho-estudo/index.html"

COMPARE_HERO='<section class="g8-hero" aria-label="Destaque Comparativos"><div class="g8-copy"><div class="eyebrow">Comparativos</div><h2>Compare pelo uso, não pelo número maior.</h2><p>Colocamos dois caminhos lado a lado e explicitamos o que muda na prática: liberdade, peso, autonomia, simplicidade e custo de oportunidade.</p><a class="g8-link" href="../setup-games/">Ver seleção ativa em Setup &amp; Games →</a></div><img src="../assets/cortex/category-gaming-v1.svg" alt="Comparativos de tecnologia e setup"></section><div class="g8-grid"><a class="g8-tile" href="../setup-games/"><img src="../assets/cortex/product-g305-editorial-v1.svg" alt="Logitech G305 em linguagem editorial Córtex"><div class="g8-caption">G305 · liberdade sem fio e autonomia.</div></a><a class="g8-tile" href="../setup-games/"><img src="../assets/cortex/product-g203-editorial-v1.svg" alt="Logitech G203 em linguagem editorial Córtex"><div class="g8-caption">G203 · simplicidade com fio e menor peso.</div></a></div>'
sed -i "0,/<main>/s|<main>|<main>${COMPARE_HERO}|" "$DIST/comparativos/index.html"

RECO_HERO='<section class="g8-hero" aria-label="Destaque Recomendados"><img src="../assets/cortex/hero-tech-v1.svg" alt="Curadoria de tecnologia Córtex Ofertas"><div class="g8-copy"><div class="eyebrow">Recomendados</div><h2>Shortlists pequenas, justificadas e acionáveis.</h2><p>Cada indicação precisa dizer para quem faz sentido, por que entrou, qual é o trade-off e qual alternativa considerar.</p><a class="g8-link" href="../setup-games/">Explorar recomendações ativas →</a></div></section><div class="g8-grid"><a class="g8-tile" href="../setup-games/"><img src="../assets/cortex/category-gaming-v1.svg" alt="Recomendações de setup e games"><div class="g8-caption">Setup &amp; Games · escolhas ativas com destino comercial validado.</div></a><a class="g8-tile" href="../trabalho-estudo/"><img src="../assets/cortex/category-work-v1.svg" alt="Recomendações de trabalho e estudo"><div class="g8-caption">Trabalho &amp; Estudo · decisões para uma rotina híbrida.</div></a></div>'
sed -i "0,/<main>/s|<main>|<main>${RECO_HERO}|" "$DIST/recomendados/index.html"

CREATOR_HERO='<section class="g8-hero" aria-label="Destaque Creator e Streaming"><img src="../assets/cortex/category-creator-v1.svg" alt="Creator e streaming na linguagem visual Córtex"><div class="g8-copy"><div class="eyebrow">Creator &amp; Streaming</div><h2>Áudio, luz e enquadramento antes da ficha técnica.</h2><p>Organize o setup pela qualidade percebida pelo público e pelo gargalo do seu fluxo — não por resolução ou acessórios isolados.</p><a class="g8-link" href="#creator-guias">Explorar guias →</a></div></section><div class="g8-grid"><div class="g8-tile"><img src="../assets/cortex/hero-tech-v1.svg" alt="Tecnologia para criação de conteúdo"><div class="g8-caption">Escolhas por função: voz, imagem, iluminação e fluxo.</div></div><div class="g8-tile"><img src="../assets/cortex/category-creator-v1.svg" alt="Ecossistema de creator e streaming"><div class="g8-caption">Menos equipamento por impulso; mais clareza sobre o gargalo real.</div></div></div>'
sed -i "0,/<main>/s|<main>|<main>${CREATOR_HERO}|" "$DIST/creator-streaming/index.html"
sed -i 's|<section><h2>Guias para decidir</h2>|<section id="creator-guias"><h2>Guias para decidir</h2>|' "$DIST/creator-streaming/index.html"

HOME_HERO='<section class="g8-hero" aria-label="Destaque Casa Inteligente"><div class="g8-copy"><div class="eyebrow">Casa Inteligente</div><h2>Automatize o problema certo.</h2><p>Comece pela função: controlar um aparelho, adicionar voz ou melhorar o streaming. Categorias diferentes não precisam virar um ranking artificial.</p><a class="g8-link" href="../recomendados/">Ver caminhos recomendados →</a></div><img src="../assets/cortex/category-home-v1.svg" alt="Casa inteligente na linguagem visual Córtex"></section><div class="g8-grid"><div class="g8-tile"><img src="../assets/cortex/category-home-v1.svg" alt="Automação residencial e entretenimento"><div class="g8-caption">Automação e entretenimento separados pelo objetivo de uso.</div></div><div class="g8-tile"><img src="../assets/cortex/hero-tech-v1.svg" alt="Ecossistema de tecnologia para casa"><div class="g8-caption">Compatibilidade, segurança e contexto antes da compra.</div></div></div>'
sed -i "0,/<main>/s|<main>|<main>${HOME_HERO}|" "$DIST/casa-inteligente/index.html"

GUIDES_HERO='<section class="g8-hero" aria-label="Destaque Guias"><img src="../assets/cortex/hero-tech-v1.svg" alt="Guias de compra Córtex Ofertas"><div class="g8-copy"><div class="eyebrow">Guias</div><h2>Critérios que continuam úteis depois da promoção.</h2><p>Os guias organizam decisões evergreen para reduzir erro de compra e evitar que uma especificação isolada vire recomendação automática.</p><a class="g8-link" href="#biblioteca-guias">Explorar biblioteca →</a></div></section><div class="g8-grid"><div class="g8-tile"><img src="../assets/cortex/category-gaming-v1.svg" alt="Guias de setup e games"><div class="g8-caption">Setup &amp; Games · desempenho, conforto e prioridade de investimento.</div></div><div class="g8-tile"><img src="../assets/cortex/category-work-v1.svg" alt="Guias de trabalho e estudo"><div class="g8-caption">Trabalho &amp; Estudo · mobilidade, legibilidade e produtividade.</div></div></div>'
sed -i "0,/<main>/s|<main>|<main>${GUIDES_HERO}<div id=\"biblioteca-guias\"></div>|" "$DIST/guias/index.html"

# Build-time market-readiness assertions for all primary nav routes.
grep -q 'category-work-v1.svg' "$DIST/trabalho-estudo/index.html"
grep -q 'product-ideapad-editorial-v1.svg' "$DIST/trabalho-estudo/index.html"
grep -q 'product-g305-editorial-v1.svg' "$DIST/comparativos/index.html"
grep -q 'product-g203-editorial-v1.svg' "$DIST/comparativos/index.html"
grep -q 'hero-tech-v1.svg' "$DIST/recomendados/index.html"
grep -q 'category-creator-v1.svg' "$DIST/creator-streaming/index.html"
grep -q 'category-home-v1.svg' "$DIST/casa-inteligente/index.html"
grep -q 'biblioteca-guias' "$DIST/guias/index.html"

legacy_count=0
while IFS= read -r -d '' file; do
  rm -f "$file"
  legacy_count=$((legacy_count + 1))
done < <(grep -rlZ --binary-files=without-match --include='*.html' --include='*.json' -- 'hennanst-20' "$DIST" || true)
find "$DIST" -type d -empty -delete || true

echo "Quarantined ${legacy_count} historical files containing obsolete affiliate tag."

cat > "$DIST/_headers" <<'EOF'
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), camera=(), microphone=()
  X-Frame-Options: SAMEORIGIN

/assets/*
  Cache-Control: public, max-age=86400, stale-while-revalidate=604800
EOF

for file in "${primary_routes[@]}"; do test -f "$file"; done
test -f "$DIST/assets/cortex/hero-tech-v1.svg"
test -f "$DIST/assets/cortex/category-work-v1.svg"
test -f "$DIST/assets/cortex/category-gaming-v1.svg"
test -f "$DIST/assets/cortex/category-creator-v1.svg"
test -f "$DIST/assets/cortex/category-home-v1.svg"
test -f "$DIST/assets/cortex/product-ideapad-editorial-v1.svg"
test -f "$DIST/assets/cortex/product-g305-editorial-v1.svg"
test -f "$DIST/assets/cortex/product-g203-editorial-v1.svg"

test ! -e "$DIST/release-state.json"
test ! -e "$DIST/.git"
test ! -e "$DIST/.github"
test ! -e "$DIST/scripts"
if grep -RIl --binary-files=without-match -- 'hennanst-20' "$DIST" | grep -q .; then
  echo "Obsolete affiliate tag remains in publish bundle" >&2
  exit 1
fi
if grep -RIl --binary-files=without-match -- "$LEGACY_ORIGIN" "$DIST" | grep -q .; then
  echo "Vercel origin remains in publish bundle" >&2
  exit 1
fi

echo "Cloudflare Pages publish bundle prepared at: $DIST"
