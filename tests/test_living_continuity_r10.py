"""Exercise paired rollback against a separately retained fixture commitment."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from phimemory9.living_contract import Context, LocalIdentity, MemoryToken
from phimemory9.living_continuity import snapshot, compare
from phimemory9.living_store import LivingStore

OWNER = LocalIdentity("fixture:owner", b"o"*32)
READER = LocalIdentity("fixture:reader", b"r"*32)
CTX = Context("demo", "demo-app", "research", ("research",))
GID = "fixture:gene"


class ContinuityR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.main, self.guard = self.root/"main.db", self.root/"guard.db"
        with LivingStore.create(self.main, self.guard, OWNER) as store:
            store.register_identity(READER)
            self.policy = store.set_policy(1)
            metadata = dict(gene_id=GID, project="demo", privacy="public",
                            consent="ask_first", repair="clean", confidence="high",
                            claim="fact", source_refs=["fixture:source"],
                            activate=["research"], suppress=[])
            store.add_gene(GID, "invented source payload", metadata,
                           MemoryToken("fixture:token", "synthetic",
                                       "fixture:source", "gene", "fixture:v1"))
            self.consent = store.grant(GID, READER, CTX, "express",
                                       now=100, expires_at=200).consent_id
            self.before = snapshot(store)
        self.backup_main, self.backup_guard = self.root/"old-main.db", self.root/"old-guard.db"
        shutil.copyfile(self.main, self.backup_main)
        shutil.copyfile(self.guard, self.backup_guard)

    def read(self):
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            return snapshot(store)

    def withdraw(self):
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            store.withdraw_consent(self.consent)
            return snapshot(store)

    def restore_pair(self):
        shutil.copyfile(self.backup_main, self.main)
        shutil.copyfile(self.backup_guard, self.guard)

    def test_snapshot_stable_across_clean_reopen(self):
        self.assertEqual(self.before, self.read())
        self.assertEqual(self.before, self.read())
        self.assertNotIn("invented source payload", json.dumps(self.before))
        self.assertNotIn(GID, json.dumps(self.before))
        self.assertEqual(self.before["authority"], "NONE")

    def test_guard_and_main_changes_bound(self):
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            store.set_policy(2)
            guard_changed = snapshot(store)
            self.assertNotEqual(guard_changed, self.before)
            store.add_copy(GID, "cache", "invented cache")
            self.assertNotEqual(snapshot(store), guard_changed)

    def test_both_file_rollback_requires_external_pin(self):
        after = self.withdraw()
        self.assertNotEqual(after, self.before)
        self.assertTrue(compare(after, after["witness_sha256"])["matches"])
        self.restore_pair()
        self.assertEqual(self.read(), self.before)
        # Counterexample: local recovery alone cannot know about the withdrawal.
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            self.assertEqual(store.evaluate([GID], READER, CTX, "express",
                                            now=150, expected_policy=self.policy).admitted_ids,
                             (GID,))
        # Read the exact rolled-back pair again without the new expression event.
        self.restore_pair()
        result = compare(self.read(), after["witness_sha256"])
        self.assertEqual(result, {"matches": False, "authority": "NONE", "status": "HELD"})

    def test_main_only_restore_cannot_match_old_pair(self):
        after = self.withdraw()
        shutil.copyfile(self.backup_main, self.main)
        self.assertEqual(self.read(), after)
        self.assertFalse(compare(self.read(), self.before["witness_sha256"])["matches"])

    def test_logical_row_order_does_not_change_snapshot(self):
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            before = snapshot(store)
            # VACUUM changes physical layout, not the logical committed rows.
            store.db.execute("VACUUM main")
            self.assertEqual(snapshot(store), before)

    def test_compare_refuses_malformed_and_never_grants_authority(self):
        for bad in ("", "A"*64, None, 1):
            with self.assertRaises(ValueError):
                compare(self.before, bad)
        with self.assertRaises(ValueError):
            compare(dict(self.before, authority="EXECUTE"), self.before["witness_sha256"])
        self.assertEqual(compare(self.before, self.before["witness_sha256"])["status"], "HELD")

    @unittest.skipUnless(os.environ.get("LIVING_NATIVE_POCKETMESH"),
                         "explicit native PocketMesh checkout required")
    def test_native_pocketmesh_signed_anchor_on_real_snapshots(self):
        after = self.withdraw()
        self.restore_pair()
        old = self.read()
        script = Path(__file__).resolve().parents[1]/"scripts/living_native_continuity.mjs"
        result = subprocess.run(
            ["node", str(script), os.environ["LIVING_NATIVE_POCKETMESH"],
             old["witness_sha256"], after["witness_sha256"]],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+"\n"+result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["checks_passed"], 9)
        self.assertEqual(report["authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
