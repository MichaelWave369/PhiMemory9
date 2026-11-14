"""Deterministic synthetic audit cases for R0.2; no outside sources."""
import tempfile
import unittest
from pathlib import Path

from phimemory9 import MemoryEngine, MemoryError9
from phimemory9.evidence import EvidenceLedger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.memory = MemoryEngine()
        self.blob = self.memory.create_blob("Evidence lab")
        self.memory_id = self.memory.enter(
            self.blob, "Recorded claim: the sensor is functional.", "fixture:one"
        )
        self.ledger = EvidenceLedger(self.memory)

    def tearDown(self):
        self.memory.close()

    def test_claim_source_attach_and_export(self):
        source = self.ledger.source(
            "Synthetic log", "fixture:one", kind="synthetic",
            independence_group="family-a"
        )
        claim = self.ledger.claim(self.memory_id, "The sensor is functional")
        link = self.ledger.attach(claim, source, "support", excerpt="OK")
        result = self.ledger.report(claim)
        self.assertEqual(result["classification"], "source_pointers_attached")
        self.assertEqual(result["declared_groups_by_stance"]["support"], ["family-a"])
        self.assertEqual(result["evidence_links"][0]["id"], link)
        self.assertEqual(self.ledger.export(claim)["sources"][0]["id"], source)
        self.assertEqual(self.ledger.export(claim)["lineage"][-1]["id"], self.memory_id)
        self.assertTrue(self.ledger.audit()["ok"])

    def test_conflicting_claims_are_preserved_symmetrically(self):
        claim_a = self.ledger.claim(self.memory_id, "The sensor is functional")
        claim_b = self.ledger.claim(self.memory_id, "The sensor is defective")
        self.ledger.contradiction(claim_a, claim_b, "Conflicting observations")
        for claim in (claim_a, claim_b):
            self.assertEqual(
                self.ledger.report(claim)["classification"], "explicitly_contested"
            )
        self.assertEqual(self.memory.memory(self.memory_id)["status"], "active")
        with self.assertRaises(MemoryError9):
            self.ledger.contradiction(claim_b, claim_a, "Duplicate")

    def test_declared_independence_does_not_count_duplicate_groups(self):
        claim = self.ledger.claim(self.memory_id, "An observation")
        a = self.ledger.source(
            "Log A", "fixture:a", kind="synthetic", independence_group="same-feed"
        )
        b = self.ledger.source(
            "Log B", "fixture:b", kind="synthetic", independence_group="same-feed"
        )
        self.ledger.attach(claim, a, "support")
        self.ledger.attach(claim, b, "support")
        summary = self.ledger.report(claim)
        self.assertEqual(len(summary["evidence_links"]), 2)
        self.assertEqual(summary["declared_groups_by_stance"]["support"], ["same-feed"])

    def test_unverified_is_not_promoted_to_truth(self):
        claim = self.ledger.claim(self.memory_id, "An unverified interpretation")
        self.assertEqual(self.ledger.report(claim)["classification"], "unreviewed")
        source = self.ledger.source("Source", "fixture:source")
        self.ledger.attach(claim, source, "context")
        self.assertEqual(self.ledger.report(claim)["classification"], "source_pointers_attached")

    def test_bad_stance_duplicate_and_locator_rejected(self):
        claim = self.ledger.claim(self.memory_id, "A claim")
        source = self.ledger.source("Source", "fixture:source")
        with self.assertRaises(MemoryError9):
            self.ledger.attach(claim, source, "yes")
        self.ledger.attach(claim, source, "challenge")
        with self.assertRaises(MemoryError9):
            self.ledger.attach(claim, source, "challenge")
        with self.assertRaises(MemoryError9):
            self.ledger.source("Duplicate", "fixture:source")

    def test_reject_bad_declared_hash(self):
        with self.assertRaises(MemoryError9):
            self.ledger.source("S", "fixture:s", declared_sha256="fake")

    def test_audit_detects_modified_claim(self):
        claim = self.ledger.claim(self.memory_id, "Initial wording")
        self.memory.db.execute(
            "UPDATE e_claims SET statement='Altered wording' WHERE id=?", (claim,)
        )
        self.memory.db.commit()
        result = self.ledger.audit()
        self.assertFalse(result["ok"])
        self.assertIn("e_claims", " ".join(result["problems"]))

    def test_audit_detects_modified_event(self):
        source = self.ledger.source("S", "fixture:s")
        self.memory.db.execute(
            "UPDATE e_log SET action='FORGED' WHERE seq=1"
        )
        self.memory.db.commit()
        result = self.ledger.audit()
        self.assertFalse(result["ok"])
        self.assertIn("hash-chain", " ".join(result["problems"]))

    def test_contradiction_must_have_two_distinct_claims(self):
        claim = self.ledger.claim(self.memory_id, "A claim")
        with self.assertRaises(MemoryError9):
            self.ledger.contradiction(claim, claim, "self")

    def test_transaction_rollback_on_duplicate_claim_source_stance(self):
        claim = self.ledger.claim(self.memory_id, "A claim")
        source = self.ledger.source("S", "fixture:s")
        self.ledger.attach(claim, source, "support")
        event_count = self.ledger.audit()["events"]
        with self.assertRaises(MemoryError9):
            self.ledger.attach(claim, source, "support")
        self.assertEqual(self.ledger.audit()["events"], event_count)

    def test_disk_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.sqlite3"
            with MemoryEngine(path) as memory:
                root = memory.create_blob("Root")
                mid = memory.enter(root, "Local synthetic observation")
                ledger = EvidenceLedger(memory)
                claim = ledger.claim(mid, "Declared hypothesis")
                source = ledger.source("Fixture", "fixture:test", kind="synthetic")
                ledger.attach(claim, source, "challenge")
            with MemoryEngine(path) as reopened:
                ledger2 = EvidenceLedger(reopened)
                self.assertTrue(ledger2.audit()["ok"])
                self.assertEqual(
                    ledger2.report(claim)["classification"], "explicitly_contested"
                )


if __name__ == "__main__":
    unittest.main()
