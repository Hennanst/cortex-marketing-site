#!/usr/bin/env python3
"""Fail-closed source, publication-surface and bundle guard for Córtex."""
from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import hashlib
from html.parser import HTMLParser
import json
import posixpath
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from public_bundle import public_files, publication_html

CANONICAL = "https://cortex-ofertas.pages.dev"
LEGACY = "cortex-public.vercel.app"
OBSOLETE_TAG = "hennanst-20"
QUARANTINE_MANIFEST = "data/quarantine-manifest.json"
SOURCE_EXCLUDED_DIRS = {".git", "dist", "node_modules", "__pycache__"}

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
    "Opções comerciais em validação",
    "Os links permanecem desativados nesta prévia",
)

PUBLIC_HIGH_RISK_PATTERNS = (
    re.compile(r'"(?:price|priceCurrency|priceValidUntil|availability|aggregateRating|reviewRating)"\s*:', re.I),
    re.compile(r'class=["\'][^"\']*(?:review-price|rating-stars|stock-status)[^"\']*["\']', re.I),
    re.compile(r"\b(?:Preço verificado em|Frete grátis com Prime|reviews técnicos gerados|em testes práticos)\b", re.I),
    re.compile(r"\bSetup Cortex\b", re.I),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_source_html(root: Path):
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root)
        if any(part.startswith(".") or part in SOURCE_EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"SOURCE_HTML_SYMLINK: {rel.as_posix()}")
        yield path, rel.as_posix()


def production_html(root: Path):
    for rel in publication_html(root):
        yield root / rel, rel


def _load_quarantine(root: Path) -> dict:
    path = root / QUARANTINE_MANIFEST
    if not path.is_file():
        raise ValueError(f"QUARANTINE_MANIFEST_MISSING: {QUARANTINE_MANIFEST}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"QUARANTINE_MANIFEST_INVALID: {exc}") from exc
    if data.get("version") != 1 or not data.get("reason"):
        raise ValueError("QUARANTINE_MANIFEST_METADATA_INVALID")
    for field in ("files", "patterns", "exceptions"):
        values = data.get(field)
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError(f"QUARANTINE_MANIFEST_FIELD_INVALID: {field}")
        if values != sorted(set(values)):
            raise ValueError(f"QUARANTINE_MANIFEST_FIELD_NOT_SORTED_UNIQUE: {field}")
    if not isinstance(data.get("expected_html_count"), int):
        raise ValueError("QUARANTINE_MANIFEST_COUNT_INVALID")
    return data


def classify_html(root: Path) -> tuple[set[str], set[str], set[str], list[str]]:
    failures: list[str] = []
    try:
        discovered = {rel for _, rel in all_source_html(root)}
        public = set(publication_html(root))
        quarantine = _load_quarantine(root)
    except ValueError as exc:
        return set(), set(), set(), [str(exc)]

    declared_files = set(quarantine["files"])
    exceptions = set(quarantine["exceptions"])
    quarantined = {
        rel for rel in discovered
        if rel not in exceptions and (rel in declared_files or any(fnmatchcase(rel, pattern) for pattern in quarantine["patterns"]))
    }
    for rel in sorted(public - discovered):
        failures.append(f"PUBLIC_HTML_MISSING: {rel}")
    for rel in sorted(declared_files - discovered):
        failures.append(f"DECLARED_QUARANTINE_HTML_MISSING: {rel}")
    for rel in sorted(public & quarantined):
        failures.append(f"PUBLIC_QUARANTINE_OVERLAP: {rel}")
    for rel in sorted(discovered - public - quarantined):
        failures.append(f"UNCLASSIFIED_SOURCE_HTML: {rel}")
    if len(quarantined) != quarantine["expected_html_count"]:
        failures.append(f"QUARANTINE_COUNT_MISMATCH[{len(quarantined)}!={quarantine['expected_html_count']}]")
    return discovered, public, quarantined, failures


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.links = []
        self.wrong_product_fallbacks = 0
        self.malformed_images = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "img" and any(value is None and key not in {"hidden", "ismap", "inert", "itemscope"} for key, value in attrs):
            self.malformed_images += 1
        values = dict(attrs)
        if tag == "img" and "m.media-amazon.com" in values.get("src", "") and "unsplash.com" in values.get("onerror", ""):
            self.wrong_product_fallbacks += 1
        if tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonicals.append(values.get("href", ""))
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])


def canonical_failures(text, rel):
    urls = Page(text).canonicals
    if len(urls) != 1:
        return [f"CANONICAL_COUNT[{len(urls)}]: {rel}"]
    url = urlparse(urls[0])
    expected = "/" + rel
    if expected.endswith("index.html"):
        expected = expected[:-len("index.html")]
    if url.scheme != "https" or url.netloc != "cortex-ofertas.pages.dev" or url.query or url.fragment:
        return [f"SPLIT_CANONICAL[{urls[0]}]: {rel}"]
    if url.path not in {expected, "/" + rel}:
        return [f"CANONICAL_WRONG_ROUTE[{urls[0]}]: {rel}"]
    return []


def _internal_html_target(current_rel: str, href: str) -> str | None:
    url = urlparse(href.strip())
    if url.scheme and url.scheme not in {"http", "https"}:
        return None
    if url.netloc and url.netloc != "cortex-ofertas.pages.dev":
        return None
    if not url.path:
        return None
    raw = unquote(url.path)
    if raw.startswith("/"):
        target = posixpath.normpath(raw.lstrip("/"))
    else:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(current_rel), raw))
    if target in {"", "."}:
        return "index.html"
    if target == ".." or target.startswith("../"):
        return "__ESCAPES_ROOT__"
    if raw.endswith("/") or not Path(target).suffix:
        target = posixpath.join(target, "index.html")
    if not target.endswith(".html"):
        return None
    return target


def _route_for_rel(rel: str) -> str:
    route = "/" + rel
    return route[:-len("index.html")] if route.endswith("index.html") else route


def _sitemap_failures(root: Path, public: set[str]) -> list[str]:
    path = root / "sitemap.xml"
    if not path.is_file():
        return ["SITEMAP_MISSING"]
    text = path.read_text(encoding="utf-8")
    actual = set(re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.I))
    expected = {CANONICAL + _route_for_rel(rel) for rel in public}
    failures = [f"SITEMAP_MISSING_PUBLIC_ROUTE: {url}" for url in sorted(expected - actual)]
    failures.extend(f"SITEMAP_UNPUBLISHED_ROUTE: {url}" for url in sorted(actual - expected))
    return failures


def scan_source(root: Path) -> list[str]:
    failures: list[str] = []
    discovered, public, quarantined, classification_failures = classify_html(root)
    failures.extend(classification_failures)
    if not discovered:
        return failures

    for rel in PRIMARY_ROUTES:
        if rel not in public:
            failures.append(f"PRIMARY_ROUTE_NOT_PUBLIC: {rel}")

    for path, rel in all_source_html(root):
        text = path.read_text(encoding="utf-8")
        if LEGACY in text:
            failures.append(f"LEGACY_ORIGIN_IN_SOURCE: {rel}")
        if OBSOLETE_TAG in text:
            failures.append(f"OBSOLETE_AFFILIATE_TAG_IN_SOURCE: {rel}")
        for marker in FORBIDDEN_SOURCE_MARKERS:
            if marker in text:
                failures.append(f"FORBIDDEN_PRODUCTION_MARKER[{marker}]: {rel}")
        page = Page(text)
        if page.wrong_product_fallbacks:
            failures.append(f"WRONG_PRODUCT_IMAGE_FALLBACK: {rel}")
        if page.malformed_images:
            failures.append(f"MALFORMED_IMAGE_ATTRIBUTES: {rel}")

        if rel not in public:
            continue
        failures.extend(canonical_failures(text, rel))
        for pattern in PUBLIC_HIGH_RISK_PATTERNS:
            if pattern.search(text):
                failures.append(f"UNVERIFIED_COMMERCIAL_CLAIM_ON_PUBLIC_ROUTE[{pattern.pattern}]: {rel}")
        for href in page.links:
            target = _internal_html_target(rel, href)
            if target and target not in public:
                kind = "QUARANTINED" if target in quarantined else "UNPUBLISHED"
                failures.append(f"PUBLIC_LINK_TO_{kind}_HTML[{target}]: {rel}")

    try:
        for path, rel in public_files(root):
            if path.suffix in {".json", ".js", ".css", ".xml", ".txt", ".svg"}:
                text = path.read_text(encoding="utf-8")
                if LEGACY in text or "hennanst.github.io/cortex-marketing-site" in text:
                    failures.append(f"LEGACY_ORIGIN_IN_SOURCE: {rel}")
                if OBSOLETE_TAG in text:
                    failures.append(f"OBSOLETE_AFFILIATE_TAG_IN_SOURCE: {rel}")
    except ValueError as exc:
        failures.append(str(exc))

    failures.extend(_sitemap_failures(root, public))
    return failures


def compare_dist(root: Path, dist: Path) -> list[str]:
    failures: list[str] = []
    if not dist.exists():
        return [f"DIST_MISSING: {dist}"]
    try:
        expected = dict((rel, src) for src, rel in public_files(root))
    except ValueError as exc:
        return [str(exc)]
    actual = {p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file()}
    for rel in sorted(actual - expected.keys()):
        failures.append(f"UNEXPECTED_DIST_FILE: {rel}")
    for rel, src in expected.items():
        out = dist / rel
        if out.is_symlink() or not out.is_file():
            failures.append(f"SOURCE_OR_DIST_ROUTE_MISSING: {rel}")
            continue
        if sha256(src) != sha256(out):
            failures.append(f"SOURCE_DEPLOY_DIVERGENCE: {rel}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--dist", default="dist")
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--compare-dist", action="store_true")
    parser.add_argument("--report", help="Write machine-readable diagnostics, including coverage")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures: list[str] = []
    if args.source_only or not args.compare_dist:
        failures.extend(scan_source(root))
    if args.compare_dist:
        failures.extend(compare_dist(root, (root / args.dist).resolve()))

    discovered, public, quarantined, classification_failures = classify_html(root)
    failures.extend(classification_failures)
    failures = sorted(set(failures))
    print(f"AUDITED_HTML_FILES={len(discovered)}")
    print(f"PUBLIC_HTML_FILES={len(public)}")
    print(f"QUARANTINED_HTML_FILES={len(quarantined)}")
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({
            "status": "FAIL" if failures else "PASS",
            "html_files": len(discovered),
            "public_html_files": len(public),
            "quarantined_html_files": len(quarantined),
            "unclassified_html_files": len(discovered - public - quarantined),
            "checks": {"source": args.source_only or not args.compare_dist, "bundle_parity": args.compare_dist},
            "failures": failures,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if failures:
        print("CORTEX_SOURCE_TRUTH_GUARD_FAIL")
        for item in failures:
            print(f" - {item}")
        return 1
    print("CORTEX_SOURCE_TRUTH_GUARD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
