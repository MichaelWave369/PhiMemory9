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

## R0.5: gated local memory and frozen retrieval evaluation

The localhost-only read API now requires a fresh high-entropy bearer access key
printed by `phi-memory9 serve`. Enter the key in the local React inspector.
The key stays in browser-tab memory and **is never sent in a URL**. Static
demo access is unaffected. The API remains read-only, and operator-approved
local CLI plans remain the only way to apply mutations. See
[access and threat model](docs/LOCAL_ACCESS_R05.md).

The new deterministic **36-query synthetic** benchmark compares lexical
retrieval, ancestry-aware lexical retrieval, sparse TF-IDF on current content
and sparse TF-IDF with ancestral text. It includes negative queries, fixed
abstention thresholds, and a manifest SHA-256:

~~~sh
phi-memory9 benchmark-r05
~~~

This is a transparent, authored test fixture, **not** an independently
collected real-world held-out evaluation or proof of superior retrieval.
See [R0.5 benchmark protocol](docs/R05_BENCHMARK_PROTOCOL.md).

## R0.4: approved memory operations and privacy exports

A **separate local CLI** now accepts strict JSON mutation plans that require
an exact SHA-256 digest from the explicit `plan-review` step. All memory
changes and approval receipts commit or roll back together; duplicate plans
are rejected. The read-only React inspector adds a **Plan Builder** which
downloads a proposal but **never writes to the server**.

~~~sh
phi-memory9 plan-review --db ./lab.sqlite3 --plan ./proposed-loop.json
phi-memory9 apply-plan --db ./lab.sqlite3 --plan ./proposed-loop.json --approve-sha256 REVIEWED_DIGEST
phi-memory9 export-memory --db ./lab.sqlite3 --memory MEMORY_ID --out ./metadata-export.json
~~~

Full-content exports require a second, content-bound digest approval.
See [governance and privacy documentation](docs/GOVERNED_PLANS_R04.md).

## R0.3: inspect real local SQLite memory

Run a separate **read-only** local memory viewer from the project checkout:

~~~sh
phi-memory9 seed-lab --db ./lab.sqlite3
cd web && npm install && npm run build && cd ..
phi-memory9 serve --db ./lab.sqlite3
~~~

Open **http://127.0.0.1:8769/PhiMemory9/** on the same computer. The Living Memory Inspector reads actual blobs, memory records, ancestry, declared claims, contradictions, and stored LOOP events. **Only** `seed-lab` writes a new, synthetic database and it refuses to overwrite files. The local server has **no write endpoint**. See [R0.3 local setup and safety](docs/LOCAL_LAB_R03.md).

The visual nine-stage gear remains a separate simulation, even in local mode. Neither this viewer nor the public/static React page can access your database unless you explicitly start the local loopback service. Do not expose the loopback service or use it with sensitive memories.

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

**Status:** R0.5 token-gated local reader and frozen synthetic retrieval benchmark, with R0.4 operator-approved mutation plans, R0.3 local SQLite inspector, R0.2 evidence, and R0.1 lifecycle core. Not integrated with PhiStream, Altermath, PhiDiscovery, Sovereign Memory Lattice, or SuperPhiVessel. No agent authority, no network transport, and no automatic cross-system memory sharing.

Read [Architecture](docs/ARCHITECTURE.md) and [the Python example](examples/nested_demo.py).

MIT licensed.
