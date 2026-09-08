#!/usr/bin/env python3
"""Validate approved source-native editorial photography without mutating HTML."""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[1]
TARGET = Path(sys.argv[1] if len(sys.argv) > 1 else REPO).resolve()
CATALOG = REPO / "data/editorial-visuals.json"
OLD_VISUAL_RE = re.compile(r"(?:hero-tech-v1|category-(?:gaming|work|creator|home)-v1|product-(?:g305|g203|ideapad)-editorial-v1)\.svg")

REQUIRED = {
    "index.html": {"home", "gaming", "work", "creator", "home_automation"},
    "setup-games/index.html": {"gaming"},
    "trabalho-estudo/index.html": {"work", "home", "gaming"},
    "creator-streaming/index.html": {"creator", "home", "work"},
    "casa-inteligente/index.html": {"home_automation", "home", "work"},
    "guias/index.html": {"home", "gaming", "work"},
    "comparativos/index.html": {"home", "gaming", "creator"},
    "recomendados/index.html": {"home", "gaming", "home_automation"},
}


class VisualParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.commercial_depth = 0
        self.stack: list[tuple[str, bool]] = []
        self.images: list[tuple[dict[str, str | None], bool]] = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        enters_commercial = "data-asin" in values
        if tag == "img":
            self.images.append((values, self.commercial_depth > 0 or enters_commercial))
        if tag not in self.VOID_TAGS:
            self.stack.append((tag, enters_commercial))
            if enters_commercial:
                self.commercial_depth += 1

    def handle_startendtag(self, tag, attrs):
        values = dict(attrs)
        if tag == "img":
            self.images.append((values, self.commercial_depth > 0 or "data-asin" in values))

    def handle_endtag(self, tag):
        while self.stack:
            open_tag, entered_commercial = self.stack.pop()
            if entered_commercial:
                self.commercial_depth -= 1
            if open_tag == tag:
                break


if not TARGET.exists():
    raise SystemExit(f"publish directory not found: {TARGET}")

catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
approved = {name: item["url"] for name, item in catalog["photos"].items()}
approved_urls = set(approved.values())
failures: list[str] = []

for rel, required_roles in REQUIRED.items():
    path = TARGET / rel
    if not path.is_file():
        failures.append(f"missing primary route {rel}")
        continue
    text = path.read_text(encoding="utf-8")
    if OLD_VISUAL_RE.search(text):
        failures.append(f"old template visual remains in {rel}")
    parser = VisualParser(text)
    seen: set[str] = set()
    for attrs, inside_commercial in parser.images:
        src = attrs.get("src") or ""
        role = attrs.get("data-editorial-photo")
        if "images.unsplash.com" in src and not role:
            failures.append(f"unclassified Unsplash image in {rel}: {src}")
        if role:
            seen.add(role)
            if role not in approved:
                failures.append(f"unknown editorial photo role {role} in {rel}")
            elif src != approved[role]:
                failures.append(f"editorial photo URL mismatch for {role} in {rel}")
            if inside_commercial:
                failures.append(f"context photo inside exact-product card in {rel}: {role}")
        elif src in approved_urls:
            failures.append(f"approved photo missing role in {rel}: {src}")
    for role in sorted(required_roles - seen):
        failures.append(f"required editorial photo missing in {rel}: {role}")

if failures:
    raise SystemExit("RG6_PREMIUM_VISUAL_VALIDATOR_FAIL\n - " + "\n - ".join(sorted(set(failures))))
print("RG6_PREMIUM_VISUAL_VALIDATOR_PASS: approved source-native photography; no mutation performed")
