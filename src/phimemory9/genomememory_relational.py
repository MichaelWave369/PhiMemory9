"""Finite affine relation experiment inspired by PhiGenesis 007; synthetic only."""
from collections.abc import Mapping

from .genomememory_retention import plan, _validated, _fixture_id
from .genomememory_integrity import _digest

P = 31
FAMILY = tuple((a, b) for a in range(1, P) for b in range(P))
SPLITS = {"train", "audit", "test"}
DOMAIN = "genomememory/relational-experiment/r0.8"


def experiment(inventory, observations, *, hold_target=None):
    """Recompute from surviving observations; audit and test never fit a rule.

    Hold target is a synthetic revocation-plan target, not a real permission.
    No persistent state, execution, real-memory access or authorization.
    """
    state, nodes, ordered = _validated(inventory)
    if not isinstance(observations, (list, tuple)) or not 1 <= len(observations) <= 31:
        raise ValueError("invalid observation count")
    rows, ids, inputs = [], set(), set()
    for row in observations:
        if not isinstance(row, Mapping) or set(row) != {"node_id", "split", "x", "y"}:
            raise ValueError("invalid observation fields")
        nid = _fixture_id(row["node_id"])
        if nid not in nodes or nodes[nid]["kind"] not in ("memory", "descendant") or nid in ids:
            raise ValueError("unknown, duplicate or unsupported observation node")
        split = row["split"]
        if not isinstance(split, str) or split not in SPLITS:
            raise ValueError("invalid split")
        x, y = row["x"], row["y"]
        if any(type(v) is not int or not 0 <= v < P for v in (x, y)):
            raise ValueError("observation outside finite field")
        if x in inputs:
            raise ValueError("duplicate input across splits")
        ids.add(nid)
        inputs.add(x)
        rows.append(dict(row))
    rows.sort(key=lambda r: r["node_id"])
    # Split labels alone do not isolate evidence. Reject direct and transitive
    # ancestry between observations in different splits, before any hold can
    # hide that leakage. A common unobserved root is not proof of independence.
    split_by_id = {r["node_id"]: r["split"] for r in rows}
    ancestors = {}
    for nid in ordered:
        parents = set(nodes[nid]["depends_on"])
        ancestors[nid] = parents | set().union(*(ancestors[p] for p in parents))
        if nid in split_by_id and any(
                p in split_by_id and split_by_id[p] != split_by_id[nid]
                for p in ancestors[nid]):
            raise ValueError("cross-split observation ancestry")
    hold = plan(inventory, hold_target, "revoke") if hold_target is not None else None
    blocked = {o["node_id"] for o in hold["obligations"]} if hold else set()
    admitted = {split: [r for r in rows if r["split"] == split and r["node_id"] not in blocked]
                for split in sorted(SPLITS)}
    excluded = sorted(ids & blocked)
    train, audit, test = (admitted[s] for s in ("train", "audit", "test"))
    candidates = [(a, b) for a, b in FAMILY
                  if all((a*r["x"]+b) % P == r["y"] for r in train)]
    rule = None
    audit_matches = None
    test_matches = None
    if not candidates:
        status = "TRAIN_CONTRADICTION"
    elif len(candidates) != 1:
        status = "UNDERDETERMINED"
    elif not audit:
        status = "AUDIT_MISSING"
    else:
        a, b = candidates[0]
        audit_matches = sum((a*r["x"]+b) % P == r["y"] for r in audit)
        if audit_matches != len(audit):
            status = "AUDIT_REJECTED"
        else:
            status = "AUDIT_MATCHED"
            rule = [a, b]
            test_matches = sum((a*r["x"]+b) % P == r["y"] for r in test) if test else None
    # All input observations, including exclusions, are committed. Synthetic only:
    # retaining such a commitment is not a real-world forget policy.
    body = {
        "schema": "genomememory-relational-report/r0.8", "synthetic": True,
        "authority": "NONE", "family_size": len(FAMILY), "status": status,
        "candidate_count": len(candidates), "rule": rule,
        "admitted_ids": {s: [r["node_id"] for r in admitted[s]] for s in admitted},
        "excluded_ids": excluded,
        "audit_matches": audit_matches, "audit_count": len(audit),
        "test_matches": test_matches, "test_count": len(test),
        "inventory_sha256": _digest("genomememory/retention-inventory/r0.7", state),
        "observations_sha256": _digest(DOMAIN+"/observations", rows),
        "hold_plan_sha256": hold["plan_sha256"] if hold else None,
        "coverage_gaps": sorted(k for k, v in state["coverage"].items() if v != "declared_complete"),
        "certified": False, "eligible": False,
    }
    return {**body, "report_sha256": _digest(DOMAIN+"/report", body)}
