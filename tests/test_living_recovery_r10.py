"""Adversarial recovery regressions for disposable Living Memory stores only."""
from pathlib import Path
import shutil
import tempfile
import unittest

from phimemory9.living_contract import Context, LocalIdentity, MemoryToken
from phimemory9.living_store import LivingStore


class RecoveryR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.main = Path(self.tmp.name) / "memory.sqlite3"
        self.guard = Path(self.tmp.name) / "guard.sqlite3"
        self.owner = LocalIdentity("fixture:owner", b"o"*32)
        self.reader = LocalIdentity("fixture:reader", b"r"*32)
        self.store = LivingStore.create(self.main, self.guard, self.owner)
        self.addCleanup(lambda: self.store.close())
        self.store.register_identity(self.reader)
        self.policy = self.store.set_policy(1)
        self.ctx = Context("demo", "demo-app", "research", ("research",))
        self.add("target")
        self.add("child", parents=("fixture:target",))
        self.add("replacement")
        self.store.grant("fixture:target", self.reader, self.ctx, "express",
                         now=100, expires_at=200)

    def add(self, name, parents=()):
        gid = "fixture:"+name
        metadata = dict(gene_id=gid, project="demo", privacy="public",
                        consent="ask_first", repair="clean", confidence="high",
                        claim="fact", source_refs=["fixture:source"],
                        activate=["research"], suppress=[])
        token = MemoryToken("fixture:token:"+name, "synthetic",
                            "fixture:source", name, "fixture:v1")
        self.store.add_gene(gid, "invented "+name, metadata, token, parents=parents)

    def reopen(self):
        self.store.close()
        self.store = LivingStore.open(self.main, self.guard, self.owner)

    def state(self, name):
        return self.store._gene("fixture:"+name)["state"]

    def assert_denied(self):
        result = self.store.evaluate(["fixture:target"], self.reader, self.ctx,
                                     "express", now=150, expected_policy=self.policy)
        self.assertFalse(result.admitted_ids)

    def test_retirement_survives_repeated_cold_open(self):
        self.store.repair("fixture:target", "retire")
        before = self.store.reconstruct()
        for _ in range(2):
            self.reopen()
            self.assertEqual(self.state("target"), "retired")
            self.assertEqual(self.state("child"), "held")
            self.assertEqual(self.store.reconstruct(), before)
            self.assert_denied()

    def test_supersession_survives_cold_open(self):
        self.store.repair("fixture:target", "correct", replacement="fixture:replacement")
        before = self.store.reconstruct()
        self.reopen()
        self.assertEqual(self.state("target"), "superseded")
        self.assertEqual(self.state("child"), "held")
        self.assertEqual(self.state("replacement"), "active")
        self.assertEqual(self.store.reconstruct(), before)
        self.assert_denied()

    def test_stale_main_recovery_does_not_invent_terminal_state(self):
        snapshot = Path(self.tmp.name) / "old.sqlite3"
        # SQLite's backup API supplies a consistent main-only snapshot.
        import sqlite3
        with sqlite3.connect(snapshot) as backup:
            self.store.db.backup(backup)
        self.store.repair("fixture:target", "retire")
        self.store.close()
        shutil.copyfile(snapshot, self.main)
        self.store = LivingStore.open(self.main, self.guard, self.owner)
        self.assertEqual(self.state("target"), "held")
        self.assertEqual(self.state("child"), "held")
        self.assertEqual(self.state("replacement"), "active")
        self.assert_denied()

    def test_newer_revocation_overrides_prior_retirement(self):
        self.store.repair("fixture:target", "retire")
        self.store.repair("fixture:target", "revoke")
        self.reopen()
        self.assertEqual(self.state("target"), "held")
        self.assertEqual(self.state("child"), "held")
        self.assert_denied()


if __name__ == "__main__":
    unittest.main()
