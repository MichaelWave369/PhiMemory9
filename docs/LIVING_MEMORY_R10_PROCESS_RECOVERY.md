# Living Memory R10.6 — process interruption and mutation boundaries

Base f2b19dc3d158e63322fecb1a8d4750a4f227d892. Disposable synthetic stores
only; production remains HELD.

## Abrupt exit protocol

Nine regression methods launch a fresh Python subprocess against two
disposable fixture database files. The worker invokes the real storage
and packet APIs, then exits with os._exit(91), without finally blocks,
connection close or interpreter cleanup. Parent checks the expected exit
code and opens the pair through the public fixture recovery API.

Test interruption after nested operation completion but before the outer
commit, immediately after the real outer commit, and between guard and
main writes. SQL trace hooks exit before the selected next statement;
these are API/statement boundaries, not arbitrary SQLite internal
instruction or disk-write boundaries. Verify memory state, current
consent, policy, replay and receipt counts, receipt reuse, logical
scrubbing and SQLite integrity checks on both attached files. This is a
subprocess crash experiment, not a hardware power-loss test.

## Remaining mutation check/use gaps

Move the migration version check, gene capacity count, chromosome catalog
validation and correction replacement-state check inside the existing
BEGIN IMMEDIATE transaction. Four tests schedule a committed competing
operation on another independently opened connection just before the
outer lock. Expected results: repeat migration is a no-op, gene count
remains bounded at 256, forgotten membership is rejected, and a
replacement retired before correction is refused.

## Reproduction

    python -m unittest discover -s tests -p 'test_living_process_recovery_r10.py' -v
    python -m unittest discover -s tests -p 'test_living_mutation_boundaries_r10.py' -v
    python -m unittest discover -s tests -v

Thirteen new methods in total. Test results require actual execution;
pre-patch failures were inferred from source, not measured.

## Limits

Small transactions on ordinary local SQLite fixtures are the test scope.
No forced cache spill, hot-journal recovery qualification, interruption
inside SQLite commit internals, filesystem/power-loss, network filesystem
or unsupported journal-mode guarantee. The read-only open preflight may
need a separate explicitly authorized recovery design for hot journals.
No recovery of a lost external effect, hostile-host defense or independent
security certification. The current guard cannot detect restoration of
both files. No change to schema, wire format or action authority.

Next: external continuity witness contract and both-file rollback
counterexamples, followed by independent review.
