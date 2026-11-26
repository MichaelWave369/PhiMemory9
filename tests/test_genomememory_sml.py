import copy
import unittest

from phimemory9.genomememory_sml import (
    REVISION, SCHEMA, SCORES, LISTS, review_snapshot, stage_snapshot,
)


def fixture():
    def packet(mid, **changes):
        row = dict(memory_id=mid, author_agent_id="fixture-agent",
                   timestamp="2026-06-20T12:00:00+00:00", state="active",
                   collab_state="shared_verified", fork_group_id=None)
        row.update({key: 1.0 for key in SCORES})
        row.update({key: [] for key in LISTS})
        row.update(changes)
        return row
    return dict(schema=SCHEMA, synthetic=True, source_revision=REVISION,
                fixture_id="fixture:demo", packets=[
                    packet("b", links=["outside", "a"], parent_ids=["external-parent"]),
                    packet("a", state="embalmed", collab_state="local_only",
                           contributors=["y", "x"]),
                ])


class SMLFixtureTests(unittest.TestCase):
    def stage(self, data):
        return stage_snapshot(data, "fixture:demo",
                              review_snapshot(data, "fixture:demo")["snapshot_sha256"])

    def test_no_authority_even_verified_and_perfect_scores(self):
        report = self.stage(fixture())
        self.assertEqual(report["authority"], "NONE")
        self.assertEqual(report["eligible_count"], 0)
        a, b = report["candidates"]
        self.assertEqual(b["source_metadata"]["collab_state"], "shared_verified")
        self.assertEqual(b["source_metadata"]["proof_score"], 1.0)
        for candidate in (a, b):
            self.assertEqual(candidate["status"], "HELD")
            self.assertFalse(candidate["eligible"])
            self.assertEqual(len(candidate["policy"]), 9)
            self.assertTrue(all(v is None for v in candidate["policy"].values()))

    def test_relationship_missingness_and_identity(self):
        a, b = self.stage(fixture())["candidates"]
        self.assertEqual(b["unresolved_links"], ["outside"])
        self.assertEqual(b["unresolved_parents"], ["external-parent"])
        self.assertEqual(b["source_metadata"]["links"], ["a", "outside"])
        self.assertEqual(a["source_identity"]["memory_id"], "a")
        self.assertEqual(b["source_identity"]["source_revision"], REVISION)

    def test_order_invariant_and_nonmutating(self):
        data = fixture()
        before = copy.deepcopy(data)
        other = copy.deepcopy(data)
        other["packets"].reverse()
        for p in other["packets"]:
            for key in LISTS:
                p[key].reverse()
        self.assertEqual(self.stage(data), self.stage(other))
        self.assertEqual(data, before)

    def test_commitment_binds_all_metadata(self):
        data = fixture()
        digest = review_snapshot(data, "fixture:demo")["snapshot_sha256"]
        for field, value in [("proof_score", 0.3), ("collab_state", "sealed"),
                             ("state", "shadow"), ("parent_ids", ["changed"]),
                             ("author_agent_id", "other"), ("fork_group_id", "fork")]:
            altered = copy.deepcopy(data)
            altered["packets"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                stage_snapshot(altered, "fixture:demo", digest)
        for bad in [None, "", "0"*64, digest.upper()]:
            with self.assertRaises(ValueError):
                stage_snapshot(data, "fixture:demo", bad)

    def test_payload_receipts_and_policy_injection_refused(self):
        for key in ["payload", "receipts", "consent", "confidence", "privacy"]:
            data = fixture()
            data["packets"][0][key] = "forbidden"
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.stage(data)

    def test_bad_fields_and_references(self):
        for field, value in [("state", "unknown"), ("collab_state", "unknown"),
                             ("memory_id", "a"), ("proof_score", True),
                             ("dispute_score", float("nan")), ("field_score", 2),
                             ("links", ["b"]), ("parent_ids", ["b"]),
                             ("contributors", ["x", "x"]), ("timestamp", "2026-02-30T00:00:00")]:
            data = fixture()
            data["packets"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.stage(data)

    def test_scope_schema_revision_and_missing_fields(self):
        data = fixture()
        with self.assertRaises(ValueError):
            review_snapshot(data, "fixture:other")
        for field, value in [("synthetic", 1), ("schema", "unknown"),
                             ("source_revision", "0"*40), ("fixture_id", "live")]:
            altered = dict(data, **{field: value})
            with self.assertRaises(ValueError):
                self.stage(altered)
        del data["packets"][0]["proof_score"]
        with self.assertRaises(ValueError):
            self.stage(data)


if __name__ == "__main__":
    unittest.main()
