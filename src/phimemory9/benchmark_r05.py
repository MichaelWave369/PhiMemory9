"""Frozen synthetic R0.5 evaluation: current text vs ancestry retrieval.

Zero model calls, no external datasets, no dependencies and no fine-tuning.
Family-separated from the earlier R0.2 six-query exercise. Report all misses.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any

from .core import MemoryEngine
from .retrieval import coverage, search, tokens

# Handwritten, frozen *new* families. The expected target is always ACTIVE.
# Data is synthetic and must not be treated as realistic field performance.
HISTORY_CASES = (
    ("North observatory magnetometer drift came from cracked ceramic bracket",
     "OBS-47 repair work order was closed",
     "north observatory magnetometer cracked ceramic"),
    ("Harbor weather buoy radio outage traced to corroded copper connector",
     "Coastal maintenance ticket CB-92 completed",
     "harbor weather buoy corroded copper connector"),
    ("Forest canopy lidar scanner lost calibration during freezing rainfall",
     "Field survey ticket FC-28 completed",
     "forest canopy lidar scanner freezing rainfall"),
    ("Substation transformer thermal anomaly caused by a failed cooling fan",
     "Grid maintenance ticket GS-61 completed",
     "substation transformer thermal anomaly cooling fan"),
    ("Mountain seismograph clock drift began after quartz oscillator failure",
     "Geology repair note MG-13 archived",
     "mountain seismograph quartz oscillator clock drift"),
    ("Wetland acoustic recorder failed because water entered microphone seal",
     "Ecology service record EC-35 completed",
     "wetland acoustic recorder microphone water seal"),
    ("Campus ethernet switch outage followed damaged fiber splice in conduit",
     "Network ticket NW-72 closed after repair",
     "campus ethernet switch damaged fiber splice"),
    ("Greenhouse irrigation monitor sent false readings from mineral buildup",
     "Agriculture repair ticket AG-81 completed",
     "greenhouse irrigation monitor mineral buildup"),
    ("River turbine vibration traced to unbalanced steel rotor blades",
     "Hydropower service note HP-26 closed",
     "river turbine vibration unbalanced rotor"),
    ("Desert telescope tracking motor stalled after gearbox bearing seizure",
     "Astronomy ticket AS-08 resolved",
     "desert telescope tracking gearbox bearing"),
    ("Ice core freezer alarm triggered by defective door gasket seal",
     "Cold storage note CS-14 closed",
     "ice core freezer defective gasket"),
    ("Museum humidity gauge displayed drift from saturated polymer sensor",
     "Preservation ticket MU-63 archived",
     "museum humidity gauge polymer sensor"),
)

CURRENT_CASES = (
    ("Mars habitat oxygen scrubber uses activated carbon cartridges",
     "mars habitat oxygen scrubber activated carbon"),
    ("Coastal drone navigation checks compass offsets each morning",
     "coastal drone navigation compass offsets"),
    ("Aquarium research tank maintains stable saline water temperature",
     "aquarium research tank saline temperature"),
    ("Library archive uses sealed archival boxes for fragile maps",
     "library archive sealed boxes fragile maps"),
    ("Field robot detects roadside obstacles using stereo cameras",
     "field robot roadside obstacles stereo cameras"),
    ("Volcanic soil lab catalogs basalt samples by microscope image",
     "volcanic soil basalt microscope samples"),
    ("Solar microgrid charges battery banks before evening peak demand",
     "solar microgrid battery banks evening peak"),
    ("Underwater glider reports depth using calibrated pressure sensors",
     "underwater glider calibrated depth pressure"),
    ("Railway signal controller records switching events to local storage",
     "railway signal switching events local storage"),
    ("Satellite uplink test measures transmission delay with timestamp pairs",
     "satellite uplink transmission delay timestamps"),
    ("Canyon trail sensor measures soil moisture after winter snowfall",
     "canyon trail soil moisture winter snowfall"),
    ("Wind farm maintenance crew checks blade tip erosion monthly",
     "wind farm blade tip erosion monthly"),
)

# Some negatives deliberately share a noun with a real document; absence
# should be judged with a frozen coverage/cosine threshold, not by "top-1".
NEGATIVES = (
    "north observatory magnetometer repaired by purple robots",
    "harbor buoy speaks twelve ancient languages",
    "forest canopy scanner predicts underground diamonds",
    "substation transformer generates infinite free energy",
    "mountain seismograph received musical tones from mars",
    "wetland acoustic recorder can teleport through weather",
    "campus ethernet switch predicts next year lottery",
    "greenhouse irrigation mineral buildup cures every illness",
    "river turbine unbalanced rotor makes ocean disappear",
    "desert telescope bearing records human dreams",
    "ice core freezer can create new continents",
    "museum humidity gauge uses quantum unicorn sensor",
)

# Chosen and frozen before evaluation. They are heuristic abstention gates,
# not calibrated probabilities or confidence intervals.
THRESHOLDS = {
    "lexical": 0.60,
    "ancestry": 0.55,
    "sparse": 0.48,
    "sparse_history": 0.48,
}
METHODS = tuple(THRESHOLDS)
MAX_HISTORY_HOPS = 6


def _tfidf_vector(words: frozenset[str], idf: dict[str, float]) -> dict[str, float]:
    weights = {word: idf[word] for word in words if word in idf}
    length = math.sqrt(sum(x*x for x in weights.values()))
    return {word: value/length for word, value in weights.items()} if length else {}


def _tfidf_rank(engine: MemoryEngine, question: str, history: bool) -> list[dict]:
    active = [
        dict(r) for r in engine.db.execute(
            "SELECT id,content,parent_memory_id FROM memories WHERE status='active'"
        ).fetchall()
    ]
    documents: list[tuple[dict, frozenset[str]]] = []
    for row in active:
        words = set(tokens(row["content"]))
        if history:
            cursor = row["parent_memory_id"]
            hops = 0
            visited = {row["id"]}
            while cursor is not None and hops < MAX_HISTORY_HOPS:
                if cursor in visited:
                    raise ValueError("Ancestry cycle")
                visited.add(cursor)
                parent = engine.memory(cursor)
                words.update(tokens(parent["content"]))
                cursor = parent["parent_memory_id"]
                hops += 1
        documents.append((row, frozenset(words)))
    n = len(documents)
    counts: Counter[str] = Counter()
    for _, words in documents:
        counts.update(words)
    idf = {word: math.log((n + 1) / (freq + 1)) + 1 for word,freq in counts.items()}
    qvec = _tfidf_vector(tokens(question), idf)
    output: list[dict] = []
    for row, words in documents:
        vector = _tfidf_vector(words, idf)
        score = sum(weight*vector.get(word,0.0) for word,weight in qvec.items())
        if score > 0:
            output.append({"id": row["id"], "content": row["content"], "score": score})
    output.sort(key=lambda r: (-r["score"], r["content"], r["id"]))
    return output


def _rank(engine: MemoryEngine, question: str, method: str) -> list[dict]:
    if method in ("lexical", "ancestry"):
        # R0.2 scoring preserved; all candidate results requested (bounded).
        results = search(engine, question, method=method, k=100)
    else:
        results = _tfidf_rank(engine, question, history=method=="sparse_history")
    return [r for r in results if r["score"] >= THRESHOLDS[method]][:3]


def _metric(ranks: list[int | None]) -> dict[str, float]:
    n = len(ranks)
    return {
        "hit_at_1": round(sum(r==1 for r in ranks)/n, 6),
        "hit_at_3": round(sum(r is not None for r in ranks)/n, 6),
        "mrr_at_3": round(sum(1/r for r in ranks if r is not None)/n, 6),
    }


def run_heldout_r05() -> dict[str, Any]:
    fixture = {
        "history_cases": HISTORY_CASES,
        "current_cases": CURRENT_CASES,
        "unanswerable_queries": NEGATIVES,
        "thresholds": THRESHOLDS,
        "max_hops": MAX_HISTORY_HOPS,
    }
    manifest = hashlib.sha256(
        json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with MemoryEngine() as engine:
        blob = engine.create_blob("frozen R0.5 synthetic research collection")
        tests: list[tuple[str, str, str | None]] = []
        for old, current, query in HISTORY_CASES:
            old_id = engine.enter(blob, old)
            new_id = engine.renew(old_id, current, "Synthetic version update")
            tests.append(("historical_wording", query, new_id))
        for current, query in CURRENT_CASES:
            identity = engine.enter(blob, current)
            tests.append(("current_wording", query, identity))
        for query in NEGATIVES:
            tests.append(("negative", query, None))
        results: list[dict] = []
        for group, query, expected in tests:
            observed: dict[str, Any] = {}
            for method in METHODS:
                retrieved = _rank(engine, query, method)
                rank = (next((i+1 for i,item in enumerate(retrieved)
                              if item["id"] == expected), None)
                        if expected is not None else None)
                observed[method] = {
                    "rank": rank,
                    "abstained": not bool(retrieved),
                    "top_match": engine.memory(retrieved[0]["id"])["content"]
                    if retrieved else None,
                }
            results.append({"group": group, "query": query, "results": observed})
        positive = {
            method: {
                group: _metric([
                    item["results"][method]["rank"] for item in results
                    if item["group"] == group
                ])
                for group in ("historical_wording", "current_wording")
            }
            for method in METHODS
        }
        negatives = {
            method: {
                "false_accept_count": sum(
                    not item["results"][method]["abstained"]
                    for item in results if item["group"] == "negative"
                ),
                "queries": len(NEGATIVES),
            }
            for method in METHODS
        }
        return {
            "schema": "phi-memory9/retrieval-heldout-r0.5",
            "manifest_sha256": manifest,
            "data_type": "frozen synthetic examples; NOT real-world held-out evidence",
            "active_candidates": len(CURRENT_CASES) + len(HISTORY_CASES),
            "historical_ancestor_records": len(HISTORY_CASES),
            "query_count": len(tests),
            "thresholds": THRESHOLDS,
            "positive": positive,
            "negative_controls": negatives,
            "queries": results,
            "limitations": (
                "All examples are hand-authored, synthetic and published with the code. "
                "No tuning was conducted against this fixture, but it is not an independently "
                "collected holdout. Ancestry methods access retired wording that direct methods "
                "do not; sparse TF-IDF is not a neural embedding baseline. "
                "Scores are uncalibrated heuristics; no superiority, statistical significance "
                "or factual correctness can be inferred."
            ),
        }
