import sys
from pathlib import Path
import tempfile
import unittest
import json
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from public_bundle import package
from recovery_source_truth_guard import canonical_failures, classify_html, compare_dist, scan_source
from office_control import table, plan_patch, assert_lease, topological_order, validate_evidence


class RecoveryTests(unittest.TestCase):
    def write_manifests(self, root, public, quarantine_files=(), patterns=(), exceptions=(), extra_static=()):
        data = root / 'data'
        data.mkdir(exist_ok=True)
        static = sorted({'_headers', 'robots.txt', 'sitemap.xml', *extra_static})
        for rel in static:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if rel == 'sitemap.xml':
                urls = []
                for page in public:
                    route = '/' + page
                    if route.endswith('index.html'):
                        route = route[:-len('index.html')]
                    urls.append(f'<url><loc>https://cortex-ofertas.pages.dev{route}</loc></url>')
                path.write_text('<urlset>' + ''.join(urls) + '</urlset>')
            elif not path.exists():
                path.write_text('fixture')
        (data / 'publication-manifest.json').write_text(json.dumps({
            'version': 1,
            'invariant': 'REVIEWED_PUBLICATION_MANIFEST_EQUALS_BUILD_OUTPUT',
            'html': sorted(public),
            'static': static,
        }))
        (data / 'quarantine-manifest.json').write_text(json.dumps({
            'version': 1,
            'reason': 'TEST_QUARANTINE',
            'files': sorted(quarantine_files),
            'patterns': sorted(patterns),
            'exceptions': sorted(exceptions),
            'expected_html_count': len(quarantine_files),
        }))

    def test_inches_in_image_alt_must_be_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / 'index.html'
            self.write_manifests(root, ['index.html'])
            page.write_text('<img src="monitor.jpg" alt="Monitor 24" IPS" loading="lazy">')
            self.assertIn('MALFORMED_IMAGE_ATTRIBUTES: index.html', scan_source(root))
            page.write_text('<img src="monitor.jpg" alt="Monitor 24&quot; IPS" loading="lazy" hidden>')
            self.assertNotIn('MALFORMED_IMAGE_ATTRIBUTES: index.html', scan_source(root))

    def test_product_image_cannot_fallback_to_unrelated_photo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / 'index.html'
            canonical = '<link rel="canonical" href="https://cortex-ofertas.pages.dev/">'
            self.write_manifests(root, ['index.html'])
            page.write_text(canonical + '<img src="https://m.media-amazon.com/images/I/product.jpg" onerror="this.src=\'https://images.unsplash.com/unrelated\'">')
            self.assertIn('WRONG_PRODUCT_IMAGE_FALLBACK: index.html', scan_source(root))
            page.write_text(canonical + '<img src="https://m.media-amazon.com/images/I/product.jpg">')
            self.assertNotIn('WRONG_PRODUCT_IMAGE_FALLBACK: index.html', scan_source(root))

    def test_dynamic_data_cannot_restore_obsolete_affiliate_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            (root / 'data/products.json').write_text('{"tag":"hennanst-20"}')
            (root / 'index.html').write_text('<link rel="canonical" href="https://cortex-ofertas.pages.dev/">')
            self.write_manifests(root, ['index.html'], extra_static=['data/products.json'])
            self.assertIn('OBSOLETE_AFFILIATE_TAG_IN_SOURCE: data/products.json', scan_source(root))

    def test_canonical_parser_rejects_spoofed_origin_and_wrong_route(self):
        self.assertEqual(canonical_failures("<link href='https://cortex-ofertas.pages.dev/guia/a.html' REL='canonical'>", 'guia/a.html'), [])
        for url in ['https://cortex-ofertas.pages.dev.evil.test/', 'http://cortex-ofertas.pages.dev/', 'https://cortex-ofertas.pages.dev/wrong.html']:
            self.assertTrue(canonical_failures(f'<link href="{url}" rel="canonical">', 'index.html'))
        self.assertTrue(canonical_failures('', 'index.html'))

    def test_full_bundle_detects_missing_changed_and_extra_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ['index.html', 'guia/example.html', 'assets/a.css', 'data/reviews.json']:
                p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('unchanged')
            (root / 'index.html').write_text('<link rel="stylesheet" href="assets/a.css">')
            self.write_manifests(root, ['guia/example.html', 'index.html'])
            (root / 'docs').mkdir(); (root / 'docs/private.json').write_text('operational')
            dist = root / 'dist'; package(root, dist)
            self.assertEqual(compare_dist(root, dist), [])
            self.assertFalse((dist / 'docs').exists())
            self.assertFalse((dist / 'data/reviews.json').exists())
            (dist / 'guia/example.html').write_text('silently changed')
            (dist / 'robots.txt').unlink()
            (dist / 'unexpected.txt').write_text('not reviewed')
            failures = compare_dist(root, dist)
            self.assertEqual(len(failures), 3)

    def test_every_source_html_is_public_or_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<link rel="canonical" href="https://cortex-ofertas.pages.dev/">')
            legacy = root / 'review/legacy.html'; legacy.parent.mkdir(); legacy.write_text('legacy')
            self.write_manifests(root, ['index.html'], quarantine_files=['review/legacy.html'])
            discovered, public, quarantined, failures = classify_html(root)
            self.assertEqual((len(discovered), len(public), len(quarantined)), (2, 1, 1))
            self.assertEqual(failures, [])
            extra = root / 'forgotten.html'; extra.write_text('unclassified')
            self.assertIn('UNCLASSIFIED_SOURCE_HTML: forgotten.html', scan_source(root))

    def test_public_page_cannot_link_to_quarantined_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<link rel="canonical" href="https://cortex-ofertas.pages.dev/"><a href="review/legacy.html">old</a>')
            legacy = root / 'review/legacy.html'; legacy.parent.mkdir(); legacy.write_text('legacy')
            self.write_manifests(root, ['index.html'], quarantine_files=['review/legacy.html'])
            self.assertIn('PUBLIC_LINK_TO_QUARANTINED_HTML[review/legacy.html]: index.html', scan_source(root))

    def test_unverified_static_offer_cannot_enter_public_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<link rel="canonical" href="https://cortex-ofertas.pages.dev/"><script type="application/ld+json">{"priceCurrency":"BRL"}</script>')
            self.write_manifests(root, ['index.html'])
            self.assertTrue(any(item.startswith('UNVERIFIED_COMMERCIAL_CLAIM_ON_PUBLIC_ROUTE') for item in scan_source(root)))

    def test_publication_manifest_rejects_path_escape_and_html_in_static(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('fixture')
            self.write_manifests(root, ['index.html'])
            manifest = root / 'data/publication-manifest.json'
            data = json.loads(manifest.read_text())
            data['static'].append('../outside.txt')
            data['static'].sort()
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'UNSAFE_PATH'):
                package(root, root / 'dist')
            data['static'] = ['_headers', 'index.html', 'robots.txt', 'sitemap.xml']
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'HTML_IN_STATIC'):
                package(root, root / 'dist')

    def test_duplicate_and_reordered_rows(self):
        rows = [['status', 'gate_id'], ['REVISE', 'RG5'], ['PASS', 'RG3']]
        patch = plan_patch(rows, 'gate_id', 'RG5', {'status': 'REVISE'}, {'status': 'AWAITING_QA'})
        self.assertEqual((patch[0]['rowIndex'], patch[0]['columnIndex']), (1, 0))
        with self.assertRaises(ValueError):
            plan_patch(rows, 'gate_id', 'RG3', {'status': 'REVISE'}, {'status': 'PASS'})
        with self.assertRaises(ValueError):
            table(rows + [['PASS', 'RG5']], 'gate_id', {'gate_id', 'status'})
        with self.assertRaises(ValueError):
            plan_patch(rows, 'gate_id', 'RG3', {}, {'status': 'REVISE'})

    def test_lease_and_independence(self):
        rows = [['lease_id', 'status', 'run_id', 'expires_at'], ['CO-DYNAMIC-RUNNER-LEASE', 'HELD', 'mine', '2026-09-07T10:00:00+00:00']]
        for holder, now in [('other', '2026-09-07T09:00:00+00:00'), ('mine', '2026-09-07T10:00:00+00:00')]:
            with self.assertRaises(ValueError):
                assert_lease(rows, holder, datetime.fromisoformat(now))
        sha = 'a' * 40
        evidence = {'sha': sha, 'executed': True, 'status': 'PASS', 'artifact': 'CI/1', 'reviewed': 784, 'unknown': 0, 'review_run': 'independent'}
        validate_evidence(evidence, sha, 784, 'producer')
        for override in [{'executed': False}, {'sha': 'b'*40}, {'reviewed': 0}, {'review_run': 'producer'}, {'unknown': 1}]:
            with self.assertRaises(ValueError):
                validate_evidence(evidence | override, sha, 784, 'producer')
        for field in ['unknown', 'reviewed', 'review_run']:
            incomplete = {k: v for k, v in evidence.items() if k != field}
            with self.subTest(missing=field), self.assertRaises(ValueError):
                validate_evidence(incomplete, sha, 784, 'producer')
        for override in [{'unknown': False}, {'reviewed': 784.0}]:
            with self.assertRaises(ValueError):
                validate_evidence(evidence | override, sha, 784, 'producer')
        with self.assertRaises(ValueError):
            validate_evidence(evidence, sha, 784, '')

    def test_release_order_has_no_circular_dependency(self):
        graph = {'QA': [], 'AUTHORIZE_SHA': ['QA'], 'DEPLOY': ['AUTHORIZE_SHA'], 'PUBLIC_QA': ['DEPLOY'], 'MARKET_READY': ['PUBLIC_QA'], 'ACQUISITION': ['MARKET_READY']}
        self.assertEqual(topological_order(graph), list(graph))
        with self.assertRaises(ValueError):
            topological_order({'RG8': ['RG9'], 'RG9': ['RG8']})


if __name__ == '__main__':
    unittest.main()
