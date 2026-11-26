import copy
import unittest

from phimemory9.genomememory_memoria import (
    SOURCE_REVISION, SNAPSHOT_SCHEMA, review_snapshot, stage_snapshot,
)


def fixture():
    return {
        "schema": SNAPSHOT_SCHEMA, "synthetic": True,
        "source_revision": SOURCE_REVISION, "fixture_id": "fixture:demo",
        "rows": [
            dict(id=2, app_name="demo", agent_id="agent-a",
                 timestamp="2026-06-20T12:00:00", tags=["research", "demo"],
                 importance_score=1.0, encrypted=0),
            dict(id=1, app_name="demo", agent_id="agent-b",
                 timestamp="2026-06-20T12:00:00Z", tags=[],
                 importance_score=0.0, encrypted=1),
        ],
    }


class MemoriaFixtureTests(unittest.TestCase):
    def stage(self, source):
        return stage_snapshot(source, "demo",
                              review_snapshot(source, "demo")["snapshot_sha256"])

    def test_all_records_held_even_high_importance(self):
        result = self.stage(fixture())
        self.assertEqual(result["eligible_count"], 0)
        self.assertEqual(result["authority"], "NONE")
        self.assertEqual([c["source_identity"]["row_id"]
                          for c in result["candidates"]], [1, 2])
        self.assertEqual(result["candidates"][1]["source_metadata"]["importance_score"], 1.0)
        for c in result["candidates"]:
            self.assertFalse(c["eligible"])
            self.assertEqual(c["status"], "HELD")
            self.assertEqual(len(c["policy"]), 9)
            self.assertTrue(all(v is None for v in c["policy"].values()))
            self.assertNotIn("content", c["source_metadata"])

    def test_order_invariance_and_no_input_mutation(self):
        source = fixture()
        reordered = copy.deepcopy(source)
        reordered["rows"].reverse()
        reordered["rows"][0]["tags"].reverse()
        original = copy.deepcopy(source)
        self.assertEqual(self.stage(source), self.stage(reordered))
        self.assertEqual(source, original)

    def test_commitment_cannot_follow_mutation(self):
        source = fixture()
        digest = review_snapshot(source, "demo")["snapshot_sha256"]
        for field, value in [("agent_id", "changed"), ("importance_score", 0.2),
                             ("tags", ["new"]), ("encrypted", 1),
                             ("timestamp", "2026-06-21T12:00:00")]:
            changed = copy.deepcopy(source)
            changed["rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                stage_snapshot(changed, "demo", digest)
        for bad in ["", None, "a"*64, digest.upper()]:
            with self.assertRaises(ValueError):
                stage_snapshot(source, "demo", bad)

    def test_scope_and_source_revision(self):
        source = fixture()
        with self.assertRaises(ValueError):
            review_snapshot(source, "other")
        for field, value in [("source_revision", "a"*40), ("synthetic", 1),
                             ("fixture_id", "real-vault"), ("schema", "unknown")]:
            altered = dict(source, **{field: value})
            with self.assertRaises(ValueError):
                review_snapshot(altered, "demo")
        changed = copy.deepcopy(source)
        changed["rows"][1]["app_name"] = "other"
        with self.assertRaises(ValueError):
            review_snapshot(changed, "demo")

    def test_payload_and_policy_injection_refused(self):
        source = fixture()
        for field in ["content", "metadata", "metadata_json", "consent", "confidence"]:
            changed = copy.deepcopy(source)
            changed["rows"][0][field] = "untrusted"
            with self.subTest(field=field), self.assertRaises(ValueError):
                review_snapshot(changed, "demo")

    def test_bad_values_and_duplicates_refused(self):
        for field, values in [
            ("id", [True, 1, 0, 2**63]),
            ("encrypted", [True, 2]),
            ("importance_score", [True, float("nan"), float("inf"), -1, 1.1, "1"]),
            ("timestamp", ["not-a-date", "2026-02-30T12:00:00"]),
            ("tags", [["a", "a"], "a"]),
        ]:
            for value in values:
                source = fixture()
                source["rows"][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    review_snapshot(source, "demo")

    def test_distinct_fixture_identity(self):
        source = fixture()
        other = dict(source, fixture_id="fixture:other")
        self.assertNotEqual(self.stage(source)["candidates"][0]["source_identity"],
                            self.stage(other)["candidates"][0]["source_identity"])
        self.assertNotEqual(review_snapshot(source, "demo")["snapshot_sha256"],
                            review_snapshot(other, "demo")["snapshot_sha256"])


if __name__ == "__main__":
    unittest.main()
