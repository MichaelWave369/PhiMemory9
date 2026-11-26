# Living Memory R10 — recovery lifecycle audit, first increment

Base: 7d4f1300d9f699372b3ecf71b165a6969c9a9fbf, the merge of #16
into the audit branch. Promotion to main is separately tracked by #17.
This is a scoped source audit and regression patch, not an external independent
security certification.

## Finding R10-01: cold restart collapses lifecycle distinctions

In v1, repair(target, retire) sets the target retired; correction/supersession
sets it superseded. All affected descendants are held. reconcile_guard(),
called on open, previously mapped every non-forget block to held, even if the
current main file already recorded the matching terminal state. This erases
lifecycle distinctions during ordinary cold reconstruction. Access remained
denied; this is a fidelity defect, not evidence of disclosure.

The guard stores a block action for each affected ID, not the target/descendant
role. It is insufficient to reconstruct the exact pre-restore lifecycle state
after restoring a stale main file. Preserve a matching retired/superseded state
when already present; otherwise conservatively hold. A newer revocation
must still produce held. Forget logic, authenticated access checks, consent,
guard schema and storage formats remain unchanged.

## Regressions

Four new disposable-store methods: repeated retirement recovery, correction
recovery, main-only restoration without invented terminal status, and a newer
revocation overriding retirement. Check access denial and unrelated replacement
preservation. The first two are counterexamples to the previous code by source
inspection; pre-fix execution is not claimed.

    python -m unittest discover -s tests -p 'test_living_recovery_r10.py' -v

This patch is not a full R10 acceptance result. Next adversarial review targets:
receipt schema/domain separation and event freshness; source identity reentry
under a new gene ID; both-file rollback; idempotence of repeated forget
reconciliation; cross-process timing and transaction boundaries. Test fixtures
only; no real data or live exploitation. Current trusted-host model and
production HELD remain unchanged. No external verifier or security sign-off.
