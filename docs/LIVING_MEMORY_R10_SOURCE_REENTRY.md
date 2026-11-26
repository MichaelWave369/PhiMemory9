# Living Memory R10.3 — native source reentry guard

Base: 14ce6daade3dbdfc8275d9f8a518a922d4b20bed.
Synthetic disposable fixture stores only. Production remains HELD.

## Finding R10-05

The previous add_gene checks a blocked local gene ID and token rebinding
only while a token still exists. Forget scrubs the source token if no
remaining gene references it. A new gene ID and token could therefore
reintroduce the same declared native source. This is a source-inspection
counterexample; pre-patch execution was not performed.

Before logical scrubbing, derive a keyed opaque guard ID from the canonical
tuple (source_system, source_instance, native_id), under the existing
store-scoped HMAC with a separate source-forget namespace. Store that
commitment in the existing guard blocks table atomically with forget.
Check the same commitment inside add_gene's transaction before any insert.
New token IDs and source revisions do not bypass the block. Descendants
scrubbed by a forget operation receive the same source-level protection.
No schema changes or raw source identifiers added to the guard.

## Scope and limitations

This is a conservative refusal of future reimports for a declared source
identity, not a semantic duplicate detector. It applies to forget, not
ordinary retirement, correction or revocation. A preexisting independently
linked sibling sharing a source token remains intact, preserving the
existing shared-token lifecycle contract. This is not a global source
erasure operation. Alternate source namespaces, source record ID changes,
untracked copies and semantic equivalents are not detected. Native ID
reuse may conservatively deny a legitimate newer record; there is no
automatic override. A key holder may test candidate IDs against the guard;
opaque HMAC values are not anonymity or proof of deletion.

Existing deleted records whose source metadata was already scrubbed cannot
be retrospectively guarded from this information alone. If an older main
backup restores a forgotten gene with its source token, reconciliation
can establish the commitment before re-scrubbing. No personal history
migration or guessing of missing source IDs. Restoring both files remains
outside the current rollback model. Existing local-key trust assumptions
are unchanged.

## Regression expectations

Eight new unittest methods cover fresh local IDs, changed source revision,
independent source scopes, preservation of existing shared-token siblings,
descendant source protection, main-only restore, atomic rollback on injected
failure, and absence of raw source IDs from guard rows.

    python -m unittest discover -s tests -p 'test_living_source_reentry_r10.py' -v
    python -m unittest discover -s tests -v

No external security audit or actual physical erasure is claimed. Next:
R10-06 repeated forgetting reconciliation and durable lifecycle fidelity.
