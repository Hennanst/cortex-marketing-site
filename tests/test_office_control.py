import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from office_control import plan_mutation


class OfficeMutationTests(unittest.TestCase):
    def setUp(self):
        # Deliberately reorder every business table and the configuration headers.
        self.snapshot = {
            'CONFIG': [['value', 'key'], ['CO', 'ACCOUNT_CODE'], ['1653454', 'TAILWIND_ACCOUNT_ID'],
                       ['https://cortex-ofertas.pages.dev/', 'CANONICAL_HOST'],
                       ['cortexofertas-20', 'AFFILIATE_TAG'],
                       ['Hennanst/cortex-marketing-site', 'GITHUB_MARKETING_REPO'],
                       ['MANUAL_MAINTENANCE', 'OFFICE_EXECUTION_MODE']],
            'GATES': [['status', 'gate_id', 'domain_job', 'gate_name', 'evidence_ref'],
                      ['REVISE', 'RG5', 'CO', 'QA', 'issue/1'],
                      ['PASS', 'RG3', 'CO', 'Image', 'artifact/1']],
            'JOBS': [['state', 'job_id', 'lane', 'priority', 'next_gate'],
                     ['AWAITING_QA', 'JOB1', 'RECOVERY', 'P0', 'RG5']],
            'STATE': [['status', 'state_id', 'domain'], ['LOCKED', 'CO-GLOBAL', 'CO']],
            'LOCKS': [['lock_id', 'scope', 'status', 'release_condition'],
                      ['MAIN', 'CO', 'LOCKED', 'independent review']],
            'RUN_CONTROL': [['lease_id', 'status', 'run_id', 'expires_at'],
                            ['CO-DYNAMIC-RUNNER-LEASE', 'HELD', 'mine', '2026-09-07T10:00:00Z']],
            'TRANSACTIONS': [['tx_id', 'target_id', 'operation'], ['TX1', 'RG3', 'REVIEW']],
        }
        self.plan = {'execution_context': 'manual', 'operation': 'state_patch',
                     'external_ref': 'artifact/2', 'tx_id': 'TX2', 'patches': [
                         {'tab': 'GATES', 'id': 'RG5', 'expected': {'status': 'REVISE'},
                          'changes': {'status': 'AWAITING_QA'}}]}
        self.now = datetime(2026, 9, 7, 9, tzinfo=timezone.utc)

    def run_plan(self, plan=None):
        return plan_mutation(self.snapshot, plan or self.plan, 'mine', self.now)

    def test_minimal_patch_follows_headers_and_ids(self):
        before = copy.deepcopy(self.snapshot)
        result = self.run_plan()
        update = result['requests'][0]['updateCells']
        self.assertEqual(update['start'], {'sheetId': 1763579041, 'rowIndex': 1, 'columnIndex': 0})
        self.assertEqual(len(result['requests']), 1)
        self.assertTrue(result['requires_atomic_transaction_append'])
        self.assertFalse(result['external_operation_authorized'])
        self.assertEqual(self.snapshot, before)

    def test_paused_scheduled_worker_cannot_mutate(self):
        with self.assertRaisesRegex(ValueError, 'SCHEDULERS_PAUSED'):
            self.run_plan(self.plan | {'execution_context': 'scheduled'})

    def test_approved_evidence_and_state_cannot_be_overwritten(self):
        for changes, expected in [({'status': 'REVISE'}, {'status': 'PASS'}),
                                  ({'evidence_ref': 'replacement'}, {'evidence_ref': 'artifact/1'})]:
            with self.assertRaisesRegex(ValueError, 'APPROVED_STATE_CHANGE'):
                self.run_plan(self.plan | {'patches': [{'tab': 'GATES', 'id': 'RG3',
                                                       'expected': expected, 'changes': changes}]})

    def test_stale_duplicate_and_release_plans_are_rejected(self):
        cases = [self.plan | {'operation': 'deploy'},
                 self.plan | {'tx_id': 'TX1'},
                 self.plan | {'patches': self.plan['patches'] * 2},
                 self.plan | {'patches': [self.plan['patches'][0] | {'expected': {'status': 'PASS'}}]},
                 self.plan | {'patches': [self.plan['patches'][0] | {'changes': {'status': 'PASS'}}]},
                 self.plan | {'patches': [{'tab': 'STATE', 'id': 'CO-GLOBAL',
                                          'expected': {'status': 'LOCKED'}, 'changes': {'status': 'READY'}}]}]
        for plan in cases:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                self.run_plan(plan)


if __name__ == '__main__':
    unittest.main()
