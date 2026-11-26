# GenomeMemory369 R0.7 — repair, revocation and forgetting impact plans

Status: synthetic-only, offline, authority NONE. Continues the June 20
GenomeMemory369 specification sections 10, 10.1, 11 and acceptance tests
T08/T09. No real memory, deletion, persistence or permission changes.

PhiMemory9 DEATH intentionally retains history; RENEW creates a descendant.
Neither is a hard-forget implementation. Existing R0.4 operator plans and
R0.1–R0.6 synthetic functions are unchanged.

## Inventory contract

Exactly schema, synthetic, fixture_id, nodes, coverage. Schema is
genomememory-retention-fixture/r0.7, synthetic literal true, bounded fixture:
IDs. Each of 1–256 nodes has exactly node_id, kind, depends_on. Kinds:
memory, descendant, export, index, backup, packet, cache.
An edge points from a dependent to its upstream dependency; multiple
parents represent merged information. Memory roots have no dependencies;
all other nodes have at least one. References must resolve, duplicate IDs
and duplicate parent references fail closed. Validate the entire acyclic
graph before planning, including unrelated branches. Unknown dependencies
are not silently dropped. Coverage for each of the seven kinds must be
declared_complete, partial or unknown. Declared completeness is not proof.

## Plan contract

plan(inventory, target, action, replacement=None) is a pure function.
Target must be a memory or descendant. Actions correct, retire, revoke,
forget. Correction requires a fresh proposed fixture ID, never automatically
eligible. All actions compute the transitive downstream dependency closure
including the target. Shared descendants are conservatively held as a unit;
unaffected ancestors are not selected merely because a descendant is shared.
No surgical removal of a contribution from merged content is attempted.
Each affected node has a proposed hold, kind-specific review obligation
and UNVERIFIED status. Forget plans distinguish source/derived erasure,
recipient copy removal, index removal, backup retention/restore blocking,
packet revocation and cache invalidation. Retirement and revocation propose
suppression or permission review, not erasure. A correction proposes
supersession and downstream dependency repair, not actual content creation.

The inventory and report use R0.3 domain-separated SHA-256 commitments.
IDs, dependencies and node order canonicalize as declared sets.
The report includes gaps, counts, explicit proposed holds and task labels.
All plans are REVIEW_REQUIRED, applied false, erasure_verified false,
authority NONE, including inventories declaring every category complete.
No actual hold is enforced by this module, no previous packet is
invalidated, and no adapter consumes the plan yet. Digests do not authenticate
the operator or prove erasure. The fixture marker is only a declaration.
Do not use real records or expose their metadata.

## Acceptance and next gates

Eight test methods cover a nine-node graph with shared ancestry and all
seven kinds, distinct actions, fresh correction identity, descendant-only
closure, unknown coverage, deterministic order and malformed/cyclic inputs.
The synthetic forget plan targets eight known nodes; an unrelated source
root remains outside the downstream closure. No claim of physical erasure.

    python -m unittest discover -s tests -p 'test_genomememory_retention.py' -v
    python -m unittest discover -s tests -v

Before real implementation: authenticated revocation, enforceable read and
write guards, durable tombstone/restore suppression design that minimizes
retained identifiers, storage-specific deletion and verification procedures,
recipient cooperation, unknown copy discovery, and adversarial recovery
tests. Keep retention and erasure receipts separate from actual evidence of
deletion. Next planned rung is a synthetic PhiGenesis relational learning
experiment; it must honor the hold semantics without claiming live enforcement.
