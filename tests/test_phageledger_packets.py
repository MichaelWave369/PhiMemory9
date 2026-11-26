import unittest

from phimemory9.phageledger_packets import SCHEMA, seal, inspect


def fixture():
    return dict(schema=SCHEMA, synthetic=True, packet_id="fixture:packet-1",
                source="fixture:memoria", destination="fixture:phimemory9",
                purpose="metadata_review", not_before=100, expires_at=200,
                payload_kind="synthetic_metadata_digest", payload_sha256="a"*64,
                policy_sha256="b"*64, authority="NONE")


def expectations():
    return dict(expected_source="fixture:memoria",
                expected_destination="fixture:phimemory9",
                expected_purpose="metadata_review", expected_payload_sha256="a"*64,
                expected_policy_sha256="b"*64, now=150)


class SoftwarePacketTests(unittest.TestCase):
    def inspect(self, packet, digest=None, **changes):
        args = expectations()
        args.update(changes)
        return inspect(packet, seal(packet)["envelope_sha256"] if digest is None else digest,
                       **args)

    def test_matching_packet_still_held(self):
        report = self.inspect(fixture())
        self.assertTrue(report["compatible"])
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["status"], "HELD")
        self.assertEqual(report["authority"], "NONE")
        self.assertFalse(report["eligible"])
        self.assertEqual(report["reason"], "compatible_but_held")

    def test_expectations_are_independent_checks(self):
        for key, value, check in [
            ("expected_source", "fixture:other", "source"),
            ("expected_destination", "fixture:other", "destination"),
            ("expected_purpose", "integrity_review", "purpose"),
            ("expected_payload_sha256", "c"*64, "payload_reference"),
            ("expected_policy_sha256", "c"*64, "policy_reference"),
        ]:
            with self.subTest(check=check):
                report = self.inspect(fixture(), **{key: value})
                self.assertFalse(report["checks"][check])
                self.assertFalse(report["compatible"])
                self.assertFalse(report["eligible"])
                self.assertEqual(report["status"], "HELD")

    def test_half_open_time_window(self):
        for now, expected in [(99, False), (100, True), (199, True),
                              (200, False), (201, False)]:
            with self.subTest(now=now):
                report = self.inspect(fixture(), now=now)
                self.assertEqual(report["compatible"], expected)
                self.assertFalse(report["eligible"])

    def test_resealed_mutations_do_not_match_prior_commitment(self):
        original = fixture()
        digest = seal(original)["envelope_sha256"]
        for key, value in [("packet_id", "fixture:other"),
                           ("source", "fixture:other"),
                           ("destination", "fixture:other"),
                           ("purpose", "integrity_review"),
                           ("not_before", 101), ("expires_at", 201),
                           ("payload_sha256", "c"*64), ("policy_sha256", "c"*64)]:
            altered = dict(original, **{key: value})
            with self.subTest(key=key):
                self.assertNotEqual(seal(altered)["envelope_sha256"], digest)
                report = self.inspect(altered, digest)
                self.assertFalse(report["checks"]["integrity"])
                self.assertFalse(report["compatible"])

    def test_order_invariance_and_expectations_binding(self):
        original = fixture()
        other = dict(reversed(list(original.items())))
        self.assertEqual(seal(original), seal(other))
        self.assertEqual(self.inspect(original), self.inspect(other))
        a = self.inspect(original, now=150)
        b = self.inspect(original, now=151)
        self.assertEqual(a["checks"], b["checks"])
        self.assertNotEqual(a["expectations_sha256"], b["expectations_sha256"])
        self.assertNotEqual(a["receipt_sha256"], b["receipt_sha256"])

    def test_invalid_envelopes_refused(self):
        for key, value in [
            ("synthetic", 1), ("schema", "unknown"), ("authority", "execute"),
            ("payload_kind", "command"), ("purpose", "execute"),
            ("source", "fixture:"), ("destination", "real-system"),
            ("destination", "fixture:memoria"), ("not_before", True),
            ("not_before", -1), ("expires_at", 100), ("expires_at", 3701),
            ("expires_at", 2**53), ("payload_sha256", "A"*64),
            ("policy_sha256", "bad"), ("payload", "forbidden"),
        ]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                seal(dict(fixture(), **{key: value}))
        missing = fixture()
        del missing["policy_sha256"]
        with self.assertRaises(ValueError):
            seal(missing)

    def test_invalid_expectations_refused(self):
        for key, value in [("now", True), ("now", -1),
                           ("expected_source", "live"), ("expected_purpose", []),
                           ("expected_policy_sha256", "bad")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.inspect(fixture(), **{key: value})
        with self.assertRaises(ValueError):
            self.inspect(fixture(), "bad")

    def test_real_r03_receipt_reference(self):
        from phimemory9.genomememory_integrity import receipt
        gene = dict(gene_id="g", project="demo", privacy="public",
                    consent="safe_to_use", repair="clean", confidence="high",
                    claim="fact", source_refs=["fixture:ref"], activate=["review"],
                    suppress=[])
        group = dict(chromosome_id="root", project="demo", parent_id=None, gene_ids=["g"])
        upstream = receipt([gene], [group], "root", "demo", ["review"])
        packet = dict(fixture(), payload_sha256=upstream["receipt_sha256"])
        report = self.inspect(packet, expected_payload_sha256=upstream["receipt_sha256"])
        self.assertTrue(report["compatible"])
        self.assertFalse(report["eligible"])


if __name__ == "__main__":
    unittest.main()
