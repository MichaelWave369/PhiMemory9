# PhageLedger369 R0.6 — bounded software envelope

Status: synthetic offline compatibility experiment; authority NONE. This is
the software analogy from the June 19 PhageLedger369 specification
(sections 3 and 9), not its biological literature atlas, a simulation of
infection, or an operational biological system. The original document remains
unchanged. No biological data, biological payload, or biological procedures.

## Design choices

The original policy capsid, addressed packet and compatibility concepts become
an immutable-by-commitment metadata envelope. The packet contains references
to synthetic metadata and policy digests only, never executable instructions
or actual memory content. The caller supplies independently retained expected
digests and exact source/destination/purpose expectations. There is no native
Memoria, SML, XiPhiOmega or PhiOS transport at this rung.

Exactly twelve fields: schema, synthetic, packet_id, source, destination,
purpose, not_before, expires_at, payload_kind, payload_sha256, policy_sha256,
authority. Schema phageledger-software-envelope/r0.6; synthetic literal true;
authority NONE; payload_kind synthetic_metadata_digest. All three identifiers
use the fixture: namespace and bounded ASCII labels. Source differs from
destination. Purposes are metadata_review or integrity_review only.
Times are explicitly supplied integer epoch seconds in [0, 2^53-1], not a
trusted clock. Maximum lifetime is 3600 seconds, with a half-open window
[not_before, expires_at). Digest strings are exactly 64 lowercase hex digits.
Unknown, missing or malformed fields refuse processing.

seal(envelope) uses the R0.3 canonical ASCII JSON digest helper with domain
phageledger/software-envelope/r0.6. The returned commitment is not a digital
signature, encryption or proof of source identity. An independently retained
prior digest is necessary to detect resealing; a party controlling both
envelope and expected digest can substitute both.

inspect(envelope, expected_sha256, *, expected_source, expected_destination,
expected_purpose, expected_payload_sha256, expected_policy_sha256, now)
checks seven independent conditions: integrity, source, destination, purpose,
payload reference, policy reference, and time window. A compatible packet
is still HELD with eligible false and authority NONE. Invalid input raises
ValueError. A structurally valid mismatch returns HELD and compatible false.
The report commits to the supplied expectations (including time), envelope,
expected commitment and check results. No raw identifiers are emitted in
the report. This is a synthetic receipt, not a trusted audit log.

The payload and policy digests are reference equality checks only. They do
not validate actual policy or payload existence. No authorization, verified
consent, revocation, encryption, durable replay prevention, persistence,
network access, runtime invocation, real clocks, or dispatch. Repeating an
inspection is allowed; it has no side effects. Fixture labels and digests
are not proof that input is synthetic. Never use real private memory.

## Acceptance

Eight test methods exercise compatible-but-held, five mismatched expectations,
half-open time boundaries, eight envelope mutation cases, ordering and
expectation binding, malformed input, and an actual synthetic R0.3 integrity
receipt referenced by an R0.6 envelope.

    python -m unittest discover -s tests -p 'test_phageledger_packets.py' -v
    python -m unittest discover -s tests -v

Next: separate repair/revocation and forgetting semantics. Preserve the
distinction between retired content and hard deletion; model descendant,
export, index and backup obligations without claiming verified erasure.
A future native transport requires independent endpoint authentication and
explicit destination authorization, not simply a matching hash.
