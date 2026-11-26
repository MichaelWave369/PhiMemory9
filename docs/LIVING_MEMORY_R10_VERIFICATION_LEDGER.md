# Living Memory R10.8 — reproducible adversarial verification package

Scope: synthetic disposable stores, no production authorization. This package
is prepared by the same research collaboration; independently implemented
reference calculations are not an independent external security review.

## Verified upstream revision register

The following exact PR heads had completed successful PR-triggered workflows
when queried. #17–#24 below are merged to main; #25 was open at the time of
inspection. The audit branch starts at #25's exact tested head.

| PR | Head | Workflow | Purpose |
|---|---|---|---|
| #17 | 7d4f1300d9f699372b3ecf71b165a6969c9a9fbf | 45894673892 | Promote persistent candidate |
| #18 | 6c387d083fa8d4900783a6707b0ed4fe7fb6be7c | 45896489493 | Lifecycle fidelity |
| #20 | 24d26f56f3d4d4602d63b974174c7bae8dafc76e | 45897731070 | Receipt schema, cache and chronology |
| #21 | d125b9f5c57b45ef9bb992adf776fbaf82885632 | 45898617248 | Source reentry guard |
| #22 | 4f074b9087e0ca449b6ccf0d5909b3b9d366e801 | 45899074720 | Idempotent forgetting |
| #23 | c98135b9beae8e25caf42dfd1861ebe571bb390f | 45900233272 | Transaction boundaries |
| #24 | a7a395b2299a798d6a5534068f68ca72e4853e6e | 45905174125 | Process recovery |
| #25 | bf5d96327fece26650cbbb7cfdb5c6f0e185d544 | 45907752182 | Native continuity witness |

Use https://github.com/MichaelWave369/PhiMemory9/actions/runs/{workflow}
for the recorded workflow. Main observed at 7138bc4ea58e1f49754c7261e517d4190a514a01.
Workflow conclusions are observed metadata, not a fresh independent execution.

## Test inventory on the #25 head

| Test module (tests/) | Methods | Git blob |
|---|---:|---|
| test_living_recovery_r10.py | 4 | fed222ea50b08f1039fb724c8fa5e0799011a365 |
| test_living_receipt_r10.py | 6 | 481038d367b662a53b9bef2ef51941e501337467 |
| test_living_source_reentry_r10.py | 8 | f8107b5a5c84a704e5d97f41a1e4e267550b01a4 |
| test_living_forget_recovery_r10.py | 8 | 546b2abadcc101cbe8bf05a5d42ef89e6e72c609 |
| test_living_transactions_r10.py | 10 | c11db6ea3b0bbb11a1889b04f491b284d55bfe3a |
| test_living_process_recovery_r10.py | 9 | 0e6211f25dda05d87984ed5a4c44ad904aa5611f |
| test_living_mutation_boundaries_r10.py | 4 | 0d86b296358c43ba4a552e50343665236ebd5be0 |
| test_living_continuity_r10.py | 7 | 5c768d56508f0c88a1ccc5771a84e00c1179ce08 |

56 existing R10 test methods, including one opt-in native test (nine native
checks inside that method). Six additional methods in this increment bring
the inventory to 62; these counts are source counts, not pass counts.

## Independent implementation comparison

The reference in tests/living_continuity_reference.py does not import the
snapshot implementation, its serialization helpers or MemoryEngine. It
opens the two closed fixture files independently in read-only mode, sorts
the SQL catalog and encoded rows, constructs length frames with struct.pack,
and uses one-shot hmac.digest. The producer uses an attached locked snapshot
and incremental HMAC. Both share Python JSON, SQLite and HMAC primitives;
this is a same-author, same-language differential check, not independent
cryptographic verification. The reference is intentionally not suitable
for concurrently changing files or real personal stores.

The six new tests compare transitions, receipt/replay binding, paired
rollback, wrong keys, schema and row changes, and unsupported row types.
They must actually execute before being marked passed.

## Reproduce

    python -m pip install -e .
    python -m unittest discover -s tests -p 'test_living_*_r10.py' -v
    python -m unittest discover -s tests -v

For the optional native test, use a trusted local checkout of NBGPocketMesh
at 0687f10970989194d4af554d9b189c7ce8a1ad15 and set
LIVING_NATIVE_POCKETMESH to its absolute checkout path; Node 20+ required.
The existing living-native CI job executes this test with a pinned checkout.

## Remaining gates

- Independent external reviewer and security sign-off: NOT OBTAINED.
- Distinct packet/receipt MAC domains, identity/key custody and trusted time.
- Actual independent administration and enforced external continuity,
  including promotion/commit recovery and authority unavailability.
- Source identity aliases, older scrubbed IDs, shared siblings and
  untracked copies; no complete erasure or semantic identity claim.
- SQLite hot-journal, arbitrary internal commit interruption and physical
  durability. No universal concurrency proof.
- Snapshot byte budget is checked during framing, not before every SQL
  row materialization or serialization. Not a hostile database parser.
- Native source security, SML store export and real memory bridge.
- Production remains HELD; no personal store or runtime authority granted.

R10 research increment can be reviewed and reproduced without claiming
these gates are complete. R11 should begin with a source-native Memoria
authorization and storage audit, while external review remains open.
