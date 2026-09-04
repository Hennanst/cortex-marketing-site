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

# Hosting cutover normalization: public canonicals, robots and sitemap must not
# keep pointing search engines back to the Vercel fallback.
while IFS= read -r -d '' file; do
  sed -i "s#${LEGACY_ORIGIN}#${PUBLIC_ORIGIN}#g" "$file"
done < <(grep -rlZ --binary-files=without-match -- "$LEGACY_ORIGIN" "$DIST" || true)

# The five curated commercial routes are active surfaces. Normalize only their
# obsolete affiliate tag to the current Córtex tag; historical documents outside
# these routes are quarantined instead of silently reactivated.
critical_routes=(
  "$DIST/index.html"
  "$DIST/setup-games/index.html"
  "$DIST/trabalho-estudo/index.html"
  "$DIST/comparativos/index.html"
  "$DIST/recomendados/index.html"
)
for file in "${critical_routes[@]}"; do
  test -f "$file"
  sed -i 's/hennanst-20/cortexofertas-20/g' "$file"
done

# Safety quarantine for historical affiliate documents still carrying the old
# Amazon tracking tag. Those products require Product/Destination revalidation
# before they can become active Cloudflare surfaces again.
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

# Critical public routes/assets must survive every publish bundle.
test -f "$DIST/index.html"
test -f "$DIST/setup-games/index.html"
test -f "$DIST/trabalho-estudo/index.html"
test -f "$DIST/comparativos/index.html"
test -f "$DIST/recomendados/index.html"
test -f "$DIST/assets/cortex/hero-tech-v1.svg"
test -f "$DIST/assets/cortex/product-g305-editorial-v1.svg"
test -f "$DIST/assets/cortex/product-g203-editorial-v1.svg"

# Prevent repository/CI internals and stale hosting/affiliate metadata from
# reaching the Cloudflare public surface.
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
