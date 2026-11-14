"""R0.5 frozen synthetic comparison: deterministic and transparent receipts."""
import json
import unittest

from phimemory9.benchmark_r05 import (
    HISTORY_CASES, CURRENT_CASES, NEGATIVES, METHODS, THRESHOLDS, run_heldout_r05,
)


class R05BenchmarkTests(unittest.TestCase):
    def test_manifest_reproducible_across_new_memory_uuids(self):
        left, right = run_heldout_r05(), run_heldout_r05()
        self.assertEqual(left, right)
        self.assertEqual(left["query_count"], 36)
        self.assertEqual(left["active_candidates"], 24)
        self.assertEqual(left["historical_ancestor_records"], 12)
        self.assertEqual(len(left["manifest_sha256"]), 64)

    def test_every_miss_and_false_accept_is_reported(self):
        output = run_heldout_r05()
        self.assertEqual(len(output["queries"]), len(HISTORY_CASES) + len(CURRENT_CASES) + len(NEGATIVES))
        self.assertEqual(set(output["positive"]), set(METHODS))
        self.assertEqual(set(output["negative_controls"]), set(METHODS))
        for method in METHODS:
            self.assertTrue(0 < THRESHOLDS[method] <= 1)
            false_accepts = sum(
                not item["results"][method]["abstained"]
                for item in output["queries"] if item["group"] == "negative"
            )
            self.assertEqual(output["negative_controls"][method]["false_accept_count"], false_accepts)
            for group in ("historical_wording", "current_wording"):
                metrics = output["positive"][method][group]
                self.assertTrue(all(0 <= value <= 1 for value in metrics.values()))

    def test_no_claim_of_production_performance(self):
        output = run_heldout_r05()
        self.assertIn("not a neural embedding", output["limitations"].lower())
        self.assertIn("not an independently collected holdout", output["limitations"].lower())
        self.assertTrue(all("top_match" in row["results"]["lexical"] for row in output["queries"]))


if __name__ == "__main__":
    unittest.main()
