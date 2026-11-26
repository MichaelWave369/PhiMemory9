import unittest
from phimemory9.genomememory_chromosomes import chromosome_preview


def gene(gid, **changes):
    row = dict(gene_id=gid, project="demo", privacy="public",
               consent="safe_to_use", repair="clean", confidence="high",
               claim="fact", source_refs=["fixture:1"], activate=["research"],
               suppress=[])
    row.update(changes)
    return row


def group(cid, parent, ids, project="demo"):
    return dict(chromosome_id=cid, project=project, parent_id=parent, gene_ids=ids)


def fixture():
    genes = [gene("a"), gene("b", suppress=["public"]), gene("c"),
             gene("d", privacy="private"), gene("e", consent="ask_first"),
             gene("f", repair="stale"), gene("g", confidence="low"),
             gene("h", claim="hypothesis"), gene("i", source_refs=[]),
             gene("j", activate=["review"])]
    groups = [group("root", None, ["a", "b", "d", "e"]),
              group("child", "root", ["a", "c", "f", "g"]),
              group("leaf", "child", ["c", "h", "i", "j"])]
    return genes, groups


class ChromosomeTests(unittest.TestCase):
    def test_original_ten_genes_three_chromosomes_five_contexts(self):
        genes, groups = fixture()
        for tags, expected in [
            (["research"], ["a", "b", "c"]),
            (["research", "public"], ["a", "c"]),
            (["review"], ["j"]), ([], []),
            (["research", "review"], ["a", "b", "c", "j"]),
        ]:
            with self.subTest(tags=tags):
                result = chromosome_preview(genes, groups, "root", "demo", tags, 9)
                self.assertEqual(result["eligible_ids"], expected)
                self.assertEqual(result["chromosome_count"], 3)
                self.assertEqual(result["membership_count"], 12)
                self.assertEqual(result["unique_gene_count"], 10)
                self.assertEqual(result["duplicate_memberships"], 2)
                self.assertEqual(result["authority"], "NONE")

    def test_subtree_scope_and_shared_gene(self):
        genes, groups = fixture()
        result = chromosome_preview(genes, groups, "child", "demo", ["research"], 9)
        self.assertEqual(result["unique_gene_count"], 7)
        self.assertEqual(result["eligible_ids"], ["a", "c"])
        self.assertEqual(chromosome_preview(genes, groups, "leaf", "demo",
                                            ["research"], 9)["eligible_ids"], ["c"])

    def test_order_and_single_global_cap(self):
        genes, groups = fixture()
        result = chromosome_preview(genes, groups, "root", "demo", ["research"], 2)
        reordered = [dict(g, gene_ids=g["gene_ids"][::-1]) for g in groups[::-1]]
        self.assertEqual(result, chromosome_preview(genes[::-1], reordered, "root",
                                                      "demo", ["research"], 2))
        self.assertEqual(result["eligible_ids"], ["a", "b"])
        self.assertEqual(chromosome_preview(genes, groups, "root", "demo",
                                            ["research"], 0)["eligible_ids"], [])

    def test_invalid_catalog_and_memberships(self):
        genes, groups = fixture()
        cases = [
            (genes, groups + [group("bad", None, ["unknown"])]),
            (genes, groups + [groups[0]]),
            (genes, [dict(groups[0], gene_ids=["a", "a"])] + groups[1:]),
            (genes + [gene("ungrouped")], groups),
            (genes + [genes[0]], groups),
            (genes, groups + [dict(group("bad", None, []), permission="allow")]),
        ]
        for gs, cs in cases:
            with self.subTest(groups=cs):
                with self.assertRaises(ValueError):
                    chromosome_preview(gs, cs, "root", "demo", ["research"])

    def test_cycle_missing_parent_and_depth(self):
        genes, groups = fixture()
        for extra in [
            [group("x", "y", []), group("y", "x", [])],
            [group("x", "missing", [])],
            [group("x", "x", [])],
            [group("x" + str(i), None if i == 0 else "x" + str(i-1), [])
             for i in range(7)],
        ]:
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError):
                    chromosome_preview(genes, groups + extra, "root", "demo", ["research"])

    def test_cross_project_and_unselected_validation(self):
        genes, groups = fixture()
        other = gene("z", project="other")
        valid = groups + [group("other", None, ["z"], "other")]
        self.assertEqual(chromosome_preview(genes + [other], valid, "root",
                                            "demo", ["research"])["eligible_ids"], ["a", "b", "c"])
        for gs, cs, root, scope in [
            (genes + [other], valid, "other", "demo"),
            (genes + [other], groups + [group("other", "root", ["z"], "other")], "root", "demo"),
            (genes + [other], groups + [group("other", None, ["z"])], "root", "demo"),
            (genes + [dict(other, privacy="invalid")], valid, "root", "demo"),
        ]:
            with self.assertRaises(ValueError):
                chromosome_preview(gs, cs, root, scope, ["research"])


if __name__ == "__main__":
    unittest.main()
