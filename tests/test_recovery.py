import sys
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from public_bundle import package
from recovery_source_truth_guard import canonical_failures, compare_dist, scan_source
from office_control import table, plan_patch, assert_lease, topological_order, validate_evidence


class RecoveryTests(unittest.TestCase):
    def test_dynamic_data_cannot_restore_obsolete_affiliate_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            (root / 'data/products.json').write_text('{"tag":"hennanst-20"}')
            self.assertIn('OBSOLETE_AFFILIATE_TAG_IN_SOURCE: data/products.json', scan_source(root))

    def test_canonical_parser_rejects_spoofed_origin_and_wrong_route(self):
        self.assertEqual(canonical_failures("<link href='https://cortex-ofertas.pages.dev/guia/a.html' REL='canonical'>", 'guia/a.html'), [])
        for url in ['https://cortex-ofertas.pages.dev.evil.test/', 'http://cortex-ofertas.pages.dev/', 'https://cortex-ofertas.pages.dev/wrong.html']:
            self.assertTrue(canonical_failures(f'<link href="{url}" rel="canonical">', 'index.html'))
        self.assertTrue(canonical_failures('', 'index.html'))

    def test_full_bundle_detects_missing_changed_and_extra_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ['index.html', 'guia/example.html', 'assets/a.css', 'data/reviews.json', 'robots.txt', '_headers']:
                p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('unchanged')
            (root / 'docs').mkdir(); (root / 'docs/private.json').write_text('operational')
            dist = root / 'dist'; package(root, dist)
            self.assertEqual(compare_dist(root, dist), [])
            self.assertFalse((dist / 'docs').exists())
            (dist / 'guia/example.html').write_text('silently changed')
            (dist / 'robots.txt').unlink()
            (dist / 'unexpected.txt').write_text('not reviewed')
            failures = compare_dist(root, dist)
            self.assertEqual(len(failures), 3)

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
