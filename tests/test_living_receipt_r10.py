"""R10 receipt integrity tests, using disposable synthetic stores only."""
import copy
from pathlib import Path
import tempfile
import unittest

from phimemory9.living_contract import Context, LocalIdentity, MemoryToken, canonical
from phimemory9.living_store import LivingStore
from phimemory9.living_transport import pack, admit, verify_receipt, _mac


class ReceiptR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.owner = LocalIdentity("fixture:owner", b"o"*32)
        self.sender = LocalIdentity("fixture:sender", b"s"*32)
        self.dest = LocalIdentity("fixture:destination", b"d"*32)
        root = Path(self.tmp.name)
        self.store = LivingStore.create(root/"main.db", root/"guard.db", self.owner)
        self.addCleanup(self.store.close)
        self.store.register_identity(self.sender)
        self.store.register_identity(self.dest)
        self.policy = self.store.set_policy(1)
        gid = "fixture:gene"
        metadata = dict(gene_id=gid, project="demo", privacy="public",
                        consent="ask_first", repair="clean", confidence="high",
                        claim="fact", source_refs=["fixture:source"],
                        activate=["research"], suppress=[])
        self.store.add_gene(gid, "invented observation", metadata,
                            MemoryToken("fixture:token", "synthetic",
                                        "fixture:source", "gene", "fixture:v1"))
        self.context = Context("demo", "demo-app", "research", ("research",),
                               self.dest.principal_id)
        self.store.grant(gid, self.sender, self.context, "transfer",
                         now=100, expires_at=200)

    def packet(self, now=150):
        return pack(self.store, ["fixture:gene"], self.sender, self.dest,
                    self.context, now=now, expires_at=190,
                    expected_policy=self.policy)

    def admit(self, packet, now=151):
        return admit(self.store, packet, self.sender, self.dest, now=now)

    def signed_receipt(self, body):
        return dict(body=body, mac=_mac(self.dest.key, body))

    def test_authenticated_wrong_schema_status_and_authority(self):
        packet = self.packet()
        receipt = self.admit(packet)
        self.assertTrue(verify_receipt(receipt, self.dest, packet=packet))
        for field, value in [("schema", "other"), ("status", "OTHER"),
                             ("authority", "EXECUTE"), ("admitted_at", True),
                             ("packet_sha256", "not-a-hash"), ("extra", "field")]:
            with self.subTest(field=field):
                body = dict(receipt["body"], **{field: value})
                self.assertFalse(verify_receipt(self.signed_receipt(body), self.dest))
        body = dict(receipt["body"])
        del body["evidence_event"]
        self.assertFalse(verify_receipt(self.signed_receipt(body), self.dest))

    def test_packet_substitution_detected(self):
        packet, other = self.packet(), self.packet()
        receipt = self.admit(packet)
        self.assertTrue(verify_receipt(receipt, self.dest))
        self.assertTrue(verify_receipt(receipt, self.dest, packet=packet))
        self.assertFalse(verify_receipt(receipt, self.dest, packet=other))
        self.assertFalse(verify_receipt(receipt, self.sender, packet=packet))

    def test_receipt_chronology_and_malformed_shapes(self):
        packet = self.packet()
        receipt = self.admit(packet)
        for time in (149, 190, 191):
            body = dict(receipt["body"], admitted_at=time)
            self.assertFalse(verify_receipt(self.signed_receipt(body), self.dest, packet=packet))
        for invalid in (None, [], {"body": [], "mac": "a"*64}, {"body": {}}):
            self.assertFalse(verify_receipt(invalid, self.dest))
        self.assertFalse(verify_receipt(receipt, self.dest, packet={"body": []}))

    def test_evidence_time_cannot_be_rebound(self):
        packet = self.packet()
        later = self.packet(now=152)
        changed = copy.deepcopy(later)
        changed["body"]["evidence_event"] = packet["body"]["evidence_event"]
        changed["mac"] = _mac(self.sender.key, changed["body"])
        with self.assertRaisesRegex(PermissionError, "receipt lineage"):
            self.admit(changed, now=153)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM lm_guard.replays").fetchone()[0], 0)

    def test_cached_receipt_checked_against_packet_and_clock(self):
        packet = self.packet()
        first = self.admit(packet, now=152)
        with self.assertRaisesRegex(PermissionError, "future-dated"):
            self.admit(packet, now=151)
        self.assertEqual(first, self.admit(packet, now=153))
        # Deliberately corrupt the disposable main cache, not the guard.
        other = self.packet()
        second = self.admit(other, now=153)
        with self.store.engine.transaction():
            self.store.db.execute("UPDATE lm_receipts SET body_json=?",
                                  (canonical(second).decode("ascii"),))
        with self.assertRaisesRegex(PermissionError, "cached receipt"):
            self.admit(packet, now=154)

    def test_cached_bad_mac_is_not_returned(self):
        packet = self.packet()
        receipt = self.admit(packet)
        receipt["mac"] = "0"*64
        with self.store.engine.transaction():
            self.store.db.execute("UPDATE lm_receipts SET body_json=?",
                                  (canonical(receipt).decode("ascii"),))
        with self.assertRaisesRegex(PermissionError, "cached receipt"):
            self.admit(packet, now=152)


if __name__ == "__main__":
    unittest.main()
