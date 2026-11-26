"""Abrupt subprocess exit at real SQLite transaction boundaries, fixtures only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from phimemory9.living_contract import Context, LocalIdentity, MemoryToken
from phimemory9.living_store import LivingStore
from phimemory9.living_transport import admit, pack

OWNER = LocalIdentity("fixture:owner", b"o"*32)
SENDER = LocalIdentity("fixture:sender", b"s"*32)
DEST = LocalIdentity("fixture:destination", b"d"*32)
CTX = Context("demo", "demo-app", "research", ("research",), DEST.principal_id)
GID = "fixture:gene"
EXIT_CODE = 91


def worker(path, guard, action, boundary, payload):
    # These are hard-coded synthetic credentials, never production keys.
    with LivingStore.open(path, guard, OWNER) as store:
        def operation():
            if action == "forget":
                store.repair(GID, "forget")
            elif action == "withdraw":
                store.withdraw_consent(payload)
            elif action == "admit":
                admit(store, payload, SENDER, DEST, now=151)
            elif action == "policy":
                store.set_policy(2)
            else:
                raise ValueError("unknown fixture action")

        if boundary == "committed":
            operation()
        else:
            with store.engine.transaction():
                if boundary != "uncommitted":
                    # Trace fires BEFORE the selected next SQL statement.
                    # The preceding statement has therefore already returned.
                    def trace(sql):
                        if sql.startswith(boundary):
                            os._exit(EXIT_CODE)
                    store.db.set_trace_callback(trace)
                operation()
                if boundary != "uncommitted":
                    raise AssertionError("requested SQL boundary was not reached")
                os._exit(EXIT_CODE)
        os._exit(EXIT_CODE)


class ProcessRecoveryR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.path, self.guard = root/"main.db", root/"guard.db"
        with LivingStore.create(self.path, self.guard, OWNER) as store:
            store.register_identity(SENDER)
            store.register_identity(DEST)
            self.policy = store.set_policy(1)
            metadata = dict(gene_id=GID, project="demo", privacy="public",
                            consent="ask_first", repair="clean", confidence="high",
                            claim="fact", source_refs=["fixture:source"],
                            activate=["research"], suppress=[])
            store.add_gene(GID, "invented observation", metadata,
                           MemoryToken("fixture:token", "synthetic",
                                       "fixture:source", "gene", "fixture:v1"))
            self.consent = store.grant(GID, SENDER, CTX, "express",
                                       now=100, expires_at=200).consent_id
            store.grant(GID, SENDER, CTX, "transfer", now=100, expires_at=200)
            self.packet = pack(store, [GID], SENDER, DEST, CTX, now=150,
                               expires_at=190, expected_policy=self.policy)

    def crash(self, action, boundary, payload=None):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                 "--worker", str(self.path), str(self.guard),
                                 action, boundary, json.dumps(payload)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, EXIT_CODE,
                         msg=result.stdout+"\n"+result.stderr)

    def open(self):
        return LivingStore.open(self.path, self.guard, OWNER)

    def count(self, store, table):
        return store.db.execute("SELECT count(*) FROM "+table).fetchone()[0]

    def evaluate(self, store):
        return store.evaluate([GID], SENDER, CTX, "express",
                              now=152, expected_policy=self.policy)

    def check_db(self, store):
        for db in ("main", "lm_guard"):
            self.assertEqual(store.db.execute("PRAGMA "+db+".integrity_check").fetchone()[0], "ok")
        self.assertTrue(store.reconstruct()["engine_integrity"])

    def test_forget_uncommitted_rolls_back_both_files(self):
        self.crash("forget", "uncommitted")
        with self.open() as store:
            self.assertEqual(store._gene(GID)["state"], "active")
            self.assertIsNone(store.block_action(GID))
            self.assertEqual(self.count(store, "lm_guard.blocks"), 0)
            self.assertEqual(self.evaluate(store).admitted_ids, (GID,))
            self.check_db(store)

    def test_forget_after_guard_write_rolls_back(self):
        self.crash("forget", "UPDATE lm_genes SET state='held'")
        with self.open() as store:
            self.assertEqual(store._gene(GID)["state"], "active")
            self.assertEqual(self.count(store, "lm_guard.blocks"), 0)
            self.check_db(store)

    def test_committed_forget_survives_abrupt_exit(self):
        self.crash("forget", "committed")
        with self.open() as store:
            self.assertEqual(store._gene(GID)["state"], "deleted")
            self.assertEqual(store.block_action(GID), "forget")
            self.assertEqual(self.count(store, "lm_guard.blocks"), 2)
            self.assertNotIn("invented observation", "\n".join(store.db.iterdump()))
            self.assertFalse(self.evaluate(store).admitted_ids)
            self.check_db(store)

    def test_withdrawal_between_guard_and_main_write_rolls_back(self):
        self.crash("withdraw", "UPDATE lm_consents SET withdrawn=1", self.consent)
        with self.open() as store:
            self.assertEqual(self.count(store, "lm_guard.withdrawals"), 0)
            self.assertEqual(self.evaluate(store).admitted_ids, (GID,))
            self.check_db(store)

    def test_committed_withdrawal_survives_exit(self):
        self.crash("withdraw", "committed", self.consent)
        with self.open() as store:
            self.assertEqual(self.count(store, "lm_guard.withdrawals"), 1)
            self.assertFalse(self.evaluate(store).admitted_ids)
            self.check_db(store)

    def test_replay_guard_without_receipt_rolls_back(self):
        self.crash("admit", "INSERT INTO lm_receipts", self.packet)
        with self.open() as store:
            self.assertEqual(self.count(store, "lm_guard.replays"), 0)
            self.assertEqual(self.count(store, "lm_receipts"), 0)
            first = admit(store, self.packet, SENDER, DEST, now=151)
            self.assertEqual(first, admit(store, self.packet, SENDER, DEST, now=152))
            self.check_db(store)

    def test_committed_admission_recovered_without_duplicate(self):
        self.crash("admit", "committed", self.packet)
        with self.open() as store:
            self.assertEqual(self.count(store, "lm_guard.replays"), 1)
            self.assertEqual(self.count(store, "lm_receipts"), 1)
            receipt = admit(store, self.packet, SENDER, DEST, now=152)
            self.assertEqual(receipt["body"]["admitted_at"], 151)
            self.assertEqual(self.count(store, "lm_receipts"), 1)
            self.check_db(store)

    def test_uncommitted_policy_does_not_replace_previous_policy(self):
        self.crash("policy", "uncommitted")
        with self.open() as store:
            self.assertEqual(store.policy()[0]["revision"], 1)
            self.assertEqual(store.policy()[1], self.policy)
            self.check_db(store)

    def test_committed_policy_survives_exit(self):
        self.crash("policy", "committed")
        with self.open() as store:
            self.assertEqual(store.policy()[0]["revision"], 2)
            self.assertFalse(self.evaluate(store).admitted_ids)
            self.check_db(store)


if __name__ == "__main__":
    if len(sys.argv) == 7 and sys.argv[1] == "--worker":
        worker(*sys.argv[2:6], json.loads(sys.argv[6]))
    else:
        unittest.main()
