"""Inventory published claim assertions; this is not factual verification or QA approval."""
import argparse
from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

from public_bundle import public_files


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_json = False
        self.buffer = []
        self.documents = []
        self.errors = 0
        self.fallbacks = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json':
            self.in_json = True
            self.buffer = []
        if tag == 'img' and 'm.media-amazon.com' in attrs.get('src', ''):
            if 'unsplash.com' in attrs.get('onerror', ''):
                self.fallbacks += 1

    def handle_data(self, data):
        if self.in_json:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.in_json:
            self.in_json = False
            try:
                self.documents.append(json.loads(''.join(self.buffer)))
            except (ValueError, TypeError):
                self.errors += 1


def assertions(value, output):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'price', 'availability', 'aggregateRating', 'reviewRating',
                       'datePublished', 'dateModified', 'priceValidUntil', 'citation'}:
                output[key] += 1
            assertions(child, output)
    elif isinstance(value, list):
        for child in value:
            assertions(child, output)


def inventory(root, destination):
    rows = []
    for source, rel in public_files(root):
        if source.suffix.lower() != '.html':
            continue
        raw = source.read_bytes()
        page = Page()
        page.feed(raw.decode('utf-8'))
        counts = Counter()
        for document in page.documents:
            assertions(document, counts)
        rows.append({'path': rel, 'sha256': hashlib.sha256(raw).hexdigest(),
                     **{key: counts[key] for key in ('price', 'availability', 'aggregateRating',
                         'reviewRating', 'datePublished', 'dateModified', 'priceValidUntil', 'citation')},
                     'amazon_image_unsplash_fallback': page.fallbacks,
                     'invalid_jsonld': page.errors})
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / 'commercial-claims-inventory.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'status': 'INVENTORY_COMPLETE_REQUIRES_EVIDENCE_REVIEW',
        'release_approved': False,
        'html_files_reviewed': len(rows),
        'pages_with_assertion': {key: sum(bool(row[key]) for row in rows) for key in list(rows[0])[2:]},
        'limitations': [
            'Presence of a static assertion is not proof it is false; absence of citation in JSON-LD is not proof no external evidence exists.',
            'This inventories all published HTML including legacy reviews; it does not exclude pages or change buyer-facing content.',
            'Copy claims outside JSON-LD and dynamic data need separate evidence review. No price, stock, rating or product fact was externally verified.',
            'A commercial Amazon image that swaps to Unsplash on error risks wrong product imagery and requires source correction.',
        ],
    }
    (destination / 'commercial-claims-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inventory(Path(__file__).resolve().parents[1], args.output), ensure_ascii=False))
