import json
import subprocess
import sys
import unittest

from phimemory9.genomememory_integration import report, scenario, SCENARIOS


class IntegrationTests(unittest.TestCase):
    def test_all_fixed_scenarios_and_live_gate(self):
        result = report()
        self.assertTrue(result["experimental_pass"])
        self.assertFalse(result["live_ready"])
        self.assertEqual(result["authority"], "NONE")
        self.assertEqual(len(result["readiness_blockers"]), 7)
        self.assertEqual([c["name"] for c in result["scenarios"]], list(SCENARIOS))
        for case in result["scenarios"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(len(case["checks"]), 8)
                self.assertTrue(all(case["checks"].values()))
                self.assertEqual(case["held_source_count"], 2)
                self.assertEqual(case["authority"], "NONE")

    def test_baseline_and_contradiction(self):
        base = scenario("baseline")
        self.assertEqual(base["preview_count"], 7)
        self.assertEqual(base["learning_status"], "AUDIT_MATCHED")
        self.assertEqual((base["test_matches"], base["test_count"]), (2, 2))
        self.assertTrue(base["packet_compatible"])
        bad = scenario("contradiction")
        self.assertEqual(bad["learning_status"], "TRAIN_CONTRADICTION")
        self.assertIsNone(bad["test_matches"])
        # A compatible envelope can describe a failed experiment.
        self.assertTrue(bad["packet_compatible"])
        self.assertEqual(bad["authority"], "NONE")

    def test_withdrawal_changes_preview_and_learning(self):
        base = scenario("contradiction")
        held = scenario("withdrawal")
        self.assertEqual(held["preview_count"], 4)
        self.assertEqual(held["excluded_count"], 3)
        self.assertEqual(held["learning_status"], "AUDIT_MATCHED")
        self.assertEqual((held["test_matches"], held["test_count"]), (1, 1))
        self.assertIsNotNone(held["receipts"]["hold"])
        for key in ("integrity", "learning", "packet"):
            self.assertNotEqual(base["receipts"][key], held["receipts"][key])

    def test_insufficient_support_abstains(self):
        case = scenario("insufficient")
        self.assertEqual(case["preview_count"], 5)
        self.assertEqual(case["excluded_count"], 1)
        self.assertEqual(case["learning_status"], "UNDERDETERMINED")
        self.assertIsNone(case["test_matches"])

    def test_negative_envelope_controls(self):
        for name, failures in [
            ("expired", {"time_window"}),
            ("wrong_destination", {"destination"}),
            ("tampered", {"integrity", "policy_reference"}),
        ]:
            with self.subTest(name=name):
                case = scenario(name)
                self.assertFalse(case["packet_compatible"])
                self.assertEqual({k for k,v in case["packet_checks"].items() if not v}, failures)
                self.assertEqual(case["learning_status"], "AUDIT_MATCHED")

    def test_determinism_and_distinct_receipts(self):
        first = report()
        self.assertEqual(first, report())
        self.assertEqual(len({c["scenario_sha256"] for c in first["scenarios"]}), 7)
        self.assertEqual(len(first["report_sha256"]), 64)
        with self.assertRaises(ValueError):
            scenario("live")

    def test_cli_report_and_intentionally_blocked_gate(self):
        for mode, code in (("report", 0), ("gate", 3)):
            result = subprocess.run(
                [sys.executable, "-m", "phimemory9.genomememory_integration", mode],
                capture_output=True, text=True, check=False, timeout=30)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertEqual(json.loads(result.stdout), report())


if __name__ == "__main__":
    unittest.main()
