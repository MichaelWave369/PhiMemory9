# GenomeMemory369 R0.2 — Nested memory chromosomes

Synthetic-only offline metadata experiment; authority NONE. This continues
the June 20, 2026 GenomeMemory369 specification sections 7.3, 18 (T02),
and appendix D. The three-chromosome nesting is a new design choice inspired
by PhiMemory9 contexts and NBG, not a requirement of the original spec.
The source fingerprints in GENOMEMEMORY_RECONCILIATION_R01.md were
recomputed from both operator-supplied DOCX files and match.

## Contract

One catalog of unique R0.1 gene IDs; each gene may be linked to multiple
chromosomes in its own project. Every chromosome has an explicit project,
unique ID, zero or one parent and a list of member IDs. Groups are not blobs
or permissions. Selection walks a chosen subtree, takes the union of its
member IDs, and applies the existing R0.1 expression preview exactly once.
A group cannot override a gene's consent, privacy, repair, activation or
suppression. No group-level policy inheritance exists. No implicit movement,
storage, graph mutation or payload access.

Bounds: 256 genes (R0.1), 64 groups, 64 members per group, 6 levels
(root counts as 1), 0–9 eligible IDs. Invalid IDs, unknown references,
duplicate IDs or membership within one chromosome, missing parents, cycles,
cross-project links or ancestry, ungrouped genes and invalid metadata anywhere
in the catalog fail closed. All branches are checked before selection.
Ordering is lexicographic by gene ID, not relevance. Counts and reason codes
are synthetic fixture diagnostics; never expose private records through
this function. A selected subtree may be rooted at any existing group in
the requested project; the caller-supplied project is not authentication.

## Frozen fixture

Three nested chromosomes with ten unique genes and twelve memberships.
Two genes are shared across chromosomes, but each is evaluated only once.
Five explicit contexts have expected eligible IDs:

| Context tags | Eligible IDs |
| --- | --- |
| research | a, b, c |
| research, public | a, c |
| review | j |
| empty | none |
| research, review | a, b, c, j |

The tests also cover subtree selection, order invariance, global cap,
scope isolation, malformed catalogs, disconnected cycles and depth limits.

Run after installing the package:
    python -m unittest discover -s tests -p 'test_genomememory_chromosomes.py' -v
    python -m unittest discover -s tests -v

## Limits and next gate

T02 is demonstrated in synthetic metadata only, not in native storage.
This is not a complete June appendix D proof loop: no gene creation,
actual expression, correction, persistent repair receipt or lineage replay
has been added. No biological genome or phage behavior is modeled.
No change to SQLite, existing lifecycle, R0.1 preview or operator plans.
Next: compare canonical representations independently, prove deduplication
and scope preservation under transformations; then source-bound adapters
with explicit missingness. Hard forget remains a separate retention design.
