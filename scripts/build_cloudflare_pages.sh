#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
PUBLIC_ORIGIN="https://cortex-ofertas.pages.dev"
LEGACY_ORIGIN="https://cortex-public.vercel.app"

rm -rf "$DIST"
mkdir -p "$DIST"

# RG6 BUILD_PURITY: packaging only. Buyer-facing semantics must already exist in SOURCE.
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='.vercel/' \
  --exclude='dist/' \
  --exclude='scripts/' \
  --exclude='CLOUDFLARE_MIGRATION.md' \
  --exclude='release-state.json' \
  "$ROOT/" "$DIST/"

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

# Infrastructure-only response headers are generated in dist; no buyer-facing HTML is changed.
cat > "$DIST/_headers" <<'EOF'
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), camera=(), microphone=()
  X-Frame-Options: SAMEORIGIN

/assets/*
  Cache-Control: public, max-age=86400, stale-while-revalidate=604800
EOF

# Fail closed on stale source semantics. Never rewrite them in dist.
for file in "${primary_routes[@]}"; do
  test -f "$file"
done

test ! -e "$DIST/release-state.json"
test ! -e "$DIST/.git"
test ! -e "$DIST/.github"
test ! -e "$DIST/scripts"

if grep -RIl --binary-files=without-match -- 'hennanst-20' "$DIST" | grep -q .; then
  echo "Obsolete affiliate tag exists in source/publish bundle; refusing build-time repair" >&2
  exit 1
fi
if grep -RIl --binary-files=without-match -- "$LEGACY_ORIGIN" "$DIST" | grep -q .; then
  echo "Legacy Vercel origin exists in source/publish bundle; refusing build-time repair" >&2
  exit 1
fi

# Source-truth parity: rsync packaging must preserve every buyer-facing primary route byte-for-byte.
for dist_file in "${primary_routes[@]}"; do
  rel="${dist_file#${DIST}/}"
  cmp --silent "$ROOT/$rel" "$dist_file" || {
    echo "RG6 BUILD_PURITY violation: dist differs from source for $rel" >&2
    exit 1
  }
done

# Commercial safety assertions validate source-derived dist without altering it.
grep -q 'B07GPRWFC5?tag=cortexofertas-20' "$DIST/setup-games/index.html"
grep -q 'B087CT8PWY?tag=cortexofertas-20' "$DIST/setup-games/index.html"
grep -q 'B0D6HXDRZL?tag=cortexofertas-20' "$DIST/trabalho-estudo/index.html"
grep -q 'B0CJRXT3L6?tag=cortexofertas-20' "$DIST/creator-streaming/index.html"

echo "RG6_BUILD_PURITY_PACKAGE_PASS: source copied without buyer-facing semantic mutation at $DIST"
