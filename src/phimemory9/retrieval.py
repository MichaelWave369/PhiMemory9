"""R0.2 retrieval experiment: lexical baseline vs ancestry-aware lexical reranking.

Strictly deterministic, model-free, synthetic only. This is NOT a claim that
ΦMemory9 improves retrieval in real workloads or against embedding methods.
"""
from __future__ import annotations

import re
from typing import Any

from .core import MemoryEngine

STOP = frozenset(
    "a an and are at by did for from how in is it of on or the to was were "
    "what when where which who why with".split()
)


def tokens(value: str) -> frozenset[str]:
    return frozenset(
        part for part in re.findall(r"[a-z0-9]+", value.casefold())
        if part not in STOP
    )


def coverage(query: frozenset[str], text: str) -> float:
    return len(query & tokens(text)) / len(query) if query else 0.0


def search(
    engine: MemoryEngine, question: str, *, method: str = "lexical", k: int = 3
) -> list[dict[str, Any]]:
    """Same active candidate pool for both methods.

    ancestry method additionally consults the candidate's past (possibly
    retired) ancestors, weighting the best match by 0.65 * 0.7 ** (hop-1).
    Search does NOT infer contradictions or confirm factual correctness.
    """
    if method not in ("lexical", "ancestry"):
        raise ValueError("method must be lexical or ancestry")
    if k < 1 or k > 100:
        raise ValueError("k must be between 1 and 100")
    query = tokens(question)
    if not query:
        return []
    active_rows = engine.db.execute(
        "SELECT id,content,parent_memory_id,blob_id FROM memories "
        "WHERE status='active'"
    ).fetchall()
    ranked = []
    for row in active_rows:
        direct = coverage(query, row["content"])
        from_lineage = 0.0
        if method == "ancestry":
            visited = {row["id"]}
            parent = row["parent_memory_id"]
            hop = 1
            while parent is not None and hop <= 6:
                if parent in visited:
                    raise ValueError("Cycle in memory ancestry")
                visited.add(parent)
                ancestor = engine.memory(parent)
                from_lineage = max(
                    from_lineage,
                    coverage(query, ancestor["content"]) * 0.65 * (0.7 ** (hop - 1)),
                )
                parent = ancestor["parent_memory_id"]
                hop += 1
        score = direct + from_lineage
        if score > 0:
            ranked.append({
                "id": row["id"],
                "content": row["content"],
                "blob_id": row["blob_id"],
                "score": round(score, 6),
                "direct_score": round(direct, 6),
                "ancestry_bonus": round(from_lineage, 6),
            })
    ranked.sort(key=lambda x: (-x["score"], x["content"], x["id"]))
    return ranked[:k]


def benchmark_fixture() -> dict[str, Any]:
    """Runs two retrieval strategies over identical active synthetic candidates."""
    with MemoryEngine() as engine:
        blob = engine.create_blob("synthetic benchmark")
        old_a = engine.enter(
            blob, "North tower pressure gauge calibration flagged 15 PSI discrepancy"
        )
        current_a = engine.renew(
            old_a, "Current plant maintenance record N-15", "Replaced obsolete wording"
        )
        old_b = engine.enter(
            blob, "East bridge fiber optic link dropped because connector was dusty"
        )
        current_b = engine.renew(
            old_b, "Maintenance job EB-12 closed after cleaning", "Updated maintenance"
        )
        old_c = engine.enter(
            blob, "Orchard kiln temperature sensor K42 failed after nineteen hours"
        )
        current_c = engine.renew(
            old_c, "Thermal system case closed after component replacement",
            "Updated maintenance",
        )
        decoys = [
            "North tower manager wrote a new maintenance checklist",
            "West wing fiber optic link requires routing changes",
            "Orchard gardens sensor noted hydration limits",
            "Hydraulic pump measured 60 PSI after pressure test",
        ]
        for item in decoys:
            engine.enter(blob, item)
        direct_a = engine.enter(blob, "Coastal museum archive boxes were scanned")
        direct_b = engine.enter(blob, "Primary battery A7 telemetry healthy")
        direct_c = engine.enter(blob, "Rollout at station delta took three hours")
        cases = [
            ("north tower pressure gauge discrepancy", current_a),
            ("east bridge dusty connector fiber", current_b),
            ("orchard kiln temperature K42", current_c),
            ("coastal museum archive boxes", direct_a),
            ("primary battery A7 telemetry", direct_b),
            ("station delta rollout hours", direct_c),
        ]
        outcomes = []
        for query, expected_id in cases:
            lexical = search(engine, query, method="lexical", k=3)
            ancestry = search(engine, query, method="ancestry", k=3)
            def rank(results: list[dict[str, Any]]) -> int | None:
                return next(
                    (i + 1 for i, item in enumerate(results)
                     if item["id"] == expected_id),
                    None,
                )
            outcomes.append({
                "query": query,
                "expected": engine.memory(expected_id)["content"],
                "lexical_rank": rank(lexical),
                "ancestry_rank": rank(ancestry),
            })
        def metric(field: str) -> dict[str, float]:
            ranks = [row[field] for row in outcomes]
            return {
                "hit_at_1": round(
                    sum(rank == 1 for rank in ranks) / len(ranks), 6
                ),
                "hit_at_3": round(
                    sum(rank is not None for rank in ranks) / len(ranks), 6
                ),
                "mrr_at_3": round(
                    sum(1 / rank for rank in ranks if rank is not None) / len(ranks),
                    6,
                ),
            }
        return {
            "schema": "phi-memory9/retrieval-benchmark-r0.2",
            "fixture": "synthetic versioned-memory retrieval; no real data",
            "query_count": len(cases),
            "active_candidate_count": engine.db.execute(
                "SELECT COUNT(*) FROM memories WHERE status='active'"
            ).fetchone()[0],
            "methods": {
                "lexical": metric("lexical_rank"),
                "ancestry": metric("ancestry_rank"),
            },
            "queries": outcomes,
            "limitations": (
                "Ancestry method has additional access to historical wording; "
                "neither method uses embeddings. Curated synthetic queries cannot "
                "establish general superiority or real-world accuracy."
            ),
        }
