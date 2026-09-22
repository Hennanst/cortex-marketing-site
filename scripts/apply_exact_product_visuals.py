#!/usr/bin/env python3
"""Install rights-safe exact-product imagery into the built Córtex site.

This is the website equivalent of the canonical affiliate destination already used for
Córtex Pins. For every validated exact-product manifest entry it:

1. uses the SAME canonical Amazon BR destination (/dp/ASIN?tag=cortexofertas-20);
2. replaces contextual/model imagery only inside a named-product surface;
3. makes the exact product image itself a disclosed Special Link to that product;
4. preserves Amazon Program Content proportions (no crop / no object-fit: cover);
5. never scrapes Amazon and never guesses an image URL.

The script runs only from validated `cortex.product-visuals.v1` manifests. If no matching
named-product surface is found it fails closed instead of silently publishing.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from amazon_affiliate import canonical_affiliate_url, validate_affiliate_url
from validate_product_visual_manifest import collect_category_urls, load_json, validate_manifest

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

STYLE = r"""
<style id="cortex-exact-product-affiliate-v1">
.exact-product-image-link{display:block;text-decoration:none;background:#fff;border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.10)}
.exact-product-image{display:block!important;width:100%!important;height:auto!important;max-height:520px!important;aspect-ratio:auto!important;object-fit:contain!important;object-position:center!important;background:#fff!important;image-rendering:auto!important}
.exact-product-image-disclosure{display:block;margin:7px 2px 12px;color:#7f8995;font-size:.7rem;line-height:1.35}
.product .exact-product-image-link,.product-card .exact-product-image-link{margin:0 0 8px}
.g8-tile.exact-product-tile{display:block}
.g8-tile.exact-product-tile .exact-product-image{max-height:360px!important}
@media(max-width:760px){.exact-product-image{max-height:420px!important}.g8-tile.exact-product-tile .exact-product-image{max-height:320px!important}}
</style>
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply validated exact-product image links")
    parser.add_argument("dist", help="Built Cloudflare publish directory")
    parser.add_argument("manifest", nargs="+", help="Validated product visual manifest JSON")
    parser.add_argument(
        "--category-assets",
        help="Optional category/hero asset JSON used by G-IMG-01P anti-reuse validation",
    )
    return parser.parse_args()


def load_products(paths: list[str], category_assets: str | None) -> list[dict]:
    category_urls = collect_category_urls(category_assets)
    products: list[dict] = []
    seen: set[str] = set()
    for path in paths:
        result = validate_manifest(load_json(path), category_urls)
        for item in result["products"]:
            if item["asin"] in seen:
                raise SystemExit(f"duplicate ASIN across manifests: {item['asin']}")
            seen.add(item["asin"])
            expected = canonical_affiliate_url(item["asin"])
            actual = validate_affiliate_url(item["destination_url"], item["asin"])
            if actual != expected:
                raise SystemExit(f"non-canonical affiliate destination for {item['asin']}")
            products.append(item)
    return products


def image_markup(item: dict) -> str:
    destination = html.escape(item["destination_url"], quote=True)
    image_url = html.escape(item["image_url"], quote=True)
    product_name = html.escape(item["product_name"], quote=True)
    return (
        f'<a class="exact-product-image-link" href="{destination}" rel="sponsored nofollow" '
        f'aria-label="Ver {product_name} na Amazon">'
        f'<img class="exact-product-image" src="{image_url}" alt="{product_name}" '
        f'width="{int(item["width"])}" height="{int(item["height"])}" loading="eager">'
        "</a>"
        '<small class="exact-product-image-disclosure">Publicidade · imagem com link de afiliado para a Amazon</small>'
    )


def replace_named_product_article(text: str, item: dict) -> tuple[str, int]:
    """Replace the primary visual in product/product-card articles that link to this ASIN."""
    asin = re.escape(item["asin"])
    destination = html.escape(item["destination_url"], quote=True)
    markup = image_markup(item)
    count = 0

    article_re = re.compile(
        rf'(<article\b[^>]*class="[^"]*(?:product|product-card)[^"]*"[^>]*>)(.*?/dp/{asin}.*?)(</article>)',
        flags=re.IGNORECASE | re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        start, body, end = match.groups()

        # Canonicalize any Amazon destination inside the named-product surface.
        body = re.sub(
            rf'href="https://www\.amazon\.com\.br/dp/{asin}\?[^\"]*"',
            f'href="{destination}"',
            body,
            flags=re.IGNORECASE,
        )

        # Prefer an existing img; otherwise replace the synthetic product-visual block.
        img_re = re.compile(r'<img\b[^>]*>', flags=re.IGNORECASE)
        if img_re.search(body):
            body = img_re.sub(markup, body, count=1)
        else:
            visual_re = re.compile(
                r'<div\b[^>]*class="[^"]*product-visual[^"]*"[^>]*>.*?</div>',
                flags=re.IGNORECASE | re.DOTALL,
            )
            if visual_re.search(body):
                body = visual_re.sub(markup, body, count=1)
            else:
                # Insert immediately before the first heading when a legacy card has no visual.
                body = re.sub(r'(<h3\b)', markup + r'\1', body, count=1, flags=re.IGNORECASE)

        # Remove context-only labels that are no longer true once the exact image is installed.
        body = re.sub(
            r'<span class="visual-context-label">.*?</span>', "", body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        body = body.replace("Imagem de contexto · ", "")
        count += 1
        return start + body + end

    return article_re.sub(repl, text), count


def model_token(product_name: str) -> str | None:
    # Prefer compact model identifiers such as G305/G203. Avoid generic numeric tokens.
    candidates = re.findall(r'\b[A-Za-z]{1,12}[A-Za-z0-9-]*\d[A-Za-z0-9-]*\b', product_name)
    if not candidates:
        return None
    return max(candidates, key=len)


def replace_named_g8_tile(text: str, item: dict) -> tuple[str, int]:
    """Upgrade comparison/recommendation tiles that visibly name a compact model token."""
    token = model_token(item["product_name"])
    if not token:
        return text, 0
    destination = html.escape(item["destination_url"], quote=True)
    markup = image_markup(item)
    count = 0

    tile_re = re.compile(
        rf'<a\b([^>]*class="[^"]*g8-tile[^"]*"[^>]*)>(?P<body>.*?{re.escape(token)}.*?</a>)',
        flags=re.IGNORECASE | re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        attrs = match.group(1)
        body = match.group("body")
        if "/dp/" in body:
            return match.group(0)
        body = re.sub(r'<img\b[^>]*>', markup, body, count=1, flags=re.IGNORECASE)
        body = re.sub(
            r'<span class="visual-context-label">.*?</span>', "", body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        body = body.replace("Imagem de contexto · ", "")
        attrs = re.sub(r'\shref="[^"]*"', "", attrs, count=1, flags=re.IGNORECASE)
        attrs = re.sub(r'\srel="[^"]*"', "", attrs, count=1, flags=re.IGNORECASE)
        attrs = re.sub(r'\sclass="([^"]*)"', lambda m: f' class="{m.group(1)} exact-product-tile"', attrs, count=1)
        count += 1
        return f'<a{attrs} href="{destination}" rel="sponsored nofollow">{body}'

    return tile_re.sub(repl, text), count


def main() -> int:
    args = parse_args()
    dist = Path(args.dist).resolve()
    if not dist.exists():
        raise SystemExit(f"publish directory not found: {dist}")

    products = load_products(args.manifest, args.category_assets)
    total_matches = {item["asin"]: 0 for item in products}

    for rel in PRIMARY_ROUTES:
        path = dist / rel
        if not path.exists():
            raise SystemExit(f"primary route missing: {rel}")
        text = path.read_text(encoding="utf-8")
        original = text
        if STYLE not in text:
            text = text.replace("</head>", STYLE + "</head>", 1)

        for item in products:
            text, article_count = replace_named_product_article(text, item)
            text, tile_count = replace_named_g8_tile(text, item)
            total_matches[item["asin"]] += article_count + tile_count

        if text != original:
            path.write_text(text, encoding="utf-8")

    for item in products:
        asin = item["asin"]
        if total_matches[asin] == 0:
            raise SystemExit(f"{asin}: exact image manifest passed but no named-product surface matched")

    # Final firewall: every installed exact image must be linked to the exact canonical destination,
    # and no exact-product image may retain the old contextual disclaimer in the same surface.
    for rel in PRIMARY_ROUTES:
        text = (dist / rel).read_text(encoding="utf-8")
        for item in products:
            if item["image_url"] in text and item["destination_url"] not in text:
                raise SystemExit(f"{rel}: exact image for {item['asin']} is not paired with its affiliate destination")

    print("Exact product affiliate-image pass:")
    for item in products:
        print(f" - {item['asin']}: {total_matches[item['asin']]} surface(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
