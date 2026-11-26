"""Synthetic-only GenomeMemory expression preview. No I/O or execution."""

from collections.abc import Mapping

FIELDS = frozenset({"gene_id", "project", "privacy", "consent", "repair",
                    "confidence", "claim", "source_refs", "activate", "suppress"})
ENUMS = {
    "privacy": {"public", "personal", "private", "sensitive"},
    "consent": {"safe_to_use", "soft_sensitive", "ask_first", "receipt_required",
                "never_infer", "never_act_without_consent"},
    "repair": {"clean", "stale", "contradicted", "needs_review", "archived"},
    "confidence": {"low", "medium", "high", "verified", "disputed", "deprecated"},
    "claim": {"fact", "hypothesis", "analogy", "speculation"},
}


def _label(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError("invalid label")
    if not all(c.isascii() and (c.isalnum() or c in "._:-") for c in value):
        raise ValueError("invalid label")
    return value


def _labels(value):
    if not isinstance(value, (list, tuple)) or len(value) > 64:
        raise ValueError("expected bounded label list")
    labels = [_label(item) for item in value]
    if len(set(labels)) != len(labels):
        raise ValueError("duplicate label")
    return frozenset(labels)


def preview(genes, project, context_tags, limit=3):
    """Return IDs and reason codes for invented fixture metadata only.

    Caller must not supply real memory. No authorization or meaning is emitted.
    """
    project = _label(project)
    tags = _labels(context_tags)
    if type(limit) is not int or not 0 <= limit <= 9:
        raise ValueError("invalid preview limit")
    if not isinstance(genes, (list, tuple)) or len(genes) > 256:
        raise ValueError("expected bounded candidate list")
    validated = {}
    for gene in genes:
        if not isinstance(gene, Mapping) or set(gene) != FIELDS:
            raise ValueError("invalid gene fields")
        gid = _label(gene["gene_id"])
        if gid in validated:
            raise ValueError("duplicate gene ID")
        _label(gene["project"])
        for key, allowed in ENUMS.items():
            if not isinstance(gene[key], str) or gene[key] not in allowed:
                raise ValueError("invalid " + key)
        refs, activate, suppress = (_labels(gene[key]) for key in
                                    ("source_refs", "activate", "suppress"))
        validated[gid] = (dict(gene), refs, activate, suppress)

    decisions = []
    eligible = []
    for gid in sorted(validated):
        gene, refs, activate, suppress = validated[gid]
        if gene["project"] != project:
            reason = "scope_mismatch"
        elif gene["privacy"] != "public":
            reason = "privacy_hold"
        elif gene["repair"] != "clean":
            reason = "repair_hold"
        elif gene["consent"] != "safe_to_use":
            reason = "consent_hold"
        elif suppress & tags:
            reason = "suppression_match"
        elif not refs:
            reason = "source_missing"
        elif gene["confidence"] not in ("high", "verified"):
            reason = "confidence_hold"
        elif gene["claim"] != "fact":
            reason = "claim_hold"
        elif not activate or not activate <= tags:
            reason = "activation_missing"
        elif len(eligible) >= limit:
            reason = "limit_hold"
        else:
            eligible.append(gid)
            reason = "preview_eligible"
        decisions.append({"gene_id": gid, "reason": reason})
    return {"schema": "genomememory-preview/r0.1", "synthetic": True,
            "authority": "NONE", "eligible_ids": eligible, "decisions": decisions}
