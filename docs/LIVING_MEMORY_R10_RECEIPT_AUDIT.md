# Living Memory R10.2 — strict receipt and replay validation

Base c2a5b33170d2be461641d456b20a5ecec8de494f. Scoped source inspection and
regression patch, not an independent external security assessment.

## Findings and changes

- R10-02: verify_receipt previously checked destination and HMAC only. An
  authenticated body could have the wrong schema, status, authority or no
  packet binding. Validate exact receipt fields, fixed schema/status/authority,
  fixture IDs, lowercase digests and integer admission time. Optional packet
  argument binds the expected packet body, identifiers, policy and time window.
  Malformed inputs return false. The optional packet is a caller-supplied
  expectation, not authenticated by this verifier; admit authenticates it.
- R10-03: cached receipts were returned after a replay/body check without
  validating the cached receipt itself. Recheck MAC, shape, packet binding
  and admission time before returning. A corrupted or substituted cache
  fails closed rather than creating a fresh receipt. This is a defense against
  inconsistent fixture state, not protection against an administrator who
  controls both keys and both stores.
- R10-04: evidence lineage did not bind the event's recorded time to the
  packet's not_before. Require exact equality, event ID and fixture authority;
  pack records the event at that timestamp. Current consent remains rechecked.
  Reject malformed tags and commitment strings at packet admission.

Existing v1 wire schema and HMAC domain are unchanged for compatibility.
Strict disjoint packet/receipt schemas reduce cross-type confusion but are
not cryptographic domain separation. A future version should use distinct
MAC domains with an explicit migration/legacy receipt policy.
No real clock, durable monotonic time, external key custody, cross-process
authentication, or new action authority. A receipt without the expected
packet is a shape/MAC check only, not evidence of present authorization.
No private data or real endpoints used.

## Regression expectations

Six new unittest methods: authenticated wrong schema/status/authority,
packet substitution, malformed shape/chronology, event-time rebinding,
cached receipt substitution and future admission, and invalid cached MAC.
Pre-patch failure inferred from inspected source, not executed.
Run on disposable fixtures:

    python -m unittest discover -s tests -p 'test_living_receipt_r10.py' -v
    python -m unittest discover -s tests -v

Full R10 remains open. Next priorities: source identity reentry under new
gene IDs, repeated forget reconciliation, both-file rollback witness,
external review and concurrent transaction boundaries. Production HELD.
