# GenomeMemory369 R0.3 — representation-invariant metadata integrity

Synthetic, offline, authority NONE. Continues the June memory specification's
lineage and verification themes and the Altermath invariant discovery and
XiPhiOmega canonical exchange research patterns. No dependency on those
repositories; no cross-language conformance is claimed yet.

## Equivalence contract

Validate the full R0.2 catalog and request, including disconnected projects,
before producing any receipt. Sort genes by stable gene ID and chromosomes by
stable chromosome ID. Sort the unique set-like fields source_refs, activate,
suppress and gene_ids, plus context_tags; normalize list and tuple to JSON
arrays. JSON object keys are sorted. Do not rename identities, flatten
relationships, coerce invalid types, ignore fields or normalize label spelling.
Ordering is declared irrelevant for precisely these fields; this does not
establish biological, linguistic or general semantic equivalence.

Each digest is SHA-256 of ASCII domain + NUL + ASCII compact sorted-key JSON,
with no trailing newline. Domains:
- genomememory/catalog/r0.3: schema plus full canonical genes and chromosomes
- genomememory/request/r0.3: root_id, project, context_tags, limit
- genomememory/result/r0.3: full R0.2 preview result
- genomememory/receipt/r0.3: object binding catalog_sha256, request_sha256,
  result_sha256

A receipt contains the four digest strings and explicit synthetic/authority
markers only. This is an integrity commitment to supplied metadata and
the deterministic preview, not a signature, authenticated timestamp, source
verification, consent grant or proof of factual accuracy. Hashes may leak
information about guessable inputs; real/private data is prohibited.

compare(before, after) takes complete argument dictionaries (including limit).
It compares normalized structures directly. It reports catalog, request and
preview equality separately; identity-set and topology changes; changed field
names on common gene IDs, including governance and provenance. Added/deleted
genes are flagged by identity-set change, not field comparison. Topology
change covers any chromosome record change, including project or membership.
Request context changes are reported as request inequality, not gene changes.
No natural-language meaning is represented, so no semantic truth is checked.
A matching preview is not sufficient for matching catalogs.

## Acceptance checks

72 exhaustive combinations of catalog order, group order and context order,
each with reversed mapping keys and set-like fields; tuple/list equivalence.
One literal independent request serialization digest vector. Mutations of
seven governance fields in an unselected project retain the same preview but
change the full receipt. Source references, parent links, stable identity,
scope and query limit changes are distinguished. Invalid disconnected inputs
refuse receipts. No raw IDs, source refs or context tags appear in receipts.

Run after editable installation:
    python -m unittest discover -s tests -p 'test_genomememory_integrity.py' -v
    python -m unittest discover -s tests -v

## Next

Freeze full golden vectors and independently implement a cross-language
oracle before any exchange claim. Native Memoria adapter should initially
accept a separately approved synthetic snapshot only, preserve missingness,
and refuse implicit promotion of importance to confidence or permission.
No real data, automatic repair, deletion, SQLite migration, network, model
calls or operational biology in R0.3.
