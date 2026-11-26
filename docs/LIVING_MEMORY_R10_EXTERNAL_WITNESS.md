# Living Memory R10.7 — separate continuity witness experiment

Base 7138bc4ea58e1f49754c7261e517d4190a514a01. Disposable synthetic
fixtures only. Authority NONE; production HELD.

## R10-08 counterexample and protocol

Local recovery cannot detect a coordinated restoration of both the main
memory and governance guard files. The test saves an old pair, withdraws
consent, commits a current snapshot, then restores the old pair. Local
evaluation can again admit the synthetic gene. The old pair still has a
valid local history. The separately retained current commitment differs.

A new advisory snapshot function takes a single serialized transaction
and authenticates the fixture operator. It computes an HMAC-SHA256 using
the store-scoped operator key and an explicit continuity domain. The
framed logical schema and sorted rows of both databases are committed,
including the event sequence; no raw row, source identifier, or key is
returned. Bounded schema/row/encoded byte counts and restricted row types
apply. This is not a general SQLite export or proof of semantic identity;
physical page layout and external copies are excluded. A local equality
comparison is only meaningful if the expected digest is independently
retained and fresh.

## Native ecosystem reuse

Inspected exact sources:

- NBGPocketMesh 0687f10970989194d4af554d9b189c7ce8a1ad15:
  docs/POCKET_EXTERNAL_ANCHOR_R11.md, scripts/pocket-anchor-authority.mjs,
  src/pocket-external-anchor.mjs. The native R11 implementation has
  nonce-bound Ed25519 attestations and create-only epoch records.
- NestedBubbleGear 41cf5be77cdd9958db55ae8de4bab559f30d79e0:
  experiments/PHMP1/KEYHOLE_BUDGET_K7.md. Signed observations do not prove
  their truth; independently retained checkpoints matter.
- XiPhiOmega 18c000897beedfb5a9759befcfd4e2330f61e227:
  docs/XPO-005.md. A valid shorter journal is indistinguishable from a
  current journal without an externally supplied tip.
- PhiGenesis README documents the Phase II PocketMesh checkpoint adapter;
  no new native PhiGenesis coupling is introduced here.

The native Node harness uses the actual PocketMesh initialize/advance,
loopback server and proof verifier functions, with fresh disposable
Ed25519 keys and a separate create-only directory. It passes real
PhiMemory9 before/after snapshot digests to the existing witness field.
This is an experimental adaptation of the existing policy-epoch API,
not a new memory-specific wire audience or checkpoint format. Use a
dedicated authority and key, never an existing policy anchor. The test
server and verifier run in one Node process, separate from Python; the
authority's directory is not among the restored database pair. No real
independent administrative custody is established by this lab.

Nine native checks: initial and advanced match, stale pair, same-epoch
digest mismatch, local epoch ahead, replayed challenge, wrong signer,
altered signed statement, and non-monotonic promotion. Native CI checks
out the exact pinned PocketMesh revision. The default Python suite
exercises six local checks and skips the optional native method unless
the trusted checkout path is explicitly supplied.

## Reproduction

    python -m unittest discover -s tests -p 'test_living_continuity_r10.py' -v

For the native check, set LIVING_NATIVE_POCKETMESH to a trusted local
checkout of the pinned revision, install Node 20+, and run the same
command. CI runs this in the existing living-native job.

## Limitations and next gate

No runtime enforcement, automatic promotion, distributed atomicity,
unavailable-authority fallback, real off-host service, external key
custody, trusted clock or power-loss qualification. The fixture verifier
can be bypassed by callers of the unchanged local API. Snapshots commit
all logical rows including ordinary audit events, so legitimate changes
also cause mismatch until an explicitly approved promotion. A mismatch
does not diagnose cause; an anchor is not proof of correct data or
current authorization. Keyed digests still permit correlation within
the same store; do not publish real commitments or keys. Restoring
both local files plus the authority history or compromising all custody
domains remains outside the model.

This milestone is advisory detection and native protocol reuse, not
rollback prevention. Next: independent verification of the full R10
ladder and a separately administered, enforced continuity design with
explicit mutation/promotion and recovery semantics. No live store access.
