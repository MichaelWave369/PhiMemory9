# GenomeMemory369 R0.4 — Memoria-shaped fixture intake

Status: synthetic offline prototype, authority NONE. This is a metadata-only
compatibility experiment, not a live Memoria adapter or authorization system.

## Source inspection

Memoria main was inspected at commit
9c480fcaea467615252d347956eac42ff038edf7:
- db/models.py: MemoryRecord
- db/storage.py: memories table, store_memory, query_memories, delete_memory,
  encryption helper and permission table
- backend/api.py: query, semantic, store, delete and permission handlers

The query handler returns memory content and does not consult the stored
can_read setting. The store handler defaults to allowing writes for an
unregistered app. Encryption can use a default-derived key and the store
handler passes plaintext to the vector upsert. The inspected delete handler
only invokes SQLite deletion. These are source observations, not a runtime
security assessment or evidence of an actual disclosure. No connection to
the API, databases, vector indexes, files or keys is permitted at this rung.
Native export, access enforcement, encryption and deletion review are required
before any real-memory bridge.

## Fixture contract

An invented operator-supplied snapshot has exactly schema, synthetic,
source_revision, fixture_id and rows. Schema is
genomememory-memoria-fixture/r0.4; synthetic must be literal true; source
revision must equal the inspected commit. Fixture ID begins with fixture:.
This is a new wrapper, not Memoria's native export format.

Each row contains exactly id, app_name, agent_id, timestamp, tags,
importance_score and encrypted. Content, arbitrary metadata and policy
injection are refused. One explicit app scope; positive SQLite-range integer
IDs unique within the fixture; 1–256 rows; bounded ASCII fixture labels and
unique tags as in R0.1. Importance is a finite number from zero to one, not
a confidence measure. Native encryption indicator is integer zero or one,
not proof of protection. Date/time syntax and Python ISO parsing are checked;
the timestamp spelling is retained, naive timestamps are not assigned a zone
and no chronology is inferred. Scope is a caller assertion, not authenticated
identity. Real rows may not meet these deliberately narrow fixture rules.

## Review and staging

review_snapshot(snapshot, expected_app) returns a row count and SHA-256
commitment to the normalized snapshot plus requested app. Row and tag order
are immaterial; numeric importance is normalized to float (zero to +0.0).
No timestamp normalization. Python canonical JSON and R0.3 domain separation
are reused; no cross-language float interoperability asserted.

stage_snapshot(snapshot, expected_app, reviewed_sha256) recomputes and
compares the digest before producing a staging report. Every candidate is
HELD with eligible false. Source identity includes system, fixture ID, row ID
and pinned revision; this is a fixture-local identity, not an authenticated
database ID. Source metadata is retained as synthetic metadata. The nine
GenomeMemory fields are explicitly null: project, privacy, consent, repair,
confidence, claim, source_refs, activate, suppress. Memoria app names are
not inferred to be GenomeMemory projects; importance is not confidence;
tags are not activation rules; encryption is not consent; source identity
is not evidence verification. No candidate is passed into the R0.1 preview.

The digest is an integrity check, not an approval signature or evidence of
actual human review. No durable state, authorization, anti-replay or action
is provided. Staging outputs contain fixture metadata, not privacy-safe
exports; never supply real records. No modification to Memoria, PhiMemory9
storage or existing R0.1–R0.3 functions.

## Acceptance and next gates

Seven test methods cover missing policy, high importance, order invariance,
digest mutation, source identity and app scope, payload/policy injection,
invalid numeric and date values and duplicate IDs.

    python -m unittest discover -s tests -p 'test_genomememory_memoria.py' -v
    python -m unittest discover -s tests -v

Next: inspect native Sovereign Memory Lattice schema at a pinned revision,
define a distinct synthetic staging adapter, preserve missing values and
authority boundaries. A later actual Memoria bridge requires an explicit
metadata-only export and reviewed read authorization, plus key, retention
and vector deletion review. Do not silently combine the repositories.
