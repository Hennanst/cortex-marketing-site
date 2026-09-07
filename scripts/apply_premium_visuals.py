#!/usr/bin/env python3
"""RG6 compatibility validator.

Historical versions of this script mutated buyer-facing HTML in dist. Under the
Source Truth recovery invariant, the workflow may still invoke this path for
compatibility, but it is validation-only: it must never edit the publish bundle.
"""
from __future__ import annotations

import sys
from pathlib import Path

DIST = Path(sys.argv[1] if len(sys.argv) > 1 else "dist").resolve()
if not DIST.exists():
    raise SystemExit(f"publish directory not found: {DIST}")

PRIMARY_ROUTES = (
    "index.html",
    "setup-games/index.html",
    "trabalho-estudo/index.html",
    "creator-streaming/index.html",
    "casa-inteligente/index.html",
    "guias/index.html",
    "comparativos/index.html",
    "recomendados/index.html",
)

for rel in PRIMARY_ROUTES:
    path = DIST / rel
    if not path.is_file():
        raise SystemExit(f"RG6 validation failed: missing primary route {rel}")
    text = path.read_text(encoding="utf-8")
    if "cortex-public.vercel.app" in text:
        raise SystemExit(f"RG6 validation failed: stale Vercel origin in {rel}")
    if "hennanst-20" in text:
        raise SystemExit(f"RG6 validation failed: obsolete affiliate tag in {rel}")

print("RG6_PREMIUM_VISUAL_VALIDATOR_PASS: no dist mutation performed")
