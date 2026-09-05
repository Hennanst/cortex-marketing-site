#!/usr/bin/env python3
"""Validate exact-product visual manifests for Córtex G-IMG-01P.

This validator is source-agnostic and fail-closed. It allows exact-product imagery to
enter the premium visual pipeline only when identity, destination, provenance and image
metadata are explicit. It does not fetch images and it never handles credentials.

Schema: cortex.product-visuals.v1

Allowed rights-safe source types:
- amazon_creators_api
- manufacturer_explicit_permission
- owner_supplied_original

A named-product image must not be reused as a generic hero/category image. Supply an
optional category-assets JSON file containing image URLs to enforce this anti-recurrence
constraint before production integration.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCHEMA = "cortex.product-visuals.v1"
ALLOWED_SOURCES = {
    "amazon_creators_api",
    "manufacturer_explicit_permission",
    "owner_supplied_original",
}
EXPECTED_HOST = "www.amazon.com.br"
EXPECTED_TAG = "cortexofertas-20"
MIN_LONG_EDGE = 800
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


class ManifestError(RuntimeError):
    pass


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: top-level JSON must be an object")
    return data


def normalize_asin(value: object) -> str:
    asin = str(value or "").strip().upper()
    if not ASIN_RE.fullmatch(asin):
        raise ManifestError(f"invalid ASIN: {value!r}")
    return asin


def validate_destination(url: object, asin: str) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != EXPECTED_HOST:
        raise ManifestError(f"{asin}: destination must be https://{EXPECTED_HOST}/...")
    if f"/dp/{asin}" not in parsed.path:
        raise ManifestError(f"{asin}: destination path does not contain /dp/{asin}")
    tag = parse_qs(parsed.query).get("tag", [None])[0]
    if tag != EXPECTED_TAG:
        raise ManifestError(f"{asin}: destination tag must be {EXPECTED_TAG}")
    return value


def validate_image(item: dict, asin: str) -> str:
    image_url = str(item.get("image_url") or "").strip()
    parsed = urlparse(image_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ManifestError(f"{asin}: image_url must be an absolute https URL")
    try:
        width = int(item.get("width"))
        height = int(item.get("height"))
    except (TypeError, ValueError):
        raise ManifestError(f"{asin}: width/height must be integers")
    if width <= 0 or height <= 0:
        raise ManifestError(f"{asin}: width/height must be positive")
    if max(width, height) < MIN_LONG_EDGE:
        raise ManifestError(
            f"{asin}: image long edge {max(width, height)}px is below {MIN_LONG_EDGE}px"
        )
    return image_url


def collect_category_urls(path: str | None) -> set[str]:
    if not path:
        return set()
    data = load_json(path)
    urls: set[str] = set()
    for value in data.get("image_urls", []):
        if isinstance(value, str) and value.startswith("https://"):
            urls.add(value)
    for item in data.get("assets", []):
        if isinstance(item, dict):
            value = item.get("image_url") or item.get("url")
            if isinstance(value, str) and value.startswith("https://"):
                urls.add(value)
    return urls


def validate_manifest(data: dict, category_urls: set[str]) -> dict:
    if data.get("schema") != SCHEMA:
        raise ManifestError(f"schema must be {SCHEMA}")
    products = data.get("products")
    if not isinstance(products, list) or not products:
        raise ManifestError("products must be a non-empty array")

    seen_asins: set[str] = set()
    seen_images: set[str] = set()
    normalized: list[dict] = []

    for raw in products:
        if not isinstance(raw, dict):
            raise ManifestError("every products entry must be an object")
        asin = normalize_asin(raw.get("asin"))
        if asin in seen_asins:
            raise ManifestError(f"duplicate ASIN: {asin}")
        seen_asins.add(asin)

        name = str(raw.get("product_name") or "").strip()
        if not name:
            raise ManifestError(f"{asin}: product_name is required")

        source_type = str(raw.get("source_type") or "").strip()
        if source_type not in ALLOWED_SOURCES:
            raise ManifestError(
                f"{asin}: source_type must be one of {sorted(ALLOWED_SOURCES)}"
            )
        rights_basis = str(raw.get("rights_basis") or "").strip()
        source_ref = str(raw.get("source_ref") or "").strip()
        verified_at = str(raw.get("verified_at") or "").strip()
        if not rights_basis or not source_ref or not verified_at:
            raise ManifestError(
                f"{asin}: rights_basis, source_ref and verified_at are required"
            )

        destination = validate_destination(raw.get("destination_url"), asin)
        image_url = validate_image(raw, asin)
        if image_url in seen_images:
            raise ManifestError(f"{asin}: image_url is reused by another named product")
        if image_url in category_urls:
            raise ManifestError(
                f"{asin}: image_url is already used by a generic hero/category asset"
            )
        seen_images.add(image_url)

        normalized.append(
            {
                "asin": asin,
                "product_name": name,
                "source_type": source_type,
                "rights_basis": rights_basis,
                "source_ref": source_ref,
                "verified_at": verified_at,
                "destination_url": destination,
                "image_url": image_url,
                "width": int(raw["width"]),
                "height": int(raw["height"]),
            }
        )

    return {"schema": SCHEMA, "status": "PASS", "products": normalized}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Córtex exact-product visual manifest")
    parser.add_argument("manifest", help="Path to cortex.product-visuals.v1 JSON")
    parser.add_argument(
        "--category-assets",
        help="Optional JSON containing generic hero/category image URLs to forbid reuse",
    )
    parser.add_argument("--output", help="Optional normalized PASS manifest path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate_manifest(
            load_json(args.manifest),
            collect_category_urls(args.category_assets),
        )
    except (ManifestError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
