#!/usr/bin/env python3
"""Fetch exact-ASIN catalog imagery from Amazon Creators API for Córtex Ofertas.

This script is intentionally fail-closed and does not contain credentials. It is designed
for the Córtex visual pipeline after G-IMG-01P established that generic contextual photos
cannot count as premium product imagery for named product cards.

Environment variables:
  AMAZON_CREATORS_CLIENT_ID       required
  AMAZON_CREATORS_CLIENT_SECRET   required
  AMAZON_CREATORS_VERSION         optional, default: 3.1
  AMAZON_PARTNER_TAG              optional, default: cortexofertas-20
  AMAZON_MARKETPLACE              optional, default: www.amazon.com.br

Example:
  python3 scripts/amazon_creators_catalog.py \
    B07GPRWFC5 B087CT8PWY --output /tmp/cortex-amazon-catalog.json

The output contains only catalog fields needed by the visual gate: ASIN, title,
Amazon detail URL and image URL/dimensions. No credentials or access token are written.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

CREATORS_BASE = "https://creatorsapi.amazon/catalog/v1"
TOKEN_ENDPOINTS = {
    "3.1": "https://api.amazon.com/auth/o2/token",      # NA: US/CA/MX/BR
    "3.2": "https://api.amazon.co.uk/auth/o2/token",   # EU
    "3.3": "https://api.amazon.co.jp/auth/o2/token",   # FE
}
DEFAULT_MARKETPLACE = "www.amazon.com.br"
DEFAULT_PARTNER_TAG = "cortexofertas-20"
RESOURCES = [
    "images.primary.large",
    "images.variants.large",
    "itemInfo.title",
]


class CreatorsAPIError(RuntimeError):
    pass


@dataclass
class Token:
    value: str
    expires_at: float


class AmazonCreatorsCatalog:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        version: str = "3.1",
        marketplace: str = DEFAULT_MARKETPLACE,
        partner_tag: str = DEFAULT_PARTNER_TAG,
        timeout: int = 25,
    ) -> None:
        if not client_id or not client_secret:
            raise CreatorsAPIError("Creators API credentials are not configured")
        if version not in TOKEN_ENDPOINTS:
            raise CreatorsAPIError(f"Unsupported Creators API credential version: {version}")
        if partner_tag != DEFAULT_PARTNER_TAG:
            raise CreatorsAPIError(
                f"Route check failed: partner tag must be {DEFAULT_PARTNER_TAG}, got {partner_tag!r}"
            )
        if marketplace != DEFAULT_MARKETPLACE:
            raise CreatorsAPIError(
                f"Route check failed: Córtex marketplace must be {DEFAULT_MARKETPLACE}, got {marketplace!r}"
            )

        self.client_id = client_id
        self.client_secret = client_secret
        self.version = version
        self.marketplace = marketplace
        self.partner_tag = partner_tag
        self.timeout = timeout
        self._token: Token | None = None

    def _json_request(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        req = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            raise CreatorsAPIError(f"Amazon API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise CreatorsAPIError(f"Amazon API network error: {exc.reason}") from exc

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CreatorsAPIError("Amazon API returned non-JSON content") from exc
        if not isinstance(result, dict):
            raise CreatorsAPIError("Amazon API returned unexpected response shape")
        return result

    def _access_token(self) -> str:
        now = time.time()
        if self._token and self._token.expires_at - now > 60:
            return self._token.value

        result = self._json_request(
            TOKEN_ENDPOINTS[self.version],
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "creatorsapi::default",
            },
        )
        value = result.get("access_token")
        expires_in = result.get("expires_in", 3600)
        if not isinstance(value, str) or not value:
            raise CreatorsAPIError("Creators API token response did not contain access_token")
        try:
            ttl = int(expires_in)
        except (TypeError, ValueError):
            ttl = 3600
        self._token = Token(value=value, expires_at=now + max(60, ttl))
        return value

    def get_items(self, asins: list[str]) -> list[dict[str, Any]]:
        cleaned: list[str] = []
        for asin in asins:
            normalized = asin.strip().upper()
            if not normalized:
                continue
            if not normalized.isalnum() or len(normalized) != 10:
                raise CreatorsAPIError(f"Invalid ASIN format: {asin!r}")
            if normalized not in cleaned:
                cleaned.append(normalized)
        if not cleaned:
            raise CreatorsAPIError("No ASINs supplied")
        if len(cleaned) > 10:
            raise CreatorsAPIError("Creators API GetItems supports at most 10 itemIds per request")

        result = self._json_request(
            f"{CREATORS_BASE}/getItems",
            {
                "itemIds": cleaned,
                "itemIdType": "ASIN",
                "marketplace": self.marketplace,
                "partnerTag": self.partner_tag,
                "resources": RESOURCES,
            },
            {
                "Authorization": f"Bearer {self._access_token()}",
                "x-marketplace": self.marketplace,
            },
        )

        container = result.get("itemsResult") or result.get("items_result") or result
        items = container.get("items") if isinstance(container, dict) else None
        if not isinstance(items, list):
            errors = result.get("errors")
            raise CreatorsAPIError(f"GetItems response did not contain items: {errors or 'unknown response'}")

        formatted: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            asin = str(item.get("asin") or "").upper()
            if asin not in cleaned:
                continue
            title = (((item.get("itemInfo") or {}).get("title") or {}).get("displayValue"))
            images = item.get("images") or {}
            primary = ((images.get("primary") or {}).get("large") or {})
            variants_raw = images.get("variants") or []
            variants = []
            if isinstance(variants_raw, list):
                for variant in variants_raw:
                    large = ((variant or {}).get("large") or {}) if isinstance(variant, dict) else {}
                    url = large.get("url")
                    if isinstance(url, str) and url.startswith("https://"):
                        variants.append(
                            {
                                "url": url,
                                "width": large.get("width"),
                                "height": large.get("height"),
                            }
                        )
            primary_url = primary.get("url")
            if not isinstance(primary_url, str) or not primary_url.startswith("https://"):
                primary_url = None
            formatted.append(
                {
                    "asin": asin,
                    "title": title,
                    "detail_page_url": item.get("detailPageURL") or item.get("detailPageUrl"),
                    "primary_image": {
                        "url": primary_url,
                        "width": primary.get("width"),
                        "height": primary.get("height"),
                    },
                    "variant_images": variants,
                    "source": "amazon_creators_api",
                    "marketplace": self.marketplace,
                    "partner_tag": self.partner_tag,
                }
            )

        found = {item["asin"] for item in formatted}
        missing = [asin for asin in cleaned if asin not in found]
        if missing:
            raise CreatorsAPIError(f"GetItems did not return expected ASIN(s): {', '.join(missing)}")
        return formatted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch exact product images through Amazon Creators API")
    parser.add_argument("asins", nargs="+", help="One to ten ASINs")
    parser.add_argument("--output", help="Write JSON manifest to this path instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        client = AmazonCreatorsCatalog(
            client_id=os.getenv("AMAZON_CREATORS_CLIENT_ID", "").strip(),
            client_secret=os.getenv("AMAZON_CREATORS_CLIENT_SECRET", "").strip(),
            version=os.getenv("AMAZON_CREATORS_VERSION", "3.1").strip() or "3.1",
            marketplace=os.getenv("AMAZON_MARKETPLACE", DEFAULT_MARKETPLACE).strip() or DEFAULT_MARKETPLACE,
            partner_tag=os.getenv("AMAZON_PARTNER_TAG", DEFAULT_PARTNER_TAG).strip() or DEFAULT_PARTNER_TAG,
        )
        data = {
            "schema": "cortex.amazon-creators-catalog.v1",
            "items": client.get_items(args.asins),
        }
    except CreatorsAPIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
