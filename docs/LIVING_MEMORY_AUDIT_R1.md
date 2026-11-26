# Living Memory R1 audit

Baseline: 5cba675a3a439023a3ff374c238dd6e4339e3a55. PRs 6–14 are
merged; all exact final PR heads have completed successful Actions workflows.
The baseline main push workflow also succeeded. Exact revisions and workflow
IDs are in living-memory/baseline-remote-v1.json. Local baseline: 124/124 test
methods; unified harness: seven scenarios × eight checks = 56/56.

## Reproduced defect LM-001

The R0.8 relational experiment accepted a training observation whose ancestry
included a test observation, and an audit observation depending transitively
on a test observation. Both returned a learned rule instead of refusing the
evaluation. Counterexamples were executed before the repair: two assertion
failures in five tests, preserved in r1-counterexamples-before.txt.

Repair: validate transitive observation ancestry across all splits before
retention filtering or fitting. Reject cross-split ancestry in either direction.
Existing fixtures sharing an unobserved background root remain accepted;
their statistical independence is not thereby established. Separate modular
inverse arithmetic agrees with the enumerative implementation for all 930
nonconstant affine maps, with 1,860 held-out predictions. This is a separate
same-author oracle, not external or PhiCleanroom certification.

After repair: 129/129 test methods. Training remains invariant under a change
to held-out answers; that change reduces test matches from 2 to 1. Recomputing
a PhageLedger receipt and every expected commitment still returns HELD with
no authority. No operational transport or real authorization existed in R0.

## Other reviewed boundaries

- R0.1–R0.3 validate exact fields, enum values, duplicate IDs, labels,
  memberships, scopes, ancestry cycles and depth before canonical hashing.
  Set-like fields normalize order. Integrity covers hidden governance and
  topology, but is unkeyed and proves no source truth.
- R0.4/R0.5 are fixture adapters. All nine policy fields remain unknown;
  synthetic source staging never grants expression permission.
- R0.6 always holds, even when caller-selected expectations all match.
  It has no authenticated identity, durable replay or current policy state.
- R0.7 computes obligations; none are applied. R0.8 still commits to withdrawn
  fixture observations, so it must not be used as a hard-forget implementation.
- Memoria source confirms unchecked read/semantic/delete/permission endpoints,
  default write allowance, deterministic fallback key derivation, plaintext
  vector documents and deletion limited to SQL. Real memory integration is
  blocked. A separate metadata-only fixture exporter does not repair that API.
- SML native lifecycle/collaboration and heuristic scores are distinct from
  authorization and evidence. Its native metadata may be projected for local
  fixtures; private source is not copied into this public repository.
- PhiCleanroom's current independent worker verifies a specific exact-title
  function contract; applying that certification to memory would be false.
  PhiProof's existing checks establish narrow arithmetic/signature properties,
  not consent or the scientific truth of memory contents.

No additional defect has been established by this bounded audit. This is not
an exhaustive security review. Readiness criteria and remaining trust boundaries
are frozen in LIVING_MEMORY_ACCEPTANCE_V1.md.
