"""Bounded nested chromosome grouping for synthetic GenomeMemory fixtures.

Groups are selectors, not grants. Every selected gene still passes R0.1.
No database, filesystem, network, payload release, or authority.
"""
from collections.abc import Mapping
from .genomememory_preview import preview, _label, _labels

GROUP_FIELDS = frozenset({"chromosome_id", "project", "parent_id", "gene_ids"})
MAX_GROUPS = 64
MAX_DEPTH = 6


def chromosome_preview(genes, chromosomes, root_id, project, context_tags, limit=3):
    """Select one subtree, deduplicate memberships, and run the R0.1 gate.

    All inputs are validated, including unselected branches. Membership is
    many-to-many within one project; each group has at most one parent.
    All genes must belong to at least one group. Root depth is one.
    """
    root_id, project = _label(root_id), _label(project)
    # Validate the entire gene catalog, not just the selected subtree.
    preview(genes, project, context_tags, limit=0)
    if type(limit) is not int or not 0 <= limit <= 9:
        raise ValueError("invalid preview limit")
    catalog = {row["gene_id"]: row for row in genes}
    if not isinstance(chromosomes, (list, tuple)) or not 1 <= len(chromosomes) <= MAX_GROUPS:
        raise ValueError("invalid chromosome count")
    groups = {}
    linked = set()
    for group in chromosomes:
        if not isinstance(group, Mapping) or set(group) != GROUP_FIELDS:
            raise ValueError("invalid chromosome fields")
        cid = _label(group["chromosome_id"])
        scope = _label(group["project"])
        parent = group["parent_id"]
        if parent is not None:
            parent = _label(parent)
        members = _labels(group["gene_ids"])
        if cid in groups:
            raise ValueError("duplicate chromosome ID")
        for gid in members:
            if gid not in catalog:
                raise ValueError("unknown gene")
            if catalog[gid]["project"] != scope:
                raise ValueError("cross-project membership")
        groups[cid] = (scope, parent, members)
        linked.update(members)
    if linked != set(catalog):
        raise ValueError("ungrouped gene")

    # Validate each ancestry chain, including disconnected roots.
    for cid, (scope, _, _) in groups.items():
        path = set()
        node = cid
        while node is not None:
            if node not in groups:
                raise ValueError("unknown parent")
            if node in path:
                raise ValueError("chromosome cycle")
            path.add(node)
            if len(path) > MAX_DEPTH:
                raise ValueError("chromosome depth exceeded")
            node_scope, node, _ = groups[node]
            if node_scope != scope:
                raise ValueError("cross-project ancestry")

    if root_id not in groups or groups[root_id][0] != project:
        raise ValueError("root unavailable in project")

    selected = set()
    membership_count = 0
    chromosome_count = 0
    for cid, (_, _, members) in groups.items():
        node = cid
        while node is not None and node != root_id:
            node = groups[node][1]
        if node == root_id:
            selected.update(members)
            membership_count += len(members)
            chromosome_count += 1

    report = preview([catalog[gid] for gid in sorted(selected)],
                     project, context_tags, limit)
    return {
        "schema": "genomememory-chromosomes/r0.2",
        "synthetic": True,
        "authority": "NONE",
        "chromosome_count": chromosome_count,
        "membership_count": membership_count,
        "unique_gene_count": len(selected),
        "duplicate_memberships": membership_count - len(selected),
        "eligible_ids": report["eligible_ids"],
        "decisions": report["decisions"],
    }
