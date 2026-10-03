#!/usr/bin/env python3
"""Build a Córtex exact-product visual manifest from official Amazon SiteStripe output metadata.

The affiliate destination is generated with the SAME canonical method used by Córtex
for Pin destinations: exact ASIN -> https://www.amazon.com.br/dp/ASIN?tag=cortexofertas-20.

This helper intentionally does NOT scrape Amazon pages and does NOT assume SiteStripe's
current HTML snippet shape. It accepts explicit image metadata copied from the official
Associate SiteStripe Image-link output and emits a `cortex.product-visuals.v1` manifest
that must still pass `validate_product_visual_manifest.py`.

Required inputs:
- exact ASIN
- product name
- Amazon-hosted image URL from SiteStripe's Image link output
- actual image pixel width/height
- provenance/evidence identifier

An optional --destination-url may be supplied as evidence, but it must validate against
the exact ASIN/tag. The emitted destination is always canonicalized by amazon_affiliate.py.
No secrets are accepted or written.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from amazon_affiliate import canonical_affiliate_url, validate_affiliate_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed Córtex SiteStripe exact-product manifest"
    )
    parser.add_argument("--asin", required=True)
    parser.add_argument("--product-name", required=True)
    parser.add_argument(
        "--destination-url",
        help="Optional Amazon BR affiliate destination evidence; must match exact ASIN/tag",
    )
    parser.add_argument("--image-url", required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument(
        "--evidence-id",
        required=True,
        help="Stable provenance label for the official SiteStripe generation event",
    )
    parser.add_argument(
        "--verified-at",
        help="ISO-8601 timestamp; defaults to current UTC time",
    )
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    asin = args.asin.strip().upper()
    product_name = args.product_name.strip()
    evidence_id = args.evidence_id.strip()
    verified_at = (
        args.verified_at.strip()
        if args.verified_at
        else datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

    if not product_name:
        raise SystemExit("product-name must not be empty")
    if not evidence_id:
        raise SystemExit("evidence-id must not be empty")

    destination_url = canonical_affiliate_url(asin)
    if args.destination_url:
        supplied = validate_affiliate_url(args.destination_url.strip(), asin)
        if supplied != destination_url:
            raise SystemExit(
                "destination-url is valid but not canonical; use the exact /dp/ASIN?tag=cortexofertas-20 form"
            )

    manifest = {
        "schema": "cortex.product-visuals.v1",
        "products": [
            {
                "asin": asin,
                "product_name": product_name,
                "source_type": "amazon_sitestripe_image_link",
                "rights_basis": "Amazon Associates SiteStripe - Obter link: Imagem",
                "source_ref": f"sitestripe:{asin}:{evidence_id}",
                "verified_at": verified_at,
                "destination_url": destination_url,
                "image_url": args.image_url.strip(),
                "width": args.width,
                "height": args.height,
            }
        ],
    }

    Path(args.output).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
