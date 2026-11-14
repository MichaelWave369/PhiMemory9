"""Contract and regression tests; synthetic data only."""
import tempfile
import unittest
from pathlib import Path

from phimemory9 import MemoryEngine, MemoryError9, STAGES
from phimemory9.core import MAX_DEPTH, MAX_LOOPS_PER_MEMORY


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()
        self.root = self.engine.create_blob("root")
        self.first = self.engine.enter(self.root, "Initial observation", "fixture:A")

    def tearDown(self):
        self.engine.close()

    def test_nine_operations_are_named(self):
        self.assertEqual(len(STAGES), 9)
        self.assertEqual(STAGES[-1], "LOOP")

    def test_birth_with_provenance_and_duplicate_rejection(self):
        original = self.engine.memory(self.first)
        self.assertEqual(original["source_ref"], "fixture:A")
        self.assertEqual([x["stage"] for x in self.engine.events(self.first)],
                         ["ENTER", "BIRTH"])
        with self.assertRaises(MemoryError9):
            self.engine.enter(self.root, "Initial observation")

    def test_death_restoration_and_immutable_text(self):
        self.engine.death(self.first, "New evidence conflicts")
        self.assertEqual(self.engine.memory(self.first)["status"], "retired")
        self.assertEqual(self.engine.memory(self.first)["content"], "Initial observation")
        self.engine.restore(self.first, "Independent review supports source")
        self.assertEqual(self.engine.memory(self.first)["status"], "active")
        self.assertIn("DEATH", [x["stage"] for x in self.engine.events(self.first)])
        self.assertIn("RESTORE", [x["stage"] for x in self.engine.events(self.first)])

    def test_renew_preserves_ancestry_and_retires_original(self):
        child = self.engine.renew(self.first, "Revised observation", "New evidence")
        self.assertEqual(self.engine.memory(self.first)["status"], "retired")
        self.assertEqual(self.engine.memory(child)["status"], "active")
        self.assertEqual(self.engine.lineage(child), [self.first, child])
        self.assertEqual(self.engine.memory(self.first)["content"], "Initial observation")

    def test_transfer_rebirth_and_liberation(self):
        nested = self.engine.create_blob("nested", self.root)
        transferred = self.engine.transfer(self.first, nested)
        reborn = self.engine.rebirth(transferred, "Different interpretation", nested)
        self.assertEqual(self.engine.lineage(reborn),
                         [self.first, transferred, reborn])
        packet = self.engine.liberation(reborn)
        self.assertEqual(packet["schema"], "phi-memory9/v0.1")
        self.assertEqual(packet["memory"]["source_ref"], "fixture:A")
        self.assertEqual(packet["lineage"][0]["id"], self.first)
        self.assertEqual(packet["events"][-1]["stage"], "LIBERATION")

    def test_loop_default_holds_and_inward_routes(self):
        held = self.engine.loop(self.first)
        self.assertEqual(held["route"], "hold")
        self.assertIsNone(held["child_memory_id"])
        inner = self.engine.loop(self.first, "inward")
        child = inner["child_memory_id"]
        self.assertEqual(self.engine.lineage(child), [self.first, child])
        self.assertEqual(self.engine.depth(inner["target_blob_id"]), 1)

    def test_loop_outward_and_lateral(self):
        nested = self.engine.create_blob("nested", self.root)
        inner = self.engine.transfer(self.first, nested)
        outward = self.engine.loop(inner, "outward")
        self.assertEqual(outward["target_blob_id"], self.root)
        # Target root already has identical content: duplicate transfers are refused.
        self.assertIsNotNone(outward["child_memory_id"])

    def test_reject_duplicate_in_lateral_target(self):
        target = self.engine.create_blob("target")
        first_copy = self.engine.loop(self.first, "lateral", target)
        self.assertIsNotNone(first_copy["child_memory_id"])
        with self.assertRaises(MemoryError9):
            self.engine.loop(self.first, "lateral", target)

    def test_root_cannot_route_outward(self):
        with self.assertRaises(MemoryError9):
            self.engine.loop(self.first, "outward")

    def test_depth_limit(self):
        current = self.root
        for depth in range(MAX_DEPTH):
            current = self.engine.create_blob(f"level-{depth}", current)
        with self.assertRaises(MemoryError9):
            self.engine.create_blob("too deep", current)

    def test_loop_budget(self):
        for _ in range(MAX_LOOPS_PER_MEMORY):
            self.engine.loop(self.first)
        with self.assertRaises(MemoryError9):
            self.engine.loop(self.first)

    def test_failed_renew_is_atomic(self):
        with self.assertRaises(MemoryError9):
            self.engine.renew(self.first, "Initial observation", "same content")
        self.assertEqual(self.engine.memory(self.first)["status"], "active")
        self.assertEqual(len(self.engine.events(self.first)), 2)

    def test_verify(self):
        self.assertTrue(self.engine.verify()["ok"])
        self.assertEqual(self.engine.verify()["memories"], 1)


class PersistenceTests(unittest.TestCase):
    def test_disk_reopens(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.sqlite3"
            with MemoryEngine(path) as db:
                root = db.create_blob("root")
                mid = db.enter(root, "Never silently delete.", "fixture:persist")
            with MemoryEngine(path) as db:
                self.assertEqual(db.memory(mid)["content"], "Never silently delete.")
                self.assertTrue(db.verify()["ok"])


if __name__ == "__main__":
    unittest.main()
