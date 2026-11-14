"""R0.4 tests: explicit approvals, rollback, privacy and replay safety."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phimemory9 import MemoryEngine, MemoryError9
from phimemory9.governance import (
    SCHEMA, apply, approval_history, export_digest, fingerprint, load_plan,
    redact_export, review, save_export, validate_plan,
)


class GovernedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbpath = Path(self.tmp.name) / "memory.sqlite3"
        self.engine = MemoryEngine(self.dbpath)
        self.blob = self.engine.create_blob("root")
        self.first = self.engine.enter(self.blob, "Original measurement", "synthetic:one")

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def plan(self, action="loop", **kwargs):
        return {
            "schema": SCHEMA, "action": action,
            "reason": "Human reviewed this experiment",
            **(dict(memory_id=self.first, route="inward") if action == "loop" else {}),
            **kwargs,
        }

    def test_review_is_read_only_except_schema_creation(self):
        p = self.plan()
        original = len(self.engine.events(self.first))
        result = review(self.engine, p)
        self.assertEqual(result["sha256"], fingerprint(p))
        self.assertEqual(len(self.engine.events(self.first)), original)
        self.assertFalse(result["previously_applied"])

    def test_mismatched_digest_never_mutates(self):
        p = self.plan()
        with self.assertRaises(MemoryError9):
            apply(self.engine, p, "0" * 64)
        self.assertEqual(approval_history(self.engine), [])
        self.assertEqual(len(self.engine.events(self.first)), 2)

    def test_actual_loop_is_atomic_and_replay_protected(self):
        p = self.plan()
        result = apply(self.engine, p, fingerprint(p))
        child = result["result"]["child_memory_id"]
        self.assertEqual(self.engine.lineage(child), [self.first, child])
        self.assertEqual(len(approval_history(self.engine)), 1)
        self.assertEqual(review(self.engine, p)["previously_applied"], True)
        with self.assertRaises(MemoryError9):
            apply(self.engine, p, fingerprint(p))
        self.assertEqual(len(approval_history(self.engine)), 1)
        self.assertEqual(self.engine.verify()["memories"], 2)

    def test_nested_error_rolls_back_approval_and_memory(self):
        p = self.plan(route="outward")  # Root cannot route outward.
        with self.assertRaises(MemoryError9):
            apply(self.engine, p, fingerprint(p))
        self.assertEqual(len(approval_history(self.engine)), 0)
        self.assertEqual(len(self.engine.events(self.first)), 2)
        self.assertEqual(self.engine.verify()["memories"], 1)

    def test_enter_death_restore_renew_and_transfer(self):
        enter = self.plan("enter", blob_id=self.blob, content="New interpretation",
                          source_ref="synthetic:two")
        born = apply(self.engine, enter, fingerprint(enter))["result"]["memory_id"]
        death = self.plan("death", memory_id=born)
        apply(self.engine, death, fingerprint(death))
        self.assertEqual(self.engine.memory(born)["status"], "retired")
        restore = self.plan("restore", memory_id=born)
        apply(self.engine, restore, fingerprint(restore))
        renewal = self.plan("renew", memory_id=born, content="Revised interpretation")
        newer = apply(self.engine, renewal, fingerprint(renewal))["result"]["memory_id"]
        nested = self.engine.create_blob("child", self.blob)
        transfer = self.plan("transfer", memory_id=newer, target_blob_id=nested)
        moved = apply(self.engine, transfer, fingerprint(transfer))["result"]["memory_id"]
        self.assertEqual(len(self.engine.lineage(moved)), 3)
        self.assertTrue(self.engine.verify()["ok"])

    def test_strict_json_input_and_duplicates(self):
        p = self.plan()
        file = Path(self.tmp.name) / "p.json"
        file.write_text(json.dumps(p), encoding="utf-8")
        self.assertEqual(load_plan(file), p)
        file.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
        with self.assertRaises(MemoryError9):
            load_plan(file)
        with self.assertRaises(MemoryError9):
            validate_plan({**p, "extra": "surprise"})
        with self.assertRaises(MemoryError9):
            validate_plan(self.plan(route="lateral"))
        with self.assertRaises(MemoryError9):
            validate_plan(self.plan(route="seed", target_blob_id=self.blob))

    def test_metadata_only_export_redacts_content_and_source(self):
        packet = redact_export(self.engine, self.first)
        data = json.dumps(packet)
        self.assertIn("content_sha256", data)
        self.assertNotIn("Original measurement", data)
        self.assertNotIn("synthetic:one", data)
        self.assertEqual(packet["mode"], "metadata_only")
        output = Path(self.tmp.name) / "meta.json"
        save_export(self.engine, self.first, output)
        self.assertTrue(output.is_file())
        with self.assertRaises(FileExistsError):
            save_export(self.engine, self.first, output)

    def test_full_export_requires_digest_and_never_overwrites(self):
        output = Path(self.tmp.name) / "full.json"
        with self.assertRaises(MemoryError9):
            save_export(self.engine, self.first, output, include_content=True)
        with self.assertRaises(MemoryError9):
            save_export(self.engine, self.first, output, include_content=True,
                        approved_sha256="0"*64)
        sha = export_digest(self.engine, self.first)
        save_export(self.engine, self.first, output, include_content=True,
                    approved_sha256=sha)
        self.assertIn("Original measurement", output.read_text())
        with self.assertRaises(FileExistsError):
            save_export(self.engine, self.first, output, include_content=True,
                        approved_sha256=sha)

    def test_core_nested_transactions_roll_back_as_one(self):
        with self.assertRaises(RuntimeError):
            with self.engine.transaction():
                memory_id = self.engine.enter(self.blob, "Never persist this child")
                self.engine.loop(memory_id, "inward")
                raise RuntimeError("Deliberate abort")
        self.assertEqual(self.engine.verify()["memories"], 1)
        self.assertEqual(self.engine.verify()["blobs"], 1)

    def test_approved_plan_survives_disk_reopen(self):
        plan = self.plan()
        apply(self.engine, plan, fingerprint(plan))
        self.engine.close()
        self.engine = MemoryEngine(self.dbpath)
        self.assertTrue(review(self.engine, plan)["previously_applied"])
        self.assertEqual(len(approval_history(self.engine)), 1)


if __name__ == "__main__":
    unittest.main()
