"""R0.2 deterministic retrieval controls and synthetic comparative report."""
import unittest

from phimemory9 import MemoryEngine
from phimemory9.retrieval import search, benchmark_fixture, tokens


class RetrievalTests(unittest.TestCase):
    def test_tokenizer_is_case_independent(self):
        self.assertEqual(tokens("The ORCHARD, sensor!"), frozenset({"orchard", "sensor"}))

    def test_baseline_no_false_match(self):
        with MemoryEngine() as engine:
            blob = engine.create_blob("test")
            engine.enter(blob, "Crimson river current")
            self.assertEqual(search(engine, "mountain basalt", method="lexical"), [])
            self.assertEqual(search(engine, "mountain basalt", method="ancestry"), [])

    def test_retired_ancestor_is_not_returned_as_active_result(self):
        with MemoryEngine() as engine:
            blob = engine.create_blob("test")
            original = engine.enter(blob, "Copper antenna received lunar beacon")
            updated = engine.renew(
                original, "Current record alpha", "Updated interpretation"
            )
            self.assertEqual(search(engine, "copper antenna lunar", method="lexical"), [])
            found = search(engine, "copper antenna lunar", method="ancestry")
            self.assertEqual(found[0]["id"], updated)
            self.assertGreater(found[0]["ancestry_bonus"], 0)

    def test_other_unchanged_memory_can_still_win(self):
        with MemoryEngine() as engine:
            blob = engine.create_blob("test")
            original = engine.enter(blob, "Obsidian ridge fault observation")
            engine.renew(original, "New record", "Update")
            other = engine.enter(blob, "Obsidian ridge fault observation confirmed")
            found = search(engine, "obsidian ridge fault", method="ancestry")
            self.assertEqual(found[0]["id"], other)

    def test_invalid_method_and_k(self):
        with MemoryEngine() as engine:
            with self.assertRaises(ValueError):
                search(engine, "x", method="semantic")
            with self.assertRaises(ValueError):
                search(engine, "x", k=0)

    def test_benchmark_is_repeatable_and_discloses_limits(self):
        first = benchmark_fixture()
        second = benchmark_fixture()
        self.assertEqual(first, second)
        self.assertEqual(first["query_count"], 6)
        self.assertIn("synthetic", first["fixture"])
        self.assertEqual(set(first["methods"]), {"lexical", "ancestry"})
        for method in first["methods"].values():
            self.assertTrue(0 <= method["hit_at_1"] <= 1)
            self.assertTrue(0 <= method["hit_at_3"] <= 1)
            self.assertTrue(0 <= method["mrr_at_3"] <= 1)
        self.assertTrue(all(row["expected"] for row in first["queries"]))


if __name__ == "__main__":
    unittest.main()
