# Operation Living Memory — controlling addendum and acceptance v1

Authority: operator mission dated 2026-11-26, attached `Pasted text.txt`.
This versioned addendum preserves all R0 APIs and the original June documents.
Candidate scope: disposable synthetic stores only, no deployment, private-store
migration, registration, model invocation, dispatch or execution authority.

## Acceptance frozen before implementation

| ID | Requirement / owner | Verification | Dependency |
|---|---|---|---|
| LM-R1 | PhiMemory9: reproduce baseline; reject cross-split ancestry | 124 prior tests, 56 harness checks; inverse-arithmetic oracle; adversarial ancestry controls | exact main 5cba675a3a439023a3ff374c238dd6e4339e3a55 |
| LM-R2 | PhiMemory9: versioned fixture overlay on MemoryEngine; tokens, genes, groups, tags, events, lineage, consent, obligations | atomic rollback, reopen reconstruction, shared memberships, unknown schema refusal | R1; existing transaction API |
| LM-R3 | Memoria: read-only metadata projection with explicit app read permission; held staging | native disposable DB; content/metadata exclusion; denied scope; source revision binding | security audit; real stores remain blocked |
| LM-R4 | PhiMemory9/XiPhiOmega: scoped nested/flat metadata contract | frozen ASCII integer-only vectors, separate Node implementation, native XPO-002 round trip | R2; no geometric complexity without benefit |
| LM-R5 | PhiMemory9: persisted scoped consent and current policy commitments | missing/expired/withdrawn consent, wrong purpose/app/project, suppression, stale commitments, events | R2; fixture operator trust only |
| LM-R6 | PhiMemory9: authenticated local packet admission, receipt lineage, durable replay | HMAC fixture identities, current policy and destination key checks, expiry, idempotency, restart | R5; no network or execution |
| LM-R7 | PhiMemory9: transitive holds and logical deletion, separate revocation guard | shared ancestry, local indexes/caches, rollback, backup restore, fresh process, unknown copies | R2/R5; never claim physical erasure |
| LM-R8 | PhiMemory9/PhiGenesis: persistent governed affine experiment | train/audit/test split isolation, cold/simple baselines, acquisition/validation/compute costs, revision after withdrawal | R5/R7; native PhiGenesis fixture comparison |
| LM-R9 | PhiOS: strictly advisory intake; reproducible native fixture demonstration | source/export/store/integrity/consent/packet/learning/revoke/restart; HELD at PhiOS boundary | R2–R8; unresolved gates stay blocked |

## Readiness and boundaries

All rungs target research candidates, not production completion. A hash is not
truth, authentication or consent. HMAC shared-key fixture authentication is not
an externally verified identity or asymmetric signature. Same-author oracles
are separate implementations, not independent external audits. A local guard
protects against restoring only the memory DB; it cannot survive rollback or
deletion of the guard itself. Hard deletion coverage of backups, native source
stores, unknown recipients, OS pages and physical media is unresolved.

Missing native governance stays unknown; no source importance/proof score
becomes confidence, consent or authority. New fixture consent must be issued
explicitly by the local synthetic operator. Reuse existing native components
through optional source paths; do not copy private source into public repos.

## Historical sources

Both original documents were found and their extracted text inspected. June
GenomeMemory sections 7–18 and Appendix D agree with the vocabulary and proof
loop above. PhageLedger section 9 supplies the software analogy; its separate
literature-atlas roadmap is outside this mission. Historical byte fingerprints
remain as recorded in GENOMEMEMORY_RECONCILIATION_R01.md; this session has not
independently rehashed the original DOCX bytes. Original bytes are not published.

## Threat model

Consider malformed metadata, replay, substituted receipts, stale consent,
cross-scope requests, restored stale stores, derived-data resurrection, split
leakage and inconsistent graph updates. Trust the fixture operator, explicit
local key configuration and operating system. A malicious process with write
access to both store and guard, key theft, hostile source checkouts, real-world
identity proof, side channels, secure deletion and production transport are
outside the demonstrated boundary and remain blockers.
