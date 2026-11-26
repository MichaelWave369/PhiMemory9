"""Synthetic retention impact planning; no mutation, deletion or authorization."""
from collections.abc import Mapping
from .genomememory_preview import _label, _labels
from .genomememory_integrity import _digest

SCHEMA = "genomememory-retention-fixture/r0.7"
KINDS = {"memory", "descendant", "export", "index", "backup", "packet", "cache"}
ACTIONS = {"correct", "retire", "revoke", "forget"}
COVERAGE = {"declared_complete", "partial", "unknown"}
MAX_NODES = 256


def _fixture_id(value):
    value = _label(value)
    if not value.startswith("fixture:") or value == "fixture:":
        raise ValueError("expected fixture identifier")
    return value


def _validated(inventory):
    if not isinstance(inventory, Mapping) or set(inventory) != {
            "schema", "synthetic", "fixture_id", "nodes", "coverage"}:
        raise ValueError("invalid inventory")
    if inventory["schema"] != SCHEMA or inventory["synthetic"] is not True:
        raise ValueError("synthetic fixture required")
    fid = _fixture_id(inventory["fixture_id"])
    coverage = inventory["coverage"]
    if not isinstance(coverage, Mapping) or set(coverage) != KINDS:
        raise ValueError("explicit coverage required for every storage kind")
    if any(not isinstance(v, str) or v not in COVERAGE for v in coverage.values()):
        raise ValueError("invalid coverage")
    rows = inventory["nodes"]
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= MAX_NODES:
        raise ValueError("invalid node count")
    nodes = {}
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"node_id", "kind", "depends_on"}:
            raise ValueError("invalid node fields")
        nid = _fixture_id(row["node_id"])
        kind = row["kind"]
        if not isinstance(kind, str) or kind not in KINDS or nid in nodes:
            raise ValueError("invalid kind or duplicate ID")
        parents = sorted(_labels(row["depends_on"]))
        for parent in parents:
            _fixture_id(parent)
        if (kind == "memory" and parents) or (kind != "memory" and not parents):
            raise ValueError("invalid root or missing dependency")
        nodes[nid] = {"node_id": nid, "kind": kind, "depends_on": parents}
    if any(p not in nodes for row in nodes.values() for p in row["depends_on"]):
        raise ValueError("unknown dependency; declare coverage gaps separately")
    # Kahn traversal validates the entire DAG, even unrelated branches.
    pending = set(nodes)
    ordered = []
    resolved = set()
    while pending:
        ready = sorted(n for n in pending if set(nodes[n]["depends_on"]) <= resolved)
        if not ready:
            raise ValueError("dependency cycle")
        ordered.extend(ready)
        resolved.update(ready)
        pending.difference_update(ready)
    state = {"schema": SCHEMA, "synthetic": True, "fixture_id": fid,
             "coverage": dict(coverage), "nodes": [nodes[n] for n in sorted(nodes)]}
    return state, nodes, ordered


def plan(inventory, target, action, *, replacement=None):
    """Plan conservative transitive holds and review obligations, never apply."""
    state, nodes, ordered = _validated(inventory)
    target = _fixture_id(target)
    if target not in nodes or nodes[target]["kind"] not in ("memory", "descendant"):
        raise ValueError("target must be known memory or descendant")
    if not isinstance(action, str) or action not in ACTIONS:
        raise ValueError("invalid action")
    if action == "correct":
        replacement = _fixture_id(replacement)
        if replacement in nodes:
            raise ValueError("correction requires a fresh proposed identity")
    elif replacement is not None:
        raise ValueError("replacement only allowed for correction")

    affected = {target}
    for nid in ordered:
        if affected.intersection(nodes[nid]["depends_on"]):
            affected.add(nid)

    obligations = []
    for nid in sorted(affected):
        kind = nodes[nid]["kind"]
        if action == "forget":
            task = {"memory": "review_content_erasure", "descendant": "review_derived_erasure",
                    "export": "review_recipient_copy_removal", "index": "review_index_removal",
                    "backup": "review_backup_retention_and_restore_block",
                    "packet": "review_packet_revocation_and_copies",
                    "cache": "review_cache_invalidation"}[kind]
        elif action == "correct":
            task = "review_supersession" if nid == target else "review_dependency_repair"
        elif action == "retire":
            task = "review_retirement" if nid == target else "review_dependent_suppression"
        else:
            task = "review_permission_revocation"
        obligations.append({"node_id": nid, "kind": kind, "proposed_hold": True,
                            "task": task, "status": "UNVERIFIED"})
    gaps = sorted(k for k, v in state["coverage"].items() if v != "declared_complete")
    body = {"schema": "genomememory-retention-plan/r0.7", "synthetic": True,
            "authority": "NONE", "action": action, "target": target,
            "proposed_replacement": replacement, "replacement_eligible": False,
            "inventory_sha256": _digest("genomememory/retention-inventory/r0.7", state),
            "coverage_gaps": gaps, "affected_count": len(affected),
            "obligations": obligations, "status": "REVIEW_REQUIRED",
            "applied": False, "erasure_verified": False}
    return {**body, "plan_sha256": _digest("genomememory/retention-plan/r0.7", body)}
