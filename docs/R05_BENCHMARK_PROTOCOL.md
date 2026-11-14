# ΦMemory9 R0.5 · Frozen Synthetic Retrieval Comparison

## Purpose

R0.2's original six examples favor ancestry-aware lexical retrieval by construction.
R0.5 deliberately *does not claim to fix that flaw*. Instead it expands the
transparent synthetic fixture, adds a sparse TF-IDF vector baseline, evaluates
unanswerable queries, and prints every query and result so regressions and
false positives are visible.

Run:
~~~sh
phi-memory9 benchmark-r05
python -m unittest discover -s tests -v
~~~

The fixture is defined in \`src/phimemory9/benchmark_r05.py\` and the report
includes a SHA-256 digest of all source texts, queries, and heuristic thresholds.

## Frozen split and candidate pool

- 12 **historical-wording** queries: the requested terms appear mainly in a
  now-retired predecessor; the expected answer is its current descendant.
- 12 **current-wording** queries: the expected active memory directly contains
  the requested terms.
- 12 **unanswerable negative controls**: queries are not supported by the
  corresponding records; some deliberately overlap ordinary topical nouns.
- 24 active candidate memories shared across retrieval approaches and 12
  retired ancestor records (available only to history-aware approaches).
- All data are invented engineering stories. No user records or internet access.
- No model training, scoring parameter fitting, prompt optimization, or tuning
  on this fixture takes place.

This is **not** an independently assembled real-world held-out test set.
The original R0.2 stories and these R0.5 stories are distinct, but authoring
fixtures in the same project is not independent validation.

## Four deterministic methods

| Method | Information | Algorithm | Abstention cutoff |
| --- | --- | --- | --- |
| \`lexical\` | Active text only | R0.2 query-token coverage | 0.60 |
| \`ancestry\` | Active + retired parent text | R0.2 discounted parent bonus | 0.55 |
| \`sparse\` | Active text only | L2-normalized, IDF-weighted sparse cosine | 0.48 |
| \`sparse_history\` | Active + up to six ancestors | Same TF-IDF cosine on merged tokens | 0.48 |

All thresholds are **fixed heuristics**, not calibrated probabilities. All
methods rank the same 24 active memory IDs; history-aware methods can consult
retired predecessors as an extra source of information. TF-IDF sparse vectors
are not neural embedding models, so no claim about embedding-search
performance is valid.

## Metrics and interpretation

- Hit@1 and Hit@3: expected memory appears in first 1/3 returned candidates.
- MRR@3: mean reciprocal expected-result rank, zero for missing.
- Negative false-accept count: unanswerable query still produces a returned
  candidate. Lower is desirable, but can reduce recall elsewhere.

The report prints exact query-level ranks, abstentions, and top texts. It may
show a history-aware advantage on archival-wording questions; that is
**expected given its additional access to historical descriptions**. Such a
result does not establish a better cognitive memory architecture, factual
correctness, or production task value.

## Next harder gate

Before any performance claims: evaluate a larger externally collected,
licensed corpus with independent human labels, query family disjointness,
equal information budgets, a current neural embedding baseline, prior
threshold registration, storage/latency cost measurements and statistical
uncertainty. Preserve failures and negative outcomes.
