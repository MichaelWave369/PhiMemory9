# GenomeMemory369 R0.8 — governed relational learning experiment

Synthetic-only, offline, authority NONE. Inspired by PhiGenesis experiment
007 and its separation of discovery and evaluation; source inspected at
bfedf68cbc7649adb13da97a78a61e68bbf3d970 (README.md,
experiments/phi_genesis_007.py, docs/genesis-field-v02.md and
docs/genesis-field-v10-rc2.md). This is not a native PhiGenesis runtime
adapter or a replacement for its RC2 journal. No model calls or real data.

## Frozen hypothesis family and procedure

The externally chosen family is f(x) = (a*x+b) mod 31 for a=1..30,
b=0..30. Exactly 930 invertible affine maps. The learner enumerates all
candidates consistent with admitted training observations. Distinct inputs
across all splits prevent direct input reuse. Zero candidates means
TRAIN_CONTRADICTION; multiple means UNDERDETERMINED. A unique candidate
requires at least one audit observation; any audit mismatch rejects it.
Audit data does not select or refit a candidate. Test data is used only to
count matches after audit acceptance, not to select or promote rules.
AUDIT_MATCHED is deliberately not certification. Sparse tests cannot rule
out an unseen nonlinear counterexample, and the grammar is supplied.

## Retention composition

experiment(inventory, observations, hold_target=None) validates the R0.7
dependency inventory and 1–31 synthetic observations. Each observation has
exactly node_id, split, x, y. The ID resolves uniquely to a memory or
descendant node; x and y are integers in [0,30], with no bool coercion;
split is train, audit or test. Unknown and duplicate IDs, reused x values,
invalid schema or graph are rejected. A supplied hold_target is passed
directly to the R0.7 revoke planner. The full downstream closure is excluded
from every split before learning; recompute from scratch rather than
incrementally preserving previously learned coefficients. The hold is a
hypothetical experimental intervention, not an authenticated revocation.

Report binds full inventory, all input observations, hypothetical hold plan,
admitted IDs by split, excluded IDs, candidate count, rule when audit
matches, evaluation counts and coverage gaps with domain-separated SHA-256.
No rule is returned on contradiction, underdetermination, missing audit
or audit failure. Test mismatch is reported without altering the selected
rule; the result remains certified false, eligible false and authority NONE.
All digests and IDs are synthetic diagnostics, not privacy-safe deletion
receipts. Real forgetting must not retain a commitment to forgotten content
without explicit retention justification.

## Acceptance protocol

Eight unittest methods include exhaustive recovery of all 930 maps on a
fixed seven-observation split (three training, two audit, two test), 1860
test predictions; a contradictory training observation whose source hold
also excludes audit/test descendants; loss of support and abstention;
audit rejection and missing audit; test mismatch without refitting;
order invariance, coverage reporting and malformed inputs. Counts describe
the designed test workload, not independently measured generalization or
observed CI status. No claims of causal truth, discovery of the grammar,
general intelligence, sentience or superiority. No transfer experiment yet.

    python -m unittest discover -s tests -p 'test_genomememory_relational.py' -v
    python -m unittest discover -s tests -v

## Next

R0.9 should provide a local end-to-end fixture harness with explicit
readiness blockers, negative controls and reproducible receipts.
Real PhiGenesis/PhiOS integration requires authenticated governance,
source-native adapters, actual revocation and retention enforcement,
independent review and separately collected evaluation. Do not promote
synthetic results into live runtime permissions.
