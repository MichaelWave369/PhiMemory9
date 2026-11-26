"""Disposable fixture tests for source-identity reentry after forgetting."""
from dataclasses import replace
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from phimemory9.living_contract import LocalIdentity, MemoryToken
from phimemory9.living_store import LivingStore


class SourceReentryR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.path, self.guard = root/"main.db", root/"guard.db"
        self.owner = LocalIdentity("fixture:owner", b"o"*32)
        self.store = LivingStore.create(self.path, self.guard, self.owner)
        self.addCleanup(lambda: self.store.close())
        self.token = MemoryToken("fixture:original-token", "synthetic",
                                 "fixture:source", "native-row-1", "fixture:v1")
        self.add("original", self.token)

    def add(self, name, token, parents=()):
        gid = "fixture:"+name
        metadata = dict(gene_id=gid, project="demo", privacy="public",
                        consent="ask_first", repair="clean", confidence="high",
                        claim="fact", source_refs=["fixture:source"],
                        activate=["research"], suppress=[])
        return self.store.add_gene(gid, "invented "+name, metadata, token,
                                   parents=parents)

    def forget(self):
        self.store.repair("fixture:original", "forget")

    def reopen(self):
        self.store.close()
        self.store = LivingStore.open(self.path, self.guard, self.owner)

    def denied(self, token):
        before = self.store.reconstruct()
        with self.assertRaisesRegex(PermissionError, "forgotten native source"):
            self.add("reimport", token)
        self.assertEqual(self.store.reconstruct(), before)

    def test_new_gene_and_token_id_do_not_bypass_forget(self):
        self.forget()
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM lm_tokens").fetchone()[0], 0)
        self.denied(self.token)
        self.denied(replace(self.token, token_id="fixture:new-token"))

    def test_revision_change_does_not_bypass_forget(self):
        self.forget()
        self.denied(replace(self.token, token_id="fixture:updated-token",
                            source_revision="fixture:v2"))
        self.reopen()
        self.denied(replace(self.token, token_id="fixture:third-token",
                            source_revision="fixture:v3"))

    def test_different_source_scope_is_not_blocked(self):
        self.forget()
        for name, changes in [
            ("different-native", {"native_id": "native-row-2"}),
            ("different-instance", {"source_instance": "fixture:other"}),
            ("different-system", {"source_system": "other-system"}),
        ]:
            token = replace(self.token, token_id="fixture:"+name, **changes)
            self.assertEqual(self.add(name, token).state, "active")

    def test_shared_existing_gene_is_not_silently_deleted(self):
        self.add("sibling", self.token)
        self.forget()
        self.assertEqual(self.store._gene("fixture:sibling")["state"], "active")
        self.denied(replace(self.token, token_id="fixture:alias"))

    def test_descendant_source_is_guarded(self):
        child = replace(self.token, token_id="fixture:child-token", native_id="native-child")
        self.add("child", child, parents=("fixture:original",))
        self.forget()
        self.assertEqual(self.store._gene("fixture:child")["state"], "deleted")
        self.denied(replace(child, token_id="fixture:child-alias"))

    def test_guard_survives_main_only_restore(self):
        snapshot = Path(self.tmp.name)/"before.db"
        with sqlite3.connect(snapshot) as backup:
            self.store.db.backup(backup)
        self.forget()
        self.store.close()
        shutil.copyfile(snapshot, self.path)
        self.store = LivingStore.open(self.path, self.guard, self.owner)
        self.assertEqual(self.store._gene("fixture:original")["state"], "deleted")
        self.denied(replace(self.token, token_id="fixture:after-restore"))

    def test_forget_transaction_rolls_back_source_guard(self):
        with self.store.engine.transaction():
            self.store.db.execute("""CREATE TRIGGER abort_forget BEFORE UPDATE ON lm_genes
                WHEN NEW.state='deleted' BEGIN SELECT RAISE(ABORT, 'fixture interruption'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.forget()
        self.assertEqual(self.store._gene("fixture:original")["state"], "active")
        self.assertIsNone(self.store.block_action("fixture:original"))
        self.assertEqual(self.add("after-abort", replace(self.token,
                         token_id="fixture:after-abort")).state, "active")

    def test_opaque_guard_does_not_store_raw_source_identity(self):
        self.forget()
        rows = self.store.db.execute("SELECT opaque_id,action FROM lm_guard.blocks").fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(len(row[0]) == 64 and row[1] == "forget" for row in rows))
        self.assertNotIn(self.token.native_id, repr([tuple(row) for row in rows]))


if __name__ == "__main__":
    unittest.main()
