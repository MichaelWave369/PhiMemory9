# GenomeMemory369 R0.9 — local integration harness

Synthetic only, authority NONE, no native deployment. This ninth rung composes
R0.1–R0.8 functions in one Python process using only invented fixed fixtures.
PhiOS README at 43620d38d6164b3579d61784cdb140462501ff1f was inspected:
capability is not authority; retrievable is not admissible; observation is
not truth. The harness is consistent with those distinctions but does not
import PhiOS or connect to its memory, shell, app platform or runtime.
No change to PhiOS, PhiGenesis, Memoria or SML repositories.

## Two deliberately separate input lanes

Memoria-shaped and SML-shaped metadata use their pinned fixture adapters.
Both candidates remain HELD with nine missing policy values. They are
not converted into memory genes or admitted to learning. Separate invented
observations carry explicitly supplied synthetic gene policy and matching
retention node IDs. R0.1 flat and R0.2 nested preview are compared; shared
membership must be deduplicated. R0.3 binds the catalog, request and result.
R0.7 constructs a hypothetical revoke plan; an explicit synthetic overlay
marks affected genes needs_review and R0.8 excludes their dependent
observations from all splits. The overlay is not durable or a real policy
enforcement mechanism. The invented observations are not retrieved from
the source metadata lane; the preview and learner share fixture IDs, not a
general adapter from memory content to numerical observations.

R0.6 references a combined commitment to both staged source snapshots,
the R0.3 receipt and R0.8 report, plus a separate commitment to the
hypothetical hold and authority NONE. It checks explicit source, destination,
purpose, expiry, payload/policy references and original envelope digest.
A compatible packet can describe a failed learning experiment; it remains
HELD and cannot execute. No payload dispatch, runtime call or real authority.

## Fixed scenarios and expected outcomes

| Scenario | Preview count | Learning | Packet |
| --- | ---: | --- | --- |
| baseline | 7 | audit matched, 2/2 test | compatible, HELD |
| contradiction | 7 | train contradiction | compatible, HELD |
| withdrawal | 4 | audit matched, 1/1 test | compatible, HELD |
| expired | 7 | audit matched | incompatible, HELD |
| wrong_destination | 7 | audit matched | incompatible, HELD |
| tampered | 7 | audit matched | incompatible, HELD |
| insufficient | 5 | underdetermined | compatible, HELD |

These are authored regression expectations, not independently collected
evidence. Seven scenarios each perform eight composite checks. The test
suite adds seven unittest methods, including CLI exit code checks and
deterministic receipt replay. The failed learning/packet cases are intended
negative controls, not successful predictions or authorized actions.
A scenario receipt binds its observed diagnostic output; the top-level
receipt binds the seven ordered scenario records and readiness blockers.
These are not authenticated signatures or proof of actual erasure.

## Run locally

    python -m pip install -e .
    python -m phimemory9.genomememory_integration report
    python -m phimemory9.genomememory_integration gate
    python -m unittest discover -s tests -p 'test_genomememory_integration.py' -v
    python -m unittest discover -s tests -v

Report exits 0 only if the synthetic expectations match, else 1.
Gate exits 3 even when the experimental suite passes, else 1.
The gate is deliberately static, not a live readiness detector.
No external input files, service connections, model calls or state writes
are required by the harness. Existing package and CI tests are unchanged.

## Readiness remains blocked

1. Native source exports and authorized read access.
2. Authenticated endpoints and consent lifecycle.
3. Enforced revocation and verified storage erasure.
4. Durable replay and restore guards.
5. Cross-language contract conformance.
6. Independent evaluation and security review.
7. Native PhiOS and PhiGenesis runtime integration.

R0.9 completes the initial synthetic research ladder, conditional on test
results, not the original June MVP or a production integration. In
particular, persistent gene creation, expression receipts, actual repair,
lineage replay of real memory and hard forgetting remain unimplemented.
PhageLedger's separate biological literature governance atlas is outside
this software experiment. No biological operation or claim of general
intelligence. Next: independent review of the exact merged ladder and a
read-only native handoff contract with a permanently held default.
