"""Independent implementation comparisons on disposable closed database pairs."""
import shutil
from pathlib import Path
import tempfile
import unittest

from living_continuity_reference import reference_digest
from phimemory9.living_contract import Context, LocalIdentity, MemoryToken
from phimemory9.living_continuity import snapshot, compare
from phimemory9.living_store import LivingStore
from phimemory9.living_transport import pack, admit

OWNER = LocalIdentity("fixture:owner", b"o"*32)
SENDER = LocalIdentity("fixture:sender", b"s"*32)
DEST = LocalIdentity("fixture:destination", b"d"*32)
CTX = Context("demo", "demo-app", "research", ("research",), DEST.principal_id)
GID = "fixture:gene"


class IndependentContinuityR10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.main, self.guard = self.root/"main.db", self.root/"guard.db"
        with LivingStore.create(self.main, self.guard, OWNER) as store:
            store.register_identity(SENDER)
            store.register_identity(DEST)
            self.policy = store.set_policy(1)
            metadata = dict(gene_id=GID, project="demo", privacy="public",
                            consent="ask_first", repair="clean", confidence="high",
                            claim="fact", source_refs=["fixture:source"],
                            activate=["research"], suppress=[])
            store.add_gene(GID, "invented source payload", metadata,
                           MemoryToken("fixture:token", "synthetic",
                                       "fixture:source", "gene", "fixture:v1"))
            self.consent = store.grant(GID, SENDER, CTX, "express",
                                       now=100, expires_at=200).consent_id
            store.grant(GID, SENDER, CTX, "transfer", now=100, expires_at=200)

    def check(self, operation=None):
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            if operation is not None:
                operation(store)
            result = snapshot(store)
        expected = reference_digest(self.main, self.guard, OWNER.key)
        self.assertEqual(result["witness_sha256"], expected)
        self.assertEqual(compare(result, expected),
                         {"matches": True, "authority": "NONE", "status": "HELD"})
        return result

    def test_independent_reference_across_governance_transitions(self):
        results = [self.check()]
        results.append(self.check(lambda s: s.add_copy(GID, "cache", "fixture cache")))
        results.append(self.check(lambda s: s.withdraw_consent(self.consent)))
        results.append(self.check(lambda s: s.set_policy(2)))
        results.append(self.check(lambda s: s.repair(GID, "forget")))
        self.assertEqual(len({r["witness_sha256"] for r in results}), 5)
        self.assertEqual(self.check(), results[-1])

    def test_receipt_and_replay_state_are_bound(self):
        before = self.check()
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            packet = pack(store, [GID], SENDER, DEST, CTX, now=150,
                          expires_at=190, expected_policy=self.policy)
        packed = self.check()
        admitted = self.check(lambda s: admit(s, packet, SENDER, DEST, now=151))
        reused = self.check(lambda s: admit(s, packet, SENDER, DEST, now=152))
        self.assertNotEqual(before, packed)
        self.assertNotEqual(packed, admitted)
        self.assertEqual(admitted, reused)

    def test_separate_pair_rollback_control(self):
        before = self.check()
        copies = [self.root/"old-main.db", self.root/"old-guard.db"]
        for source, dest in zip((self.main, self.guard), copies):
            shutil.copyfile(source, dest)
        latest = self.check(lambda s: s.withdraw_consent(self.consent))
        for source, dest in zip(copies, (self.main, self.guard)):
            shutil.copyfile(source, dest)
        restored = self.check()
        self.assertEqual(restored, before)
        self.assertFalse(compare(restored, latest["witness_sha256"])["matches"])

    def test_wrong_key_does_not_reproduce_commitment(self):
        actual = self.check()
        wrong = reference_digest(self.main, self.guard, b"x"*32)
        self.assertNotEqual(actual["witness_sha256"], wrong)

    def test_schema_and_rows_are_bound(self):
        original = self.check()
        def new_table(s):
            with s.engine.transaction():
                s.db.execute('CREATE TABLE "fixture extra" (value TEXT)')
        schema = self.check(new_table)
        self.assertNotEqual(original, schema)
        def add_row(s):
            with s.engine.transaction():
                s.db.execute('INSERT INTO "fixture extra" VALUES (?)', ("text",))
        row = self.check(add_row)
        self.assertNotEqual(schema, row)

    def test_unsupported_row_types_refused_by_both(self):
        with LivingStore.open(self.main, self.guard, OWNER) as store:
            with store.engine.transaction():
                store.db.execute("CREATE TABLE fixture_extra (value)")
                store.db.execute("INSERT INTO fixture_extra VALUES (?)", (b"synthetic",))
            with self.assertRaisesRegex(ValueError, "row type"):
                snapshot(store)
        with self.assertRaisesRegex(ValueError, "row type"):
            reference_digest(self.main, self.guard, OWNER.key)


if __name__ == "__main__":
    unittest.main()
