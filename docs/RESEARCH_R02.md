# ΦMemory9 R0.2: evidence ledger and retrieval baseline

**Scope:** deterministic, local, offline, opt-in research prototype. It neither fact-checks sources nor makes autonomous decisions about which beliefs to preserve.

## Source-backed claims

The R0.2 \`EvidenceLedger\` attaches to the existing \`MemoryEngine\` SQLite database. It creates separate tables; existing R0.1 memories and event rows are unchanged.

The API supports:
- \`source(label, locator, kind, independence_group, declared_sha256)\`: register a source *pointer*. Hashes are supplied by the operator and are not independently obtained or checked against the source.
- \`claim(memory_id, statement)\`: register an interpretation linked to an existing memory.
- \`attach(claim_id, source_id, stance, excerpt)\`: record a source relationship as \`support\`, \`challenge\`, or \`context\`.
- \`contradiction(claim_a, claim_b, reason)\`: explicitly link two interpretations without automatically deciding which is correct.
- \`report(claim_id)\`: reveal attachments, declared independence groups, contradiction links and conservative classification.
- \`export(claim_id)\`: explicit local evidence packet with ancestry. **It does not transmit anything.**
- \`audit()\`: rehash stored records, validate the chained evidence events, verify base memory integrity and detect broken foreign keys.

Both the source independence group and the evidence stance are *operator declarations*. The summary never labels a claim as true, proven, or scientifically confirmed. Five sources derived from one feed count as one declared group. The default group is \`unverified\` for precisely that reason.

Audit integrity detects accidental mutations and some localized corruption. It does **not** provide trusted timestamps, immutable storage guarantees, digital signatures, tamperproof auditing, or protection against an attacker who can rewrite both data and hashes.

## Quick local experiment

~~~python
from phimemory9 import MemoryEngine
from phimemory9.evidence import EvidenceLedger

with MemoryEngine() as m:
    blob = m.create_blob("local lab")
    mid = m.enter(blob, "A sensor reading was recorded.", "fixture:sensor")
    e = EvidenceLedger(m)
    src = e.source("synthetic log", "fixture:log", kind="synthetic")
    first = e.claim(mid, "The sensor is operational")
    second = e.claim(mid, "The sensor is not operational")
    e.attach(first, src, "context", excerpt="A reading exists")
    e.contradiction(first, second, "Interpretations disagree")
    print(e.report(first))
    print(e.audit())
~~~

\`EvidenceLedger\` does not change the existing \`liberation()\` packet format. For a claim that includes evidence, export \`e.export(claim_id)\` separately; those packets can expose full content and must be manually reviewed for privacy.

## Retrieval experiment

\`phi-memory9 benchmark\` runs a **small synthetic corpus** of 6 queries against two approaches using the same active-memory candidate set:

| Method | Description |
|---|---|
| \`lexical\` | Fraction of query tokens appearing directly in an active memory |
| \`ancestry\` | Same direct lexical score plus a discounted score for wording in an ancestor memory, including retired ancestors |

It reports Hit@1, Hit@3, and MRR@3, plus every query's expected result and observed rank. Candidate lists contain active memories only. Both methods see the same active candidates; the ancestry method intentionally accesses stored historical wording. This is a test of **versioned-memory wording recovery**, not a fair comparison against an embedding model or a general semantic search system.

The fixture is intentionally tiny, hand-built and favorable to historical lexical recovery. Positive results cannot demonstrate overall superiority; negatives must be retained. No parameter tuning, hidden model execution, scientific discovery, or real-world inference has been performed.

Run:

~~~sh
python -m pip install -e .
phi-memory9 benchmark
python -m unittest discover -s tests -v
~~~

## Next milestone

- Privacy and permission classification for source/citation exports.
- Proper schema migration checks and write-once controls.
- Larger, pre-registered held-out comparison including a true vector-search baseline.
- An explicit localhost API for the React visual lab, **not** a direct connection from a public site to a private SQLite file.
- Separate governance adapters to Sovereign Memory Lattice, PhiDiscovery, and SuperPhiVessel after validated benchmarks.
