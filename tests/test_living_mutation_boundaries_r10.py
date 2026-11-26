"""Scheduled competing fixture mutations around the outer write lock."""
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phimemory9.living_contract import LocalIdentity, MemoryToken, MemoryChromosome
from phimemory9.living_store import LivingStore


class MutationBoundariesR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.owner = LocalIdentity("fixture:owner", b"o"*32)
        self.a = LivingStore.create(self.root/"main.db", self.root/"guard.db", self.owner)
        self.addCleanup(self.a.close)
        self.b = LivingStore.open(self.root/"main.db", self.root/"guard.db", self.owner)
        self.addCleanup(self.b.close)

    def interleave(self, store, competing, operation):
        original = store.engine.transaction
        called = False

        @contextmanager
        def boundary():
            nonlocal called
            if not called:
                called = True
                competing()
            with original():
                yield

        with patch.object(store.engine, "transaction", boundary):
            try:
                return operation()
            finally:
                self.assertTrue(called)

    def add(self, store, name):
        gid = "fixture:"+name
        metadata = dict(gene_id=gid, project="demo", privacy="public",
                        consent="ask_first", repair="clean", confidence="high",
                        claim="fact", source_refs=["fixture:source"],
                        activate=["research"], suppress=[])
        return store.add_gene(gid, "invented "+name, metadata,
                              MemoryToken("fixture:token:"+name, "synthetic",
                                          "fixture:source", name, "fixture:v1"))

    def test_competing_upgrade_is_idempotent(self):
        path, guard = self.root/"old.db", self.root/"old-guard.db"
        with LivingStore.create(path, guard, self.owner, version=1) as first:
            with LivingStore.open(path, guard, self.owner) as second:
                self.interleave(first, second.upgrade_fixture, first.upgrade_fixture)
                self.assertEqual(first._meta("version"), "2")
                self.assertEqual(second._meta("version"), "2")
                self.assertTrue(first.reconstruct()["engine_integrity"])

    def test_competing_final_gene_respects_capacity(self):
        for i in range(255):
            self.add(self.a, "gene-"+str(i))
        with self.assertRaisesRegex(ValueError, "fixture gene budget"):
            self.interleave(self.a, lambda: self.add(self.b, "winner"),
                            lambda: self.add(self.a, "loser"))
        self.assertEqual(self.a.db.execute("SELECT count(*) FROM lm_genes").fetchone()[0], 256)
        self.assertEqual(self.a._gene("fixture:winner")["state"], "active")
        with self.assertRaises(ValueError):
            self.a._gene("fixture:loser")

    def test_chromosome_cannot_reintroduce_forgotten_membership(self):
        self.add(self.a, "target")
        chromosome = MemoryChromosome("root", "demo", None, ("fixture:target",))
        with self.assertRaises(ValueError):
            self.interleave(self.a, lambda: self.b.repair("fixture:target", "forget"),
                            lambda: self.a.add_chromosome(chromosome))
        self.assertEqual(self.a.db.execute("SELECT count(*) FROM lm_memberships").fetchone()[0], 0)
        self.assertEqual(self.a.db.execute("SELECT count(*) FROM lm_chromosomes").fetchone()[0], 0)

    def test_replacement_must_remain_active_at_repair_lock(self):
        self.add(self.a, "target")
        self.add(self.a, "replacement")
        with self.assertRaisesRegex(ValueError, "fresh active replacement"):
            self.interleave(self.a, lambda: self.b.repair("fixture:replacement", "retire"),
                            lambda: self.a.repair("fixture:target", "correct",
                                                  replacement="fixture:replacement"))
        self.assertEqual(self.a._gene("fixture:target")["state"], "active")
        self.assertEqual(self.a._gene("fixture:replacement")["state"], "retired")
        self.assertIsNone(self.a.block_action("fixture:target"))


if __name__ == "__main__":
    unittest.main()
