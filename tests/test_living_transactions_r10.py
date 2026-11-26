"""R10.5: deterministic two-connection interleavings on disposable fixtures."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from phimemory9.living_contract import Context, LocalIdentity, MemoryToken
from phimemory9.living_learning import learn, observe
from phimemory9.living_store import LivingStore
from phimemory9.living_transport import admit, pack


class TransactionR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.path, self.guard = root/"main.db", root/"guard.db"
        self.owner = LocalIdentity("fixture:owner", b"o"*32)
        self.sender = LocalIdentity("fixture:sender", b"s"*32)
        self.dest = LocalIdentity("fixture:destination", b"d"*32)
        self.a = LivingStore.create(self.path, self.guard, self.owner)
        self.addCleanup(self.a.close)
        self.a.register_identity(self.sender)
        self.a.register_identity(self.dest)
        self.policy = self.a.set_policy(1)
        self.gid = "fixture:gene"
        metadata = dict(gene_id=self.gid, project="demo", privacy="public",
                        consent="ask_first", repair="clean", confidence="high",
                        claim="fact", source_refs=["fixture:source"],
                        activate=["research"], suppress=[])
        self.a.add_gene(self.gid, "invented observation", metadata,
                        MemoryToken("fixture:token", "synthetic",
                                    "fixture:source", "gene", "fixture:v1"))
        self.context = Context("demo", "demo-app", "research", ("research",),
                               self.dest.principal_id)
        self.b = LivingStore.open(self.path, self.guard, self.owner)
        self.addCleanup(self.b.close)

    def interleave(self, competing, operation):
        original = self.a.engine.transaction
        called = False

        @contextmanager
        def boundary():
            nonlocal called
            if not called:
                called = True
                competing()
            with original():
                yield

        with patch.object(self.a.engine, "transaction", boundary):
            try:
                return operation()
            finally:
                self.assertTrue(called, "competing transaction must execute")

    def grant(self, operation):
        return self.a.grant(self.gid, self.sender, self.context, operation,
                            now=100, expires_at=200)

    def evaluate(self):
        return self.a.evaluate([self.gid], self.sender, self.context, "express",
                               now=150, expected_policy=self.policy)

    def packet(self):
        self.grant("transfer")
        return pack(self.a, [self.gid], self.sender, self.dest, self.context,
                    now=150, expires_at=190, expected_policy=self.policy)

    def count(self, table):
        return self.a.db.execute("SELECT count(*) FROM "+table).fetchone()[0]

    def test_identity_revoked_before_expression_lock(self):
        self.grant("express")
        before = self.count("lm_events")
        with self.assertRaisesRegex(PermissionError, "revoked"):
            self.interleave(lambda: self.b.revoke_identity(self.sender.principal_id),
                            self.evaluate)
        self.assertEqual(self.count("lm_events"), before)

    def test_identity_revoked_before_grant_lock(self):
        before = self.count("lm_consents")
        with self.assertRaisesRegex(PermissionError, "revoked"):
            self.interleave(lambda: self.b.revoke_identity(self.sender.principal_id),
                            lambda: self.grant("express"))
        self.assertEqual(self.count("lm_consents"), before)

    def test_policy_revision_cannot_regress_between_checks(self):
        with self.assertRaisesRegex(ValueError, "policy revision"):
            self.interleave(lambda: self.b.set_policy(3),
                            lambda: self.a.set_policy(2))
        self.assertEqual(self.a.policy()[0]["revision"], 3)

    def test_consent_withdrawal_before_expression_lock(self):
        consent = self.grant("express")
        result = self.interleave(lambda: self.b.withdraw_consent(consent.consent_id),
                                 self.evaluate)
        self.assertEqual(result.admitted_ids, ())
        self.assertEqual(result.held, ((self.gid, "consent_missing_or_expired"),))

    def test_destination_revoked_before_packet_creation_lock(self):
        self.grant("transfer")
        before = self.count("lm_events")
        with self.assertRaisesRegex(PermissionError, "revoked"):
            self.interleave(lambda: self.b.revoke_identity(self.dest.principal_id),
                            lambda: pack(self.a, [self.gid], self.sender, self.dest,
                                         self.context, now=150, expires_at=190,
                                         expected_policy=self.policy))
        self.assertEqual(self.count("lm_events"), before)

    def test_source_revoked_before_admission_lock(self):
        packet = self.packet()
        with self.assertRaisesRegex(PermissionError, "revoked"):
            self.interleave(lambda: self.b.revoke_identity(self.sender.principal_id),
                            lambda: admit(self.a, packet, self.sender, self.dest, now=151))
        self.assertEqual(self.count("lm_guard.replays"), 0)
        self.assertEqual(self.count("lm_receipts"), 0)

    def test_destination_revoked_before_cached_admission_lock(self):
        packet = self.packet()
        admit(self.a, packet, self.sender, self.dest, now=151)
        with self.assertRaisesRegex(PermissionError, "revoked"):
            self.interleave(lambda: self.b.revoke_identity(self.dest.principal_id),
                            lambda: admit(self.a, packet, self.sender, self.dest, now=152))
        self.assertEqual(self.count("lm_guard.replays"), 1)
        self.assertEqual(self.count("lm_receipts"), 1)

    def test_learning_reads_after_competing_forget(self):
        observe(self.a, self.gid, "train", 1, 2)
        self.grant("learn")
        result = self.interleave(lambda: self.b.repair(self.gid, "forget"),
                                 lambda: learn(self.a, self.sender, self.context,
                                               now=150, expected_policy=self.policy))
        self.assertEqual(result["status"], "NO_GOVERNED_OBSERVATIONS")
        self.assertEqual(result["excluded_count"], 0)
        self.assertNotIn("event_id", result)
        self.assertEqual(self.count("lm_observations"), 0)

    def test_empty_learning_still_authenticates(self):
        self.b.revoke_identity(self.sender.principal_id)
        with self.assertRaisesRegex(PermissionError, "revoked"):
            learn(self.a, self.sender, self.context, now=150, expected_policy=self.policy)

    def test_parallel_duplicate_admission_returns_one_receipt(self):
        packet = self.packet()
        barrier = threading.Barrier(2)

        def worker():
            with LivingStore.open(self.path, self.guard, self.owner) as store:
                barrier.wait(timeout=10)
                return admit(store, packet, self.sender, self.dest, now=151)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            first, second = [f.result(timeout=20) for f in futures]
        self.assertEqual(first, second)
        self.assertEqual(self.count("lm_guard.replays"), 1)
        self.assertEqual(self.count("lm_receipts"), 1)


if __name__ == "__main__":
    unittest.main()
