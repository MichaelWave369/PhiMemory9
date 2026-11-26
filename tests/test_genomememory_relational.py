import copy
import unittest

from phimemory9.genomememory_relational import experiment, FAMILY, P
from phimemory9.genomememory_retention import SCHEMA, KINDS


def fixture():
    nodes = [dict(node_id="fixture:source", kind="memory", depends_on=[])]
    rows = []
    for x, split in enumerate(["train", "train", "train", "audit", "audit", "test", "test"]):
        nid = f"fixture:o{x}"
        nodes.append(dict(node_id=nid, kind="descendant",
                          depends_on=["fixture:source"] if x in (2, 4, 6) else []))
        if not nodes[-1]["depends_on"]:
            nodes[-1]["kind"] = "memory"
        rows.append(dict(node_id=nid, split=split, x=x, y=(7*x+4)%P))
    inventory = dict(schema=SCHEMA, synthetic=True, fixture_id="fixture:learning",
                     coverage={k:"declared_complete" for k in KINDS}, nodes=nodes)
    return inventory, rows


class RelationalTests(unittest.TestCase):
    def test_known_rule_and_heldout(self):
        inventory, rows = fixture()
        result = experiment(inventory, rows)
        self.assertEqual(result["family_size"], 930)
        self.assertEqual(result["rule"], [7, 4])
        self.assertEqual(result["status"], "AUDIT_MATCHED")
        self.assertEqual(result["audit_matches"], 2)
        self.assertEqual(result["test_matches"], 2)
        self.assertFalse(result["certified"])
        self.assertFalse(result["eligible"])
        self.assertEqual(result["authority"], "NONE")

    def test_withdrawal_recomputes_and_excludes_all_splits(self):
        inventory, rows = fixture()
        rows[2]["y"] = (rows[2]["y"]+1)%P
        self.assertEqual(experiment(inventory, rows)["status"], "TRAIN_CONTRADICTION")
        result = experiment(inventory, rows, hold_target="fixture:source")
        self.assertEqual(result["excluded_ids"], ["fixture:o2", "fixture:o4", "fixture:o6"])
        self.assertEqual(result["rule"], [7, 4])
        self.assertEqual(result["audit_count"], 1)
        self.assertEqual(result["test_count"], 1)
        self.assertEqual(result["test_matches"], 1)
        self.assertTrue(result["hold_plan_sha256"])
        self.assertEqual(sum(map(len,result["admitted_ids"].values())), 4)

    def test_loss_of_support_abstains(self):
        inventory, rows = fixture()
        result = experiment(inventory, rows[:2]+rows[3:], hold_target="fixture:o0")
        self.assertEqual(result["status"], "UNDERDETERMINED")
        self.assertEqual(result["candidate_count"], 30)
        self.assertIsNone(result["rule"])
        self.assertIsNone(result["test_matches"])

    def test_audit_does_not_fit_or_promote(self):
        inventory, rows = fixture()
        rows[3]["y"] = (rows[3]["y"]+1)%P
        report = experiment(inventory, rows)
        self.assertEqual(report["status"], "AUDIT_REJECTED")
        self.assertEqual(report["candidate_count"], 1)
        self.assertIsNone(report["rule"])
        self.assertIsNone(report["test_matches"])
        report = experiment(inventory, rows[:3]+rows[5:])
        self.assertEqual(report["status"], "AUDIT_MISSING")
        self.assertIsNone(report["rule"])

    def test_test_outcome_does_not_select_rule(self):
        inventory, rows = fixture()
        initial = experiment(inventory, rows)
        rows[5]["y"] = (rows[5]["y"]+1)%P
        result = experiment(inventory, rows)
        self.assertEqual(result["rule"], initial["rule"])
        self.assertEqual(result["status"], initial["status"])
        self.assertEqual(result["test_matches"], 1)
        self.assertNotEqual(result["report_sha256"], initial["report_sha256"])

    def test_exhaustive_family_recovery(self):
        inventory, rows = fixture()
        for a, b in FAMILY:
            data = [dict(r, y=(a*r["x"]+b)%P) for r in rows]
            result = experiment(inventory, data)
            self.assertEqual(result["rule"], [a,b])
            self.assertEqual(result["test_matches"], 2)

    def test_order_and_coverage(self):
        inventory, rows = fixture()
        original = copy.deepcopy(inventory), copy.deepcopy(rows)
        baseline = experiment(inventory, rows)
        altered = copy.deepcopy(inventory)
        altered["nodes"].reverse()
        self.assertEqual(baseline, experiment(altered, rows[::-1]))
        self.assertEqual((inventory, rows), original)
        altered["coverage"]["backup"] = "unknown"
        result = experiment(altered, rows)
        self.assertEqual(result["coverage_gaps"], ["backup"])
        self.assertFalse(result["certified"])

    def test_invalid_input_fails_closed(self):
        inventory, rows = fixture()
        for change in [
            dict(rows[0], x=True), dict(rows[0], y=31),
            dict(rows[0], split="validation"), dict(rows[0], x=1),
            dict(rows[0], node_id="fixture:missing"), dict(rows[0], payload="no"),
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                experiment(inventory, [change]+rows[1:])
        with self.assertRaises(ValueError):
            experiment(inventory, rows, hold_target="fixture:missing")


if __name__ == "__main__":
    unittest.main()
