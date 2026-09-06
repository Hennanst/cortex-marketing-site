#!/usr/bin/env python3
"""One-time recovery materializer.

Takes the already-built legacy `dist/` artifact and commits its reviewed buyer-facing
semantics back into source. This script is recovery-only and must not remain in the
production build path.

It intentionally preserves setup-games/index.html because Setup has already been
restored separately with source-native product/editorial assets.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ARCHIVE = ROOT / "archive" / "legacy-affiliate-pre-recovery-20260906"
PRESERVE = {"setup-games/index.html"}
LEGACY_TAG = "hennanst-20"
LEGACY_ORIGIN = "cortex-public.vercel.app"
CANONICAL_ORIGIN = "cortex-ofertas.pages.dev"


def rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def sanitize_html(text: str, path: str) -> str:
    soup = BeautifulSoup(text, "html.parser")

    # Recovery invariant: bootstrap/temporary production state never survives.
    if soup.body:
        for attr in list(soup.body.attrs):
            if attr.startswith("data-bootstrap"):
                del soup.body.attrs[attr]

    # Remove build-only cleanup CSS; unfinished states are resolved in SOURCE instead.
    cleanup = soup.find("style", id="cortex-g9-blocked-cleanup")
    if cleanup:
        cleanup.decompose()

    # Resolve visible blocked merchant state at source. A blocked product card is
    # removed from the buyer-facing module; it can return only through a new gate.
    blocked_nodes = list(soup.select('[data-merchant-state="blocked"]'))
    for node in blocked_nodes:
        card = node.find_parent(class_="product-card")
        if card is None:
            card = node.find_parent("article")
        (card or node).decompose()

    # Remove commercial modules that now have no release-ready product cards/CTA.
    for module in list(soup.select(".product-module")):
        has_active = module.select_one('[data-merchant-state="active"]') is not None
        has_affiliate = any("amazon.com.br" in (a.get("href") or "") for a in module.find_all("a"))
        has_cards = module.select_one(".product-card") is not None
        if not has_active and not has_affiliate and not has_cards:
            module.decompose()

    # Remove explicit temporary image-free workaround blocks. If present inside a
    # commercial card, remove the card; otherwise remove only the temporary notice.
    for node in list(soup.select(".imagefree")):
        card = node.find_parent(class_="product-card") or node.find_parent(class_="product")
        if card is not None:
            card.decompose()
        else:
            node.decompose()

    out = str(soup)
    temporary_phrases = (
        "Card comercial intencionalmente sem imagem de produto",
        "Seleção comercial temporariamente indisponível",
        "Link de produto será ativado após a revalidação final da oferta",
    )
    for phrase in temporary_phrases:
        out = out.replace(phrase, "")

    if LEGACY_ORIGIN in out:
        raise SystemExit(f"materialized HTML still contains legacy origin: {path}")
    if LEGACY_TAG in out:
        raise SystemExit(f"materialized HTML still contains obsolete affiliate tag: {path}")
    if 'data-merchant-state="blocked"' in out:
        raise SystemExit(f"materialized HTML still contains blocked merchant state: {path}")
    if "data-bootstrap-" in out:
        raise SystemExit(f"materialized HTML still contains bootstrap marker: {path}")
    return out


def archive_obsolete_source() -> list[str]:
    moved: list[str] = []
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.html", "*.json"):
        for path in list(ROOT.rglob(pattern)):
            rp = rel(path, ROOT)
            if rp.startswith(("dist/", "archive/", ".git/")):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if LEGACY_TAG not in text:
                continue
            target = ARCHIVE / rp
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target))
            moved.append(rp)
    return moved


def materialize_dist() -> list[str]:
    if not DIST.exists():
        raise SystemExit("dist/ missing; run legacy recovery build first")
    changed: list[str] = []

    for source in DIST.rglob("*.html"):
        rp = rel(source, DIST)
        if rp in PRESERVE:
            continue
        text = source.read_text(encoding="utf-8")
        text = sanitize_html(text, rp)
        target = ROOT / rp
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        changed.append(rp)

    for rp in ("robots.txt", "sitemap.xml"):
        source = DIST / rp
        if source.exists():
            text = source.read_text(encoding="utf-8")
            if LEGACY_ORIGIN in text or LEGACY_TAG in text:
                raise SystemExit(f"materialized {rp} still stale")
            (ROOT / rp).write_text(text, encoding="utf-8")
            changed.append(rp)

    return changed


def main() -> int:
    moved = archive_obsolete_source()
    changed = materialize_dist()
    print("RECOVERY_SOURCE_MATERIALIZATION_COMPLETE")
    print(f"archived obsolete-tag source files: {len(moved)}")
    for p in moved:
        print(f" archive: {p}")
    print(f"materialized files: {len(changed)}")
    for p in changed:
        print(f" source: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
