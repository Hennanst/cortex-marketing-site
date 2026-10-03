#!/usr/bin/env python3
"""Canonical Amazon affiliate-link helper for Córtex Ofertas.

One deterministic method is used for every surface (Pins, site CTAs and product-image
links): exact ASIN -> Amazon Brasil /dp/ASIN + tracking tag cortexofertas-20.

This module does not query Amazon, infer product identity, price, stock or seller.
It only builds and validates the affiliate destination after the ASIN has passed the
Product/Destination gates.
"""

from __future__ import annotations

import argparse
import re
from urllib.parse import parse_qs, urlparse

EXPECTED_HOST = "www.amazon.com.br"
EXPECTED_TAG = "cortexofertas-20"
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


class AffiliateLinkError(ValueError):
    pass


def normalize_asin(value: object) -> str:
    asin = str(value or "").strip().upper()
    if not ASIN_RE.fullmatch(asin):
        raise AffiliateLinkError(f"invalid ASIN: {value!r}")
    return asin


def canonical_affiliate_url(asin: object) -> str:
    exact = normalize_asin(asin)
    return f"https://{EXPECTED_HOST}/dp/{exact}?tag={EXPECTED_TAG}"


def validate_affiliate_url(url: object, asin: object | None = None) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != EXPECTED_HOST:
        raise AffiliateLinkError(f"destination must be https://{EXPECTED_HOST}/...")
    query_tag = parse_qs(parsed.query).get("tag", [None])[0]
    if query_tag != EXPECTED_TAG:
        raise AffiliateLinkError(f"destination tag must be {EXPECTED_TAG}")
    if asin is not None:
        exact = normalize_asin(asin)
        if f"/dp/{exact}" not in parsed.path:
            raise AffiliateLinkError(f"destination path does not contain /dp/{exact}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the canonical Córtex Amazon Brasil affiliate URL for an exact ASIN"
    )
    parser.add_argument("--asin", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(canonical_affiliate_url(args.asin))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
