import copy
import unittest

from phimemory9.genomememory_retention import KINDS, SCHEMA, plan


def node(name, kind, *parents):
    return dict(node_id="fixture:"+name, kind=kind,
                depends_on=["fixture:"+p for p in parents])


def fixture():
    return dict(schema=SCHEMA, synthetic=True, fixture_id="fixture:retention",
                coverage={k: "declared_complete" for k in KINDS}, nodes=[
                    node("root", "memory"),
                    node("other", "memory"),
                    node("child", "descendant", "root"),
                    node("merge", "descendant", "child", "other"),
                    node("export", "export", "merge"),
                    node("index", "index", "root", "merge"),
                    node("backup", "backup", "export"),
                    node("packet", "packet", "child"),
                    node("cache", "cache", "packet"),
                ])


class RetentionTests(unittest.TestCase):
    def test_forget_transitive_diamond_and_copy_obligations(self):
        report = plan(fixture(), "fixture:root", "forget")
        self.assertEqual(report["affected_count"], 8)
        self.assertEqual({o["kind"] for o in report["obligations"]}, KINDS)
        self.assertNotIn("fixture:other", [o["node_id"] for o in report["obligations"]])
        self.assertTrue(all(o["proposed_hold"] and o["status"] == "UNVERIFIED"
                            for o in report["obligations"]))
        self.assertFalse(report["erasure_verified"])
        self.assertFalse(report["applied"])
        self.assertEqual(report["authority"], "NONE")
        self.assertEqual(report["coverage_gaps"], [])

    def test_retirement_revocation_and_forget_are_distinct(self):
        reports = [plan(fixture(), "fixture:root", a) for a in ("retire", "revoke", "forget")]
        self.assertEqual(len({r["plan_sha256"] for r in reports}), 3)
        self.assertEqual([r["affected_count"] for r in reports], [8, 8, 8])
        for r in reports:
            self.assertEqual(r["status"], "REVIEW_REQUIRED")
            self.assertFalse(r["erasure_verified"])
        self.assertNotEqual(reports[0]["obligations"], reports[2]["obligations"])

    def test_correction_proposes_new_identity_without_activation(self):
        source = fixture()
        r = plan(source, "fixture:root", "correct", replacement="fixture:revised")
        self.assertEqual(r["proposed_replacement"], "fixture:revised")
        self.assertFalse(r["replacement_eligible"])
        self.assertFalse(r["applied"])
        for bad in [None, "fixture:root", "fixture:other", "real"]:
            with self.assertRaises(ValueError):
                plan(source, "fixture:root", "correct", replacement=bad)
        with self.assertRaises(ValueError):
            plan(source, "fixture:root", "forget", replacement="fixture:revised")

    def test_descendant_target_does_not_hold_ancestors(self):
        r = plan(fixture(), "fixture:child", "forget")
        ids = {o["node_id"] for o in r["obligations"]}
        self.assertNotIn("fixture:root", ids)
        self.assertNotIn("fixture:other", ids)
        self.assertEqual(len(ids), 7)

    def test_coverage_gaps_never_imply_erasure(self):
        source = fixture()
        source["coverage"]["backup"] = "unknown"
        source["coverage"]["export"] = "partial"
        r = plan(source, "fixture:root", "forget")
        self.assertEqual(r["coverage_gaps"], ["backup", "export"])
        self.assertFalse(r["erasure_verified"])
        self.assertFalse(plan(fixture(), "fixture:root", "forget")["erasure_verified"])

    def test_order_invariance_and_nonmutation(self):
        source = fixture()
        original = copy.deepcopy(source)
        other = copy.deepcopy(source)
        other["nodes"].reverse()
        for n in other["nodes"]:
            n["depends_on"].reverse()
        self.assertEqual(plan(source, "fixture:root", "revoke"),
                         plan(other, "fixture:root", "revoke"))
        self.assertEqual(source, original)
        other["coverage"]["backup"] = "unknown"
        self.assertNotEqual(plan(source, "fixture:root", "revoke")["plan_sha256"],
                            plan(other, "fixture:root", "revoke")["plan_sha256"])

    def test_invalid_graph_anywhere_fails_closed(self):
        for extra in [
            [node("a", "cache", "b"), node("b", "cache", "a")],
            [node("a", "cache", "missing")],
            [node("a", "export")],
            [node("a", "memory", "root")],
            [node("root", "memory")],
            [node("a", "cache", "root", "root")],
        ]:
            source = fixture()
            source["nodes"] += extra
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                plan(source, "fixture:root", "forget")

    def test_invalid_schema_payload_target_and_action(self):
        source = fixture()
        for action, target in [("delete", "fixture:root"), ("forget", "fixture:export"),
                               ("revoke", "fixture:missing")]:
            with self.assertRaises(ValueError):
                plan(source, target, action)
        for changed in [dict(source, synthetic=1), dict(source, schema="unknown"),
                        dict(source, coverage={}), dict(source, payload="no")]:
            with self.assertRaises(ValueError):
                plan(changed, "fixture:root", "forget")
        source["nodes"][0]["content"] = "forbidden"
        with self.assertRaises(ValueError):
            plan(source, "fixture:root", "forget")


if __name__ == "__main__":
    unittest.main()
