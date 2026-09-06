#!/usr/bin/env python3
"""Fail-closed recovery guard for Córtex production source truth.

This script intentionally fails while RECOVERY_MODE defects still exist. It is
not an auto-fixer. Production source must contain the buyer-facing truth; dist
must not acquire different buyer-facing HTML during build/deploy.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

CANONICAL = "https://cortex-ofertas.pages.dev"
LEGACY = "cortex-public.vercel.app"
OBSOLETE_TAG = "hennanst-20"

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

FORBIDDEN_SOURCE_MARKERS = (
    'data-bootstrap-image-free="true"',
    "data-bootstrap-",
    'data-merchant-state="blocked"',
    "Card comercial intencionalmente sem imagem de produto",
    "Seleção comercial temporariamente indisponível",
    "Link de produto será ativado após a revalidação final da oferta",
)

FORBIDDEN_BUILD_BEHAVIORS = (
    "apply_premium_visuals.py dist",
    "Apply G-IMG-01 premium visual pass",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def production_html(root: Path):
    for path in root.rglob("*.html"):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in {"dist", ".git"}:
            continue
        yield path, rel.as_posix()


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def scan_source(root: Path) -> list[str]:
    failures: list[str] = []

    for rel in PRIMARY_ROUTES:
        path = root / rel
        if not path.exists():
            fail(f"PRIMARY_ROUTE_MISSING: {rel}", failures)
            continue
        text = path.read_text(encoding="utf-8")
        if f'href="{CANONICAL}' not in text:
            fail(f"PRIMARY_CANONICAL_NOT_CLOUDFLARE: {rel}", failures)

    for path, rel in production_html(root):
        text = path.read_text(encoding="utf-8")
        if LEGACY in text:
            fail(f"LEGACY_ORIGIN_IN_SOURCE: {rel}", failures)
        if OBSOLETE_TAG in text:
            fail(f"OBSOLETE_AFFILIATE_TAG_IN_SOURCE: {rel}", failures)
        for marker in FORBIDDEN_SOURCE_MARKERS:
            if marker in text:
                fail(f"FORBIDDEN_PRODUCTION_MARKER[{marker}]: {rel}", failures)
        canonical_matches = re.findall(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)', text, re.I)
        for url in canonical_matches:
            if not url.startswith(CANONICAL):
                fail(f"SPLIT_CANONICAL[{url}]: {rel}", failures)

    for rel in ("robots.txt", "sitemap.xml"):
        path = root / rel
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if LEGACY in text:
                fail(f"LEGACY_ORIGIN_IN_SOURCE: {rel}", failures)
            if OBSOLETE_TAG in text:
                fail(f"OBSOLETE_AFFILIATE_TAG_IN_SOURCE: {rel}", failures)

    workflow = root / ".github/workflows/cloudflare-pages.yml"
    if workflow.exists():
        text = workflow.read_text(encoding="utf-8")
        for behavior in FORBIDDEN_BUILD_BEHAVIORS:
            if behavior in text:
                fail(f"BUILD_TIME_BUYER_FACING_MUTATION_HOOK[{behavior}]", failures)

    return failures


def compare_dist(root: Path, dist: Path) -> list[str]:
    failures: list[str] = []
    if not dist.exists():
        return [f"DIST_MISSING: {dist}"]

    # Strong recovery invariant: primary buyer-facing HTML must be byte-identical
    # between reviewed source and publish bundle. Infrastructure packaging belongs
    # outside those HTML files.
    for rel in PRIMARY_ROUTES:
        src = root / rel
        out = dist / rel
        if not src.exists() or not out.exists():
            fail(f"SOURCE_OR_DIST_ROUTE_MISSING: {rel}", failures)
            continue
        if sha256(src) != sha256(out):
            fail(f"SOURCE_DEPLOY_DIVERGENCE: {rel}", failures)

    for rel in ("robots.txt", "sitemap.xml"):
        src = root / rel
        out = dist / rel
        if src.exists() and out.exists() and sha256(src) != sha256(out):
            fail(f"SOURCE_DEPLOY_DIVERGENCE: {rel}", failures)

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--dist", default="dist")
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--compare-dist", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures: list[str] = []

    if args.source_only or not args.compare_dist:
        failures.extend(scan_source(root))
    if args.compare_dist:
        failures.extend(compare_dist(root, (root / args.dist).resolve()))

    if failures:
        print("CORTEX_SOURCE_TRUTH_GUARD_FAIL")
        for item in sorted(set(failures)):
            print(f" - {item}")
        return 1

    print("CORTEX_SOURCE_TRUTH_GUARD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
