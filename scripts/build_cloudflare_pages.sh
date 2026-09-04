#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"

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

cat > "$DIST/_headers" <<'EOF'
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), camera=(), microphone=()
  X-Frame-Options: SAMEORIGIN

/assets/*
  Cache-Control: public, max-age=86400, stale-while-revalidate=604800
EOF

# Migration preflight: critical public routes/assets must exist.
test -f "$DIST/index.html"
test -f "$DIST/setup-games/index.html"
test -f "$DIST/trabalho-estudo/index.html"
test -f "$DIST/comparativos/index.html"
test -f "$DIST/recomendados/index.html"
test -f "$DIST/assets/cortex/hero-tech-v1.svg"
test -f "$DIST/assets/cortex/product-g305-editorial-v1.svg"
test -f "$DIST/assets/cortex/product-g203-editorial-v1.svg"
test ! -e "$DIST/release-state.json"

# Prevent accidental publication of repository/CI internals.
test ! -e "$DIST/.git"
test ! -e "$DIST/.github"
test ! -e "$DIST/scripts"

echo "Cloudflare Pages publish bundle prepared at: $DIST"
