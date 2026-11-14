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

## R0.2: evidence, contradictions and retrieval

The optional `EvidenceLedger` layer adds source pointers, operator-declared claims,
support/challenge/context links, recorded contradictions, declared independence
groups, and a hash-checked event chain. It **does not validate the truth of claims**
or automatically infer contradictory conclusions. R0.1 memories remain intact.

```sh
phi-memory9 evidence-demo
phi-memory9 benchmark
phi-memory9 verify-evidence --db ./phi-memory9.sqlite3
```

The benchmark compares an active-memory lexical baseline to ancestry-aware
reranking on **six hand-built synthetic queries**. Neither is a vector model;
the dataset favors historic-wording recovery and is not evidence of general
retrieval superiority. See [R0.2 Research](docs/RESEARCH_R02.md).

## React visual lab

The `web/` directory contains a **synthetic, browser-only** nine-stage visual lab. It illustrates nested blobs and operator-selected LOOP routing; it does **not** read or write the SQLite engine.

~~~sh
cd web
npm install
npm run dev
~~~

Use `npm run build` in `web/` for static GitHub Pages-compatible assets (base path `/PhiMemory9/`). Hosting is **not enabled by this commit**.

Run the Python demo directly from source:

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
- No validated retrieval superiority is claimed. The R0.2 tiny synthetic comparison is exploratory only.

**Status:** R0.2 research prototype with R0.1 lifecycle core. Not integrated with PhiStream, Altermath, PhiDiscovery, Sovereign Memory Lattice, or SuperPhiVessel. No agent authority, no network transport, and no automatic cross-system memory sharing.

Read [Architecture](docs/ARCHITECTURE.md) and [the Python example](examples/nested_demo.py).

MIT licensed.
