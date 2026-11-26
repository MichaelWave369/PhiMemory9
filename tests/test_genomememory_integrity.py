import copy
import hashlib
import itertools
import unittest

from phimemory9.genomememory_integrity import compare, receipt


def fixture():
    def gene(gid, project="demo"):
        return dict(gene_id=gid, project=project, privacy="public",
                    consent="safe_to_use", repair="clean", confidence="high",
                    claim="fact", source_refs=["fixture:2", "fixture:1"],
                    activate=["research", "review"], suppress=["stop", "pause"])
    return dict(
        genes=[gene("a"), gene("b"), gene("z", "other")],
        chromosomes=[
            dict(chromosome_id="root", project="demo", parent_id=None, gene_ids=["b", "a"]),
            dict(chromosome_id="child", project="demo", parent_id="root", gene_ids=["a"]),
            dict(chromosome_id="other", project="other", parent_id=None, gene_ids=["z"]),
        ],
        root_id="root", project="demo", context_tags=["research", "review"], limit=1,
    )


class IntegrityTests(unittest.TestCase):
    def test_72_permutations(self):
        source = fixture()
        expected = receipt(**source)
        for genes, groups, tags in itertools.product(
                itertools.permutations(source["genes"]),
                itertools.permutations(source["chromosomes"]),
                itertools.permutations(source["context_tags"])):
            candidate = dict(source, genes=[dict(reversed(list(g.items()))) for g in genes],
                             chromosomes=[dict(reversed(list(c.items()))) for c in groups],
                             context_tags=tags)
            for g in candidate["genes"]:
                for field in ("source_refs", "activate", "suppress"):
                    g[field] = tuple(reversed(g[field]))
            for c in candidate["chromosomes"]:
                c["gene_ids"] = tuple(reversed(c["gene_ids"]))
            self.assertEqual(receipt(**candidate), expected)
            result = compare(source, candidate)
            self.assertTrue(result["catalog_equivalent"])
            self.assertTrue(result["request_equivalent"])
            self.assertTrue(result["preview_equivalent"])
            self.assertEqual(result["changed_gene_fields"], [])

    def test_independent_request_digest_vector(self):
        # Literal serialization, independent of production normalizer.
        raw = b'genomememory/request/r0.3\x00{"context_tags":["research","review"],"limit":1,"project":"demo","root_id":"root"}'
        self.assertEqual(receipt(**fixture())["request_sha256"], hashlib.sha256(raw).hexdigest())

    def test_governance_mutations_even_when_preview_unchanged(self):
        source = fixture()
        for field, value in [
            ("privacy", "private"), ("consent", "ask_first"),
            ("repair", "stale"), ("confidence", "low"), ("claim", "hypothesis"),
            ("activate", ["unmatched"]), ("suppress", ["research"]),
        ]:
            candidate = copy.deepcopy(source)
            candidate["genes"][2][field] = value  # outside selected project
            result = compare(source, candidate)
            self.assertFalse(result["catalog_equivalent"])
            self.assertTrue(result["preview_equivalent"])
            self.assertEqual(result["governance_fields_changed"], [field])
            self.assertNotEqual(receipt(**source)["receipt_sha256"],
                                receipt(**candidate)["receipt_sha256"])
            self.assertEqual(receipt(**source)["result_sha256"],
                             receipt(**candidate)["result_sha256"])

    def test_provenance_topology_identity_and_request(self):
        source = fixture()
        candidate = copy.deepcopy(source)
        candidate["genes"][0]["source_refs"] = ["fixture:3"]
        self.assertTrue(compare(source, candidate)["provenance_changed"])
        candidate = copy.deepcopy(source)
        candidate["chromosomes"][1]["parent_id"] = None
        self.assertTrue(compare(source, candidate)["topology_changed"])
        candidate = copy.deepcopy(source)
        candidate["genes"][2]["gene_id"] = "new"
        candidate["chromosomes"][2]["gene_ids"] = ["new"]
        self.assertTrue(compare(source, candidate)["identity_set_changed"])
        candidate = dict(source, limit=2)
        report = compare(source, candidate)
        self.assertTrue(report["catalog_equivalent"])
        self.assertFalse(report["request_equivalent"])
        self.assertFalse(report["preview_equivalent"])
        self.assertEqual(receipt(**source)["catalog_sha256"],
                         receipt(**candidate)["catalog_sha256"])

    def test_scope_change_valid_and_detected(self):
        source = fixture()
        candidate = copy.deepcopy(source)
        candidate["genes"][2]["project"] = "third"
        candidate["chromosomes"][2]["project"] = "third"
        result = compare(source, candidate)
        self.assertEqual(result["governance_fields_changed"], ["project"])
        self.assertTrue(result["topology_changed"])
        self.assertTrue(result["preview_equivalent"])

    def test_invalid_never_receipted(self):
        source = fixture()
        candidate = copy.deepcopy(source)
        candidate["genes"][2]["source_refs"] = ["x", "x"]
        with self.assertRaises(ValueError):
            receipt(**candidate)
        with self.assertRaises(ValueError):
            compare(source, candidate)
        candidate = copy.deepcopy(source)
        candidate["chromosomes"][2]["parent_id"] = "other"
        with self.assertRaises(ValueError):
            receipt(**candidate)

    def test_receipt_has_only_digests_and_boundary(self):
        result = receipt(**fixture())
        self.assertEqual(result["authority"], "NONE")
        self.assertTrue(result["synthetic"])
        self.assertEqual(set(result), {"schema", "synthetic", "authority",
                                      "catalog_sha256", "request_sha256",
                                      "result_sha256", "receipt_sha256"})
        for key in ("catalog_sha256", "request_sha256", "result_sha256", "receipt_sha256"):
            self.assertEqual(len(result[key]), 64)
        self.assertEqual(len({result[key] for key in result if key.endswith("sha256")}), 4)


if __name__ == "__main__":
    unittest.main()
