"""Canonical integrity of synthetic metadata, not semantic truth or authorization."""
import hashlib
import json

from .genomememory_chromosomes import chromosome_preview

SET_FIELDS = {"source_refs", "activate", "suppress", "gene_ids"}
GOVERNANCE_FIELDS = {"project", "privacy", "consent", "repair", "confidence",
                     "claim", "activate", "suppress"}


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(domain, value):
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + _bytes(value)).hexdigest()


def _canonical_row(row):
    return {key: sorted(value) if key in SET_FIELDS else value
            for key, value in row.items()}


def _validated(genes, chromosomes, root_id, project, context_tags, limit):
    result = chromosome_preview(genes, chromosomes, root_id, project,
                                context_tags, limit)
    state = {
        "schema": "genomememory-catalog/r0.3",
        "genes": sorted((_canonical_row(g) for g in genes),
                        key=lambda g: g["gene_id"]),
        "chromosomes": sorted((_canonical_row(c) for c in chromosomes),
                              key=lambda c: c["chromosome_id"]),
    }
    request = {"root_id": root_id, "project": project,
               "context_tags": sorted(context_tags), "limit": limit}
    return state, request, result


def receipt(genes, chromosomes, root_id, project, context_tags, limit=3):
    """Return domain-separated digests only; synthetic metadata, no payload."""
    state, request, result = _validated(genes, chromosomes, root_id, project,
                                        context_tags, limit)
    catalog_hash = _digest("genomememory/catalog/r0.3", state)
    request_hash = _digest("genomememory/request/r0.3", request)
    result_hash = _digest("genomememory/result/r0.3", result)
    binding = {"catalog_sha256": catalog_hash, "request_sha256": request_hash,
               "result_sha256": result_hash}
    return {"schema": "genomememory-integrity/r0.3", "synthetic": True,
            "authority": "NONE", **binding,
            "receipt_sha256": _digest("genomememory/receipt/r0.3", binding)}


def compare(before, after):
    """Compare two complete argument dictionaries; no claim of meaning equality.

    Both sides must be valid under R0.2. Compare normalized records directly
    rather than treating an equal output or hash as proof of equivalence.
    """
    left, lreq, lresult = _validated(**before)
    right, rreq, rresult = _validated(**after)
    old = {g["gene_id"]: g for g in left["genes"]}
    new = {g["gene_id"]: g for g in right["genes"]}
    identity_changed = old.keys() != new.keys()
    fields = set()
    for gid in old.keys() & new.keys():
        fields.update(k for k in old[gid] if old[gid][k] != new[gid][k])
    topology_changed = left["chromosomes"] != right["chromosomes"]
    return {
        "schema": "genomememory-comparison/r0.3",
        "synthetic": True, "authority": "NONE",
        "catalog_equivalent": left == right,
        "request_equivalent": lreq == rreq,
        "preview_equivalent": lresult == rresult,
        "identity_set_changed": identity_changed,
        "topology_changed": topology_changed,
        "governance_fields_changed": sorted(fields & GOVERNANCE_FIELDS),
        "provenance_changed": "source_refs" in fields,
        "changed_gene_fields": sorted(fields),
    }
