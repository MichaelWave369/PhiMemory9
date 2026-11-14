# ΦPMA-9 Architecture: R0.1 core + R0.2 evidence and retrieval

## Nine operations, not a compulsory linear life

The stages are verbs available to an evidence-preserving memory record:

| Stage | Meaning | Invariant |
| --- | --- | --- |
| ENTER | Content enters a blob | Source pointer may be stored; no truth promotion |
| BIRTH | A new memory identifier exists | Stable ID, content fingerprint, source lineage |
| DEATH | An interpretation is retired | Never deletes the content or history |
| TRANSFER | Existing content enters another blob | Child points back to source |
| REBIRTH | A new interpretation derives from prior material | Distinct child ID and content |
| RESTORE | Reinstates a retired interpretation | Explicit recorded reason required |
| RENEW | An updated version supersedes the prior one | Old text remains; new child and reason |
| LIBERATION | Portable snapshot is exported locally | No automatic publishing or external transmission |
| LOOP | Ninth gear routes lineage to a new context | Explicit route and bounded budget |

A memory enters with an ENTER/BIRTH pair, but other operations are contingent. A useful stable observation does **not** have to "die" or undergo all nine transitions.

## The ninth gear

Route decisions: hold (default), inward (create child blob), outward (parent blob), lateral (operator-selected blob), seed (new root). Route decisions and resulting child IDs are recorded in the source memory's append-only event history. Every routed transfer preserves a lineage pointer.

Safety constraints in R0.1:
- Max nesting depth 6, max 512 blobs per database, max 9 LOOP events per memory.
- Identical content within a given blob cannot be inserted twice.
- No network adapters, model calls, inference permissions, automatic agent routing, or silent exports.
- LOOP decisions are explicitly made by the caller, never inferred from mythology or an unverified theory.
- The code enforces graph ancestry acyclicity through fresh IDs and immutable parent links.
- A source pointer is metadata, not a proof of source quality or factual certainty.

## Evidence ledger and retrieval (R0.2)

A separate local `EvidenceLedger` provides operator-declared evidence
attachments, explicit contradictions, source-dependency groups, and an
auditable hash chain. This does not alter nine-stage memory events or decide
which claims are correct. A hash chain is not tamperproof storage.

`retrieval.py` offers basic lexical and ancestry-augmented lexical retrieval,
plus a tiny synthetic benchmark. Read [R0.2 Research](RESEARCH_R02.md) for
exact scoring, known biases, and limitations.

## React visualization

`web/` is an explicitly synthetic browser simulator. It visually steps through the nine stages, displays a nested blob tree, and allows an operator to select a ninth-gear route. It is deliberately not connected to the SQLite runtime: UI graph nodes and event messages are illustrative, not canonical memory receipts. React/Vite builds are checked in CI.

## Intentional limitations

- SQLite is a local single-process prototype; concurrency/transaction robustness beyond SQLite defaults is not established.
- No embeddings, production-quality search, access-control layer, or schema migrations yet; only a deliberately narrow synthetic retrieval fixture.
- No data retention policy or privacy classification. Do not store secrets or sensitive user data in this experimental version.
- LIBERATION exports full text and provenance; callers must review privacy and permission boundaries before sharing.
- No demonstrated empirical advantage over vector search, event sourcing, or ordinary knowledge graphs.
- NBG/Altermath is an **architecture metaphor and research inspiration**, not a proved physical/mathematical law.

## Next research milestones

1. Counterexample and adversarial tests for lineage cycles, transfer duplication, and bounded recursive routing.
2. Immutable evidence bundles with citation-level provenance and contradictions (potential PhiDiscovery adapter).
3. Retrieval benchmark against full-text and vector baselines, using equal memory/compute budgets.
4. Opt-in import/export adapters for SML, PhiStream, SuperPhiVessel; preserve governance at each boundary.
5. Versioned storage migrations, permissions, and redaction before any real personal memory deployment.
