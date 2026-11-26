import unittest
from phimemory9.genomememory_preview import preview


def gene(gid, **changes):
    row = dict(gene_id=gid, project="demo", privacy="public",
               consent="safe_to_use", repair="clean", confidence="high",
               claim="fact", source_refs=["fixture:1"], activate=["research"],
               suppress=[])
    row.update(changes)
    return row


class GenomeMemoryPreviewTests(unittest.TestCase):
    def test_ten_fixture_candidates(self):
        rows = [
            gene("a"), gene("b", suppress=["public"]),
            gene("c", project="other"), gene("d", privacy="private"),
            gene("e", consent="ask_first"), gene("f", repair="stale"),
            gene("g", confidence="low"), gene("h", claim="hypothesis"),
            gene("i", source_refs=[]), gene("j", activate=["review"]),
        ]
        report = preview(rows, "demo", ["research", "public"])
        self.assertEqual(report["eligible_ids"], ["a"])
        self.assertEqual([d["reason"] for d in report["decisions"]],
                         ["preview_eligible", "suppression_match", "scope_mismatch",
                          "privacy_hold", "consent_hold", "repair_hold",
                          "confidence_hold", "claim_hold", "source_missing",
                          "activation_missing"])
        self.assertEqual(report["authority"], "NONE")
        self.assertTrue(report["synthetic"])
        self.assertEqual(preview(rows, "demo", ["research"])["eligible_ids"], ["a", "b"])
        self.assertEqual(preview(rows, "demo", ["review"])["eligible_ids"], ["j"])
        self.assertEqual(preview(rows, "other", ["research"])["eligible_ids"], ["c"])
        self.assertEqual(preview(rows, "demo", [])["eligible_ids"], [])

    def test_suppression_beats_all_activation_tags(self):
        row = gene("a", activate=["research", "review"], suppress=["stop"])
        self.assertEqual(preview([row], "demo", ["research"])["eligible_ids"], [])
        self.assertEqual(preview([row], "demo", ["research", "review"])["eligible_ids"], ["a"])
        self.assertEqual(preview([row], "demo", ["research", "review", "stop"])["eligible_ids"], [])

    def test_order_and_cap(self):
        rows = [gene("c"), gene("a"), gene("b")]
        result = preview(rows, "demo", ["research"], 2)
        self.assertEqual(result, preview(rows[::-1], "demo", ["research"], 2))
        self.assertEqual(result["eligible_ids"], ["a", "b"])
        self.assertEqual(result["decisions"][-1]["reason"], "limit_hold")
        self.assertEqual(preview(rows, "demo", ["research"], 0)["eligible_ids"], [])

    def test_no_implicit_permission(self):
        for consent in ["soft_sensitive", "ask_first", "receipt_required",
                        "never_infer", "never_act_without_consent"]:
            with self.subTest(consent=consent):
                self.assertEqual(preview([gene("a", consent=consent)], "demo",
                                         ["research", "approved"])["eligible_ids"], [])

    def test_invalid_fails_closed(self):
        for bad in [gene("a", privacy="unknown"), gene("a", meaning="payload"),
                    gene("a", activate="research"), gene("a", source_refs=["x", "x"]),
                    gene("a", confidence=[]), gene("a", project=""), gene("a", activate=[1])]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    preview([gene("valid"), bad], "demo", ["research"])
        for rows, limit in [([gene("a"), gene("a")], 3), ([gene("a")], True),
                            ([gene("a")], 10)]:
            with self.assertRaises(ValueError):
                preview(rows, "demo", ["research"], limit)

    def test_no_payload_or_source_output(self):
        report = preview([gene("a", source_refs=["private:marker"])],
                         "demo", ["research"])
        self.assertNotIn("private:marker", str(report))
        self.assertNotIn("research", str(report))
        self.assertNotIn("demo", str(report))

    def test_empty_activation_and_repair_hold(self):
        self.assertEqual(preview([gene("a", activate=[])], "demo",
                                 ["research"])["eligible_ids"], [])
        for state in ["stale", "contradicted", "needs_review", "archived"]:
            self.assertEqual(preview([gene("a", repair=state)], "demo",
                                     ["research"])["eligible_ids"], [])


if __name__ == "__main__":
    unittest.main()
