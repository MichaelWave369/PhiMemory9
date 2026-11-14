# ΦMemory9

**ΦPMA-9 | Recursive Altermath Memory** is an experimental, local-first, event-sourced memory engine. It models nine *operations*, not biological or metaphysical claims:

1. **ENTER** — ingest content with provenance.
2. **BIRTH** — establish a new, addressable memory.
3. **DEATH** — retire an interpretation without deleting evidence.
4. **TRANSFER** — transmit a traceable descendant to another blob.
5. **REBIRTH** — create a reinterpreted descendant.
6. **RESTORE** — reactivate a retired interpretation with a recorded reason.
7. **RENEW** — supersede an interpretation with a revised descendant.
8. **LIBERATION** — produce a portable, source-linked export.
9. **LOOP** — route a descendant across nested blobs using an explicit gear decision.

A **blob** is an addressable memory context; blobs may nest. The ninth gear can stay inside the current blob, route inward, move outward, transfer laterally, or seed a new root. There is **no unsupervised autonomous spawning** in R0.1; explicit decisions, depth limits, loop budgets, and duplicate detection prevent uncontrolled growth.

## Quick start

Python 3.10+; standard-library core, no API keys and no network access:

~~~sh
python -m pip install -e .
python -m unittest discover -s tests -v
phi-memory9 demo
phi-memory9 demo --db ./phi-memory9.sqlite3
phi-memory9 verify --db ./phi-memory9.sqlite3
~~~

Run the interactive demo directly from source:

~~~sh
PYTHONPATH=src python examples/nested_demo.py
~~~

## Core contracts

- SQLite keeps original text, immutable source references, parent/child lineage, and append-only events. **DEATH never erases a memory.**
- A renewed or reborn memory is a **new identifier**, never a silent overwrite.
- Each operation is recorded with a timestamp, operation name and machine-readable payload.
- An optional source reference establishes an attribution pointer, **not** independent verification.
- A LOOP chooses a route under explicit operator control. The default route is **hold**.
- Repeated identical content within one blob is rejected; depth and loop limits are enforced.
- No claims that the nine-stage metaphor improves retrieval have yet been established. Comparative benchmarks are future work.

**Status:** R0.1 research prototype. Not integrated with PhiStream, Altermath, PhiDiscovery, Sovereign Memory Lattice, or SuperPhiVessel. No agent authority, no network transport, and no automatic cross-system memory sharing.

Read [Architecture](docs/ARCHITECTURE.md) and [the Python example](examples/nested_demo.py).

MIT licensed.
