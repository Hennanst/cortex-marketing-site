#!/usr/bin/env python3
"""Apply the Córtex G-IMG-01 premium visual layer to the built Cloudflare bundle.

This pass replaces the previous vector-placeholder visual language with rights-safe
editorial photography for primary consumer-facing surfaces. The hero/category candidates
below are source-verified under the Unsplash License and are staged for rendered crop and
qualitative review; source verification alone does not equal G-IMG-01 PASS.

Named-product cards remain explicitly CONTEXT_ONLY until exact rights-safe product imagery
passes G-IMG-01P. They must not be promoted to premium product-visual PASS merely because
the contextual photography is attractive.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DIST = Path(sys.argv[1] if len(sys.argv) > 1 else "dist").resolve()
if not DIST.exists():
    raise SystemExit(f"publish directory not found: {DIST}")

PHOTOS = {
    # Source-verified hero/category candidates. Final PASS requires rendered review.
    "hero-tech-v1.svg": "https://images.unsplash.com/photo-1762096070873-63e82ab143ca?auto=format&fit=crop&w=1800&q=86",
    "category-gaming-v1.svg": "https://images.unsplash.com/photo-1779452525134-bb7c08326179?auto=format&fit=crop&w=1500&q=86",
    "category-work-v1.svg": "https://images.unsplash.com/photo-1781106743595-1a2c6397e812?auto=format&fit=crop&w=1500&q=86",
    "category-creator-v1.svg": "https://images.unsplash.com/photo-1764664035187-e89b27d54c7b?auto=format&fit=crop&w=1500&q=86",
    "category-home-v1.svg": "https://images.unsplash.com/photo-1772475329864-e30a2f1278c0?auto=format&fit=crop&w=1500&q=86",
    # Named-product visuals remain CONTEXT_ONLY until an exact rights-safe source passes
    # the frozen G-IMG-01P Product Recognition subgate.
    "product-g305-editorial-v1.svg": "https://images.unsplash.com/photo-1691580438246-a6e5cb35ca05?auto=format&fit=crop&w=1400&q=86",
    "product-g203-editorial-v1.svg": "https://images.unsplash.com/photo-1693880269247-97721478c508?auto=format&fit=crop&w=1400&q=86",
    "product-ideapad-editorial-v1.svg": "https://images.unsplash.com/photo-1781106743595-1a2c6397e812?auto=format&fit=crop&w=1400&q=86",
}

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
<style id="cortex-premium-photo-pass-v1">
img[src*="images.unsplash.com"]{background:#0d1218;object-fit:cover;image-rendering:auto}
.visual-context-label{display:block;margin:8px 14px 0;color:#8f99a6;font-size:.69rem;line-height:1.35;letter-spacing:.01em}
.hero img[src*="images.unsplash.com"],.g8-hero img[src*="images.unsplash.com"]{min-height:320px;max-height:560px;object-fit:cover}
.hero img[src*="photo-1762096070873-63e82ab143ca"]{object-position:center 38%}
.g8-tile img[src*="images.unsplash.com"],.product img[src*="images.unsplash.com"]{object-fit:cover}
.product-visual{background:center/cover no-repeat!important;border:1px solid rgba(255,255,255,.08)!important;overflow:hidden!important;position:relative!important}
.product-visual:after,.product-visual>span,.product-visual>b{display:none!important}
.product-visual:before{content:"Imagem editorial de contexto";position:absolute;left:14px;bottom:12px;z-index:2;padding:5px 8px;border-radius:999px;background:rgba(6,9,13,.78);color:#d7dee7;font-size:.66rem;font-weight:750;letter-spacing:.03em;backdrop-filter:blur(8px)}
@media(max-width:760px){.hero img[src*="images.unsplash.com"],.g8-hero img[src*="images.unsplash.com"]{min-height:240px;max-height:380px}.visual-context-label{margin:7px 10px 0}.hero img[src*="photo-1762096070873-63e82ab143ca"]{object-position:center 34%}}
</style>
""".strip()

ALT_REPLACEMENTS = {
    "Ilustração editorial Córtex de setup gamer": "Fotografia editorial de contexto para Setup & Games",
    "Ilustração editorial do Logitech G305": "Imagem editorial de contexto para mouse sem fio; confirme o SKU exato no varejista",
    "Ilustração editorial do Logitech G203": "Imagem editorial de contexto para mouse com fio; confirme o SKU exato no varejista",
    "Logitech G305 em linguagem editorial Córtex": "Imagem editorial de contexto para mouse sem fio; não é foto do SKU exato",
    "Logitech G203 em linguagem editorial Córtex": "Imagem editorial de contexto para mouse com fio; não é foto do SKU exato",
    "Ilustração editorial do Lenovo IdeaPad 1": "Imagem editorial de contexto para notebook; confirme o SKU exato no varejista",
    "Seleção editorial Córtex para trabalho e estudo": "Fotografia editorial de contexto para trabalho e estudo",
    "Comparativos de tecnologia e setup": "Fotografia editorial de contexto para comparativos de tecnologia",
    "Curadoria de tecnologia Córtex Ofertas": "Fotografia editorial de contexto para curadoria de tecnologia",
    "Recomendações de setup e games": "Fotografia editorial de contexto para Setup & Games",
    "Recomendações de trabalho e estudo": "Fotografia editorial de contexto para trabalho e estudo",
}


def replace_asset_refs(text: str) -> str:
    for filename, url in PHOTOS.items():
        pattern = re.compile(rf"(?:\.\./|\./|/)?assets/cortex/{re.escape(filename)}")
        text = pattern.sub(url, text)
    for old, new in ALT_REPLACEMENTS.items():
        text = text.replace(old, new)
    return text


def force_primary_images_eager(text: str) -> str:
    """Primary G-IMG-01 visuals must render immediately on the audited routes."""
    text = re.sub(
        r'(<img\b(?=[^>]*images\.unsplash\.com)[^>]*?)\sloading=("|\')lazy\2',
        r'\1 loading="eager"',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'(<img\b(?=[^>]*images\.unsplash\.com)(?![^>]*\sloading=)[^>]*)(>)',
        r'\1 loading="eager"\2',
        text,
        flags=re.IGNORECASE,
    )
    return text


def add_context_label_after_image(text: str, photo_url: str) -> str:
    pattern = re.compile(rf'(<img\b[^>]*src="{re.escape(photo_url)}"[^>]*>)(?!\s*<span class="visual-context-label")')
    return pattern.sub(
        r'\1<span class="visual-context-label">Imagem editorial de contexto · confirme o produto exato no varejista.</span>',
        text,
    )


changed = []
for rel in PRIMARY_ROUTES:
    path = DIST / rel
    if not path.exists():
        raise SystemExit(f"primary route missing after build: {rel}")
    text = path.read_text(encoding="utf-8")
    original = text
    text = replace_asset_refs(text)
    text = force_primary_images_eager(text)

    if STYLE not in text:
        text = text.replace("</head>", STYLE + "</head>", 1)

    if rel in {"setup-games/index.html", "comparativos/index.html", "recomendados/index.html"}:
        text = add_context_label_after_image(text, PHOTOS["product-g305-editorial-v1.svg"])
        text = add_context_label_after_image(text, PHOTOS["product-g203-editorial-v1.svg"])

    if rel == "trabalho-estudo/index.html":
        text = add_context_label_after_image(text, PHOTOS["product-ideapad-editorial-v1.svg"])
        text = text.replace(
            "background:linear-gradient(160deg,#1a2330,#0d1118);",
            f"background-image:url('{PHOTOS['product-ideapad-editorial-v1.svg']}');background-position:center;background-size:cover;",
        )

    text = text.replace("G305 · liberdade sem fio e autonomia.", "Imagem de contexto · G305: liberdade sem fio e autonomia.")
    text = text.replace("G203 · simplicidade com fio e menor peso.", "Imagem de contexto · G203: simplicidade com fio e menor peso.")
    text = text.replace("Notebook já presente na curadoria ativa, com contexto de uso e trade-off explícito.", "Imagem de contexto · notebook da curadoria ativa com uso e trade-off explícitos.")

    if text != original:
        path.write_text(text, encoding="utf-8")
        changed.append(rel)

old_names = tuple(PHOTOS)
for rel in PRIMARY_ROUTES:
    text = (DIST / rel).read_text(encoding="utf-8")
    leftovers = [name for name in old_names if name in text]
    if leftovers:
        raise SystemExit(f"G-IMG-01 precheck failed at {rel}: old primary visual refs remain: {leftovers}")
    if "./https://images.unsplash.com" in text or "../https://images.unsplash.com" in text:
        raise SystemExit(f"G-IMG-01 precheck failed at {rel}: malformed external image URL")

print("Premium visual pass applied to:")
for rel in changed:
    print(f" - {rel}")
