"""Separately formulated arithmetic oracle and adversarial split controls.

These are same-author implementation checks, not external verification.
The oracle uses a modular inverse, not the production hypothesis enumerator.
"""
import copy
import unittest

from phimemory9.genomememory_integration import _fixtures
from phimemory9.genomememory_relational import experiment
from phimemory9 import phageledger_packets as packets


class AuditR1Tests(unittest.TestCase):
    def test_algebraic_oracle_exhaustive(self):
        inventory, rows = _fixtures()[4:]
        for a in range(1, 31):
            for b in range(31):
                samples = [dict(r, y=(a*r['x']+b) % 31) for r in rows]
                x0, x1 = samples[:2]
                slope = ((x1['y']-x0['y']) * pow(x1['x']-x0['x'], -1, 31)) % 31
                intercept = (x0['y']-slope*x0['x']) % 31
                result = experiment(inventory, samples)
                self.assertEqual(result['rule'], [slope, intercept])
                self.assertEqual(result['test_matches'], 2)

    def test_reject_train_depending_on_heldout(self):
        inventory, rows = _fixtures()[4:]
        inventory['nodes'][1].update(kind='descendant', depends_on=['fixture:o5'])
        with self.assertRaisesRegex(ValueError, 'cross-split'):
            experiment(inventory, rows)

    def test_reject_audit_depending_on_heldout_transitively(self):
        inventory, rows = _fixtures()[4:]
        inventory['nodes'][4].update(kind='descendant', depends_on=['fixture:bridge'])
        inventory['nodes'].append(dict(node_id='fixture:bridge', kind='descendant',
                                       depends_on=['fixture:o5']))
        with self.assertRaisesRegex(ValueError, 'cross-split'):
            experiment(inventory, rows)

    def test_no_fit_from_heldout_answers(self):
        inventory, rows = _fixtures()[4:]
        altered = copy.deepcopy(rows)
        altered[-1]['y'] = (altered[-1]['y']+1) % 31
        left, right = experiment(inventory, rows), experiment(inventory, altered)
        self.assertEqual(left['rule'], right['rule'])
        self.assertEqual((left['test_matches'], right['test_matches']), (2, 1))

    def test_receipt_substitution_never_grants_authority(self):
        envelope = dict(schema=packets.SCHEMA, synthetic=True, packet_id='fixture:p',
                        source='fixture:a', destination='fixture:b', purpose='metadata_review',
                        not_before=100, expires_at=200, payload_kind='synthetic_metadata_digest',
                        payload_sha256='1'*64, policy_sha256='2'*64, authority='NONE')
        # An attacker may recompute every unkeyed commitment; it still cannot grant use.
        result = packets.inspect(envelope, packets.seal(envelope)['envelope_sha256'],
                                 expected_source='fixture:a', expected_destination='fixture:b',
                                 expected_purpose='metadata_review', expected_payload_sha256='1'*64,
                                 expected_policy_sha256='2'*64, now=150)
        self.assertTrue(result['compatible'])
        self.assertEqual(result['status'], 'HELD')
        self.assertFalse(result['eligible'])

