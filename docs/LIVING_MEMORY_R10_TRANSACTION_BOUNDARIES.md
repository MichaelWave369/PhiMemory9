# Living Memory R10.5 — transaction-boundary audit

Base 0332758f46273d398af728692fa3ad822f9490a1. Scoped source audit,
not a complete concurrent-runtime qualification or external review.
Disposable synthetic files only; production HELD.

## Findings R10-07

The existing MemoryEngine outer transaction uses BEGIN IMMEDIATE; nested
operations use savepoints. Several security-relevant reads nevertheless
occurred before this boundary:

* evaluate/grant: an identity may be revoked by another connection after
  the initial authentication and before the transaction starts. Recheck
  inside the transaction before evaluating or inserting consent.
* pack/admit: recheck both endpoints inside the transaction, including
  before cached receipt reuse. An early successful authentication is not
  authority to proceed after a competing revocation commits.
* set_policy: move the increasing-revision check into the transaction;
  reauthenticate the operator and reject a revision lower than or equal
  to the latest committed revision. Do not overwrite a newer policy.
* learn: read observations and lineage, validate, evaluate consent and
  compute results in a single serialized transaction. Authenticate even
  when the observation table is empty. Nested evaluate uses a savepoint.

Current consent, scope, expiry and packet checks remain in place.
The first three changes close source-inspected check/use gaps; pre-fix
execution is not claimed. No new permission or wire/schema changes.
Learning may hold the write lock longer and incur additional SQL checks;
historic benchmark traces describe their original revision only.

## Test protocol

Ten new methods use two independently opened connections to the same
disposable main and guard files. A one-shot boundary hook commits a
competing operation on connection B just before connection A acquires
its outer transaction. Cover identity revocation before expression and
grant, policy revision regression, consent withdrawal, destination
revocation before packing, source revocation before admission,
destination revocation before cached admission, learning after forgetting,
authentication on empty learning, and duplicate admission using two
threads with separate connections and a barrier. Assert receipt/event
counts and the selected post-commit state, not just exceptions.

    python -m unittest discover -s tests -p 'test_living_transactions_r10.py' -v
    python -m unittest discover -s tests -v

The scheduled tests demonstrate specific interleavings, not all possible
schedules. Parallel test uses threads with independent connections, not
a separate-process crash/power-loss experiment. The linearization boundary
is the database transaction: a revocation committed first must deny
subsequent admission; a previously committed result is not erased from
a caller's possession. Supplied fixture time is not a trusted clock.
Direct SQL, hostile host, separate process qualification, deadlock/timeout
policy, additional mutation paths (chromosome admission, migration,
repair replacement checks, gene capacity), full storage durability and
both-file rollback remain open. No claim of exactly-once external effects.
Next: expand process-level contention and interruption tests before
external rollback witness and independently administered review.
