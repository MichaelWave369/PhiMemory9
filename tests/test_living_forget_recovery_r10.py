"""Disposable fixture regressions for stable forgetting reconciliation."""
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from phimemory9.living_contract import Context, LocalIdentity, MemoryToken, canonical
from phimemory9.living_store import LivingStore


class ForgetRecoveryR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.path, self.guard = root/"main.db", root/"guard.db"
        self.owner = LocalIdentity("fixture:owner", b"o"*32)
        self.reader = LocalIdentity("fixture:reader", b"r"*32)
        self.store = LivingStore.create(self.path, self.guard, self.owner)
        self.addCleanup(lambda: self.store.close())
        self.store.register_identity(self.reader)
        self.policy = self.store.set_policy(1)
        self.context = Context("demo", "demo-app", "research", ("research",))
        self.add("target")
        self.add("child", parents=("fixture:target",))
        self.add("other")
        for gid in ("fixture:target", "fixture:other"):
            self.store.grant(gid, self.reader, self.context, "express",
                             now=100, expires_at=200)
        self.mid = self.store._gene("fixture:target")["memory_id"]

    def add(self, name, parents=()):
        gid = "fixture:"+name
        metadata = dict(gene_id=gid, project="demo", privacy="public",
                        consent="ask_first", repair="clean", confidence="high",
                        claim="fact", source_refs=["fixture:source"],
                        activate=["research"], suppress=[])
        self.store.add_gene(gid, "invented "+name, metadata,
                            MemoryToken("fixture:token:"+name, "synthetic",
                                        "fixture:source", name, "fixture:v1"),
                            parents=parents)

    def forget(self):
        self.store.repair("fixture:target", "forget")

    def reopen(self):
        self.store.close()
        self.store = LivingStore.open(self.path, self.guard, self.owner)

    def state(self):
        return self.store.reconstruct()

    def dump(self):
        return tuple(self.store.db.iterdump())

    def events(self):
        return self.store.engine.events(self.mid)

    def test_reconciliation_is_logically_and_write_count_idempotent(self):
        self.forget()
        before = self.dump()
        changes = self.store.db.total_changes
        for _ in range(3):
            self.store.reconcile_guard()
            self.assertEqual(self.dump(), before)
            self.assertEqual(self.store.db.total_changes, changes)

    def test_repeated_cold_open_preserves_event_identity_and_timestamp(self):
        self.forget()
        before, event = self.dump(), self.events()
        self.assertEqual(len(event), 1)
        self.assertEqual(event[0]["stage"], "DEATH")
        for _ in range(3):
            self.reopen()
            self.assertEqual(self.events(), event)
            self.assertEqual(self.dump(), before)
            self.assertTrue(self.state()["engine_integrity"])

    def test_clean_marker_does_not_skip_residual_copy_or_event_cleanup(self):
        self.forget()
        event = self.events()
        gid = "fixture:target"
        with self.store.engine.transaction():
            self.store.db.execute("INSERT INTO lm_copies VALUES (?,?,?,?)",
                                  ("fixture:residue", gid, "cache", "invented residue"))
            body = canonical({"gene": gid, "detail": "invented residue"}).decode("ascii")
            self.store.db.execute("INSERT INTO lm_events VALUES (?,?,?)",
                                  ("fixture:residual-event", "repair", body))
        self.store.reconcile_guard()
        self.assertEqual(self.events(), event)
        self.assertNotIn("invented residue", "\n".join(self.dump()))
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM lm_copies").fetchone()[0], 0)
        before = self.dump()
        self.store.reconcile_guard()
        self.assertEqual(self.dump(), before)

    def test_tombstone_with_restored_content_is_rescrubbed(self):
        self.forget()
        with self.store.engine.transaction():
            self.store.db.execute("UPDATE memories SET content=?,source_ref=? WHERE id=?",
                                  ("invented restored payload", "fixture:old-source", self.mid))
        self.store.reconcile_guard()
        self.assertNotIn("invented restored payload", "\n".join(self.dump()))
        self.assertEqual(len(self.events()), 1)
        self.assertTrue(self.state()["engine_integrity"])
        before = self.dump()
        self.store.reconcile_guard()
        self.assertEqual(self.dump(), before)

    def test_extra_core_event_is_removed(self):
        self.forget()
        with self.store.engine.transaction():
            self.store.engine._event(self.mid, "DEATH", reason="invented stale event")
        self.store.reconcile_guard()
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.events()[0]["detail"], {"reason": "fixture logical deletion"})
        before = self.dump()
        self.store.reconcile_guard()
        self.assertEqual(self.dump(), before)

    def test_stale_main_restore_rescrubs_then_stabilizes(self):
        snapshot = Path(self.tmp.name)/"before.db"
        with sqlite3.connect(snapshot) as backup:
            self.store.db.backup(backup)
        self.forget()
        self.store.close()
        shutil.copyfile(snapshot, self.path)
        self.store = LivingStore.open(self.path, self.guard, self.owner)
        self.assertEqual(self.store._gene("fixture:target")["state"], "deleted")
        self.assertEqual(self.store._gene("fixture:child")["state"], "deleted")
        self.assertNotIn("invented target", "\n".join(self.dump()))
        before = self.dump()
        self.reopen()
        self.assertEqual(self.dump(), before)
        self.assertTrue(self.state()["engine_integrity"])

    def test_unrelated_memory_and_authorization_preserved(self):
        other = self.store._gene("fixture:other")["memory_id"]
        original = self.store.engine.memory(other), self.store.engine.events(other)
        self.forget()
        self.reopen()
        self.assertEqual((self.store.engine.memory(other), self.store.engine.events(other)), original)
        report = self.store.evaluate(["fixture:target", "fixture:other"], self.reader,
                                     self.context, "express", now=150, expected_policy=self.policy)
        self.assertEqual(report.admitted_ids, ("fixture:other",))
        self.assertEqual(report.held, (("fixture:target", "lifecycle_hold"),))

    def test_public_repeat_forget_keeps_existing_refusal_contract(self):
        self.forget()
        before = self.dump()
        with self.assertRaisesRegex(ValueError, "already deleted"):
            self.forget()
        self.assertEqual(self.dump(), before)


if __name__ == "__main__":
    unittest.main()
