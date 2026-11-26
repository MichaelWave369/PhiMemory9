# Living Memory R10.4 — idempotent forgetting reconciliation

Base e085d0bd78d38ecc1edb4b764cd9684322a187f0. Disposable fixtures only.

## Finding R10-06

The previous _scrub always deleted all core events and inserted a new DEATH
event even for a correctly scrubbed memory. Reconciliation on every open
therefore changed event identity, timestamp and the SQLite event sequence.
This is a source-inspection counterexample; pre-fix tests were not executed.

Preserve the existing sole DEATH event if its detail matches the logical
deletion marker and the core memory content, fingerprint, retired state
and null source reference are already correct. If these conditions fail,
repair the marker and recreate the minimal deletion event as appropriate.
A deleted gene flag alone never short-circuits cleanup: still sweep copies,
consents, observations, memberships, ancestry, related overlay events
and receipts. Keep the source guard and external obligations.

Avoid redundant row updates for clean tombstones, detached core ancestry,
already-held records and already-withdrawn consent. Preserve existing
schema and public API. Repeating repair(target, 'forget') on a deleted
target continues to raise ValueError without mutation.

## Acceptance

Eight fixture regression methods cover stable SQL dumps and zero additional
SQLite total_changes on repeated clean reconciliation, cold opens preserving
event identity/time, residual copies/events, restored payload despite a
deleted flag, extra core events, stale main-only backup recovery, unrelated
memory and consent, and the explicit repeated-repair refusal contract.

    python -m unittest discover -s tests -p 'test_living_forget_recovery_r10.py' -v
    python -m unittest discover -s tests -v

Logical idempotence here refers to this reconciliation procedure on clean,
consistent fixture state, not byte-for-byte database files, filesystem
metadata, physical erasure or a universal proof of deletion. Corrupted
unparseable event data may fail closed; malicious edits and rolling back
both stores remain outside the trusted host model. External copies remain
unknown; no new authority, schema migration or production readiness.
Next: R10-07 concurrent process and transaction-boundary tests.
