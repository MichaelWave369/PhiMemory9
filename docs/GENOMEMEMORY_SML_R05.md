# GenomeMemory369 R0.5 — Sovereign Memory Lattice fixture projection

Synthetic, offline, authority NONE. This is a compatibility staging prototype,
not a live native SML integration, execution adapter or authorization mechanism.

## Source inspection

Pinned SML commit 43f7513c46529167d842a7c195029b03574dc393:
- sml/memory/packets.py: MemoryPacket, lifecycle and collaboration states,
  author/contributor labels, scores, links, parents, fork groups and receipts.
- sml/engines/ingest.py: token-based coherence and novelty, default proof 0.5.
- sml/governance/model_output.py: heuristic candidate scores, proof 0.2.
- sml/governance/filtering.py: visibility, dispute and trust thresholds.
- sml/persistence/store.py and sml/core/graph.py: canonical node persistence,
  hydration defaults and graph reconstruction.
- sml/engines/retrieve.py: query-time field/render scoring.

Native proof and consensus scores are not independent evidence verification.
The shared_verified collaboration label is not a GenomeMemory consent grant.
The native receipt signature helper hashes a representation of supplied
fields; it is not authenticated digital signing. Native graph loading calls
initialize and can create directories. Do not import or invoke these modules
against a real store for this experiment.

## Strict fixture wrapper

The new envelope has exactly schema, synthetic, source_revision, fixture_id
and packets. Schema is genomememory-sml-fixture/r0.5. Revision is pinned;
synthetic must be literal true, fixture_id must match the explicitly selected
fixture: namespace. The marker is a declaration, not proof of origin.
Use invented fixtures only.

Each projected packet has exactly the 17 fields from the native dataclass
other than payload and receipts: identity, author, timestamp, contributor/
intent/role labels, six scores, state, collaboration state, links, parents
and optional fork group. Payload, raw receipts and injected policy fields are
refused. Bounds: 1–256 packets, unique bounded ASCII IDs and lists, six finite
scores in [0,1], known native states, valid ISO-like timestamp spelling.
Naive timestamps retain unknown zone. No default repair, identity substitution,
or inference from a missing field. Duplicate labels and self references are
refused. Other graph cycles or nonreciprocal links are retained as declarations;
no native graph reconstruction or ancestry validation. References absent from
this fixture are explicitly reported, never treated as nonexistent records.

For the fixture contract, packet and list ordering is irrelevant, numeric
scores normalize to Python floats and zero to positive zero. This is a
declared projection equivalence, not native serialization equivalence.

## Review and stage

review_snapshot(snapshot, expected_fixture) produces a count and domain
separated SHA-256 commitment to the canonical projected snapshot.
stage_snapshot(snapshot, expected_fixture, reviewed_sha256) recomputes and
checks the commitment, preserves metadata and fixture-local identity, and
returns only HELD candidates with nine null GenomeMemory policy fields and
zero eligible records. A digest is not evidence of human approval, replay
protection, or authentication. Source references and other IDs may reveal
information; real memory metadata is not supported. No payload, SQLite,
network, model, native receipt verification, or storage writes.

## Tests and next step

Seven test methods exercise perfect score and verified-label holds, explicit
unresolved reference handling, stable ordering and unchanged inputs,
commitment mutation, payload/receipt rejection, invalid fields, and scope.

    python -m unittest discover -s tests -p 'test_genomememory_sml.py' -v
    python -m unittest discover -s tests -v

Next: a distinct PhageLedger-inspired software-only packet envelope with
explicit target, purpose, expiry and integrity bindings. No transfer of
SML permissions, no biological payloads and no runtime dispatch. Native
Memoria/SML exports, authentication, erasure and real-data governance remain
separate review gates.
