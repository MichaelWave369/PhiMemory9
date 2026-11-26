"""Synthetic SML metadata projection. No payload, execution, or authority."""
from collections.abc import Mapping
import hmac
import math
import re
from datetime import datetime

from .genomememory_preview import _label, _labels
from .genomememory_integrity import _digest

REVISION = "43f7513c46529167d842a7c195029b03574dc393"
SCHEMA = "genomememory-sml-fixture/r0.5"
DOMAIN = "genomememory/sml-fixture/r0.5"
SCORES = ("coherence_score", "novelty_score", "proof_score", "field_score",
          "consensus_score", "dispute_score")
LISTS = ("contributors", "intent_tags", "role_tags", "links", "parent_ids")
FIELDS = {"memory_id", "author_agent_id", "timestamp", "state", "collab_state",
          "fork_group_id", *SCORES, *LISTS}
STATES = {"active", "embalmed", "shadow", "released"}
COLLAB = {"local_only", "shared_candidate", "shared_verified", "disputed", "forked", "sealed"}
POLICY = ("project", "privacy", "consent", "repair", "confidence",
          "claim", "source_refs", "activate", "suppress")
STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                   r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?")


def _canonical(snapshot, expected_fixture):
    expected_fixture = _label(expected_fixture)
    if not isinstance(snapshot, Mapping) or set(snapshot) != {
            "schema", "synthetic", "source_revision", "fixture_id", "packets"}:
        raise ValueError("invalid fixture envelope")
    if (snapshot["schema"] != SCHEMA or snapshot["synthetic"] is not True
            or snapshot["source_revision"] != REVISION
            or not expected_fixture.startswith("fixture:")
            or snapshot["fixture_id"] != expected_fixture):
        raise ValueError("fixture scope or revision mismatch")
    packets = snapshot["packets"]
    if not isinstance(packets, (list, tuple)) or not 1 <= len(packets) <= 256:
        raise ValueError("invalid packet count")
    seen = set()
    normalized = []
    for packet in packets:
        if not isinstance(packet, Mapping) or set(packet) != FIELDS:
            raise ValueError("invalid projection; payload and receipts forbidden")
        mid = _label(packet["memory_id"])
        if mid in seen:
            raise ValueError("duplicate memory ID")
        seen.add(mid)
        _label(packet["author_agent_id"])
        if packet["fork_group_id"] is not None:
            _label(packet["fork_group_id"])
        for key, allowed in (("state", STATES), ("collab_state", COLLAB)):
            if not isinstance(packet[key], str) or packet[key] not in allowed:
                raise ValueError("invalid " + key)
        stamp = packet["timestamp"]
        if not isinstance(stamp, str) or not STAMP.fullmatch(stamp):
            raise ValueError("invalid timestamp")
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        row = dict(packet)
        for key in SCORES:
            score = packet[key]
            if type(score) not in (int, float) or not 0 <= score <= 1 or not math.isfinite(score):
                raise ValueError("invalid " + key)
            row[key] = float(score) if score else 0.0
        for key in LISTS:
            row[key] = sorted(_labels(packet[key]))
        if mid in row["links"] or mid in row["parent_ids"]:
            raise ValueError("self reference")
        normalized.append(row)
    return {"schema": SCHEMA, "synthetic": True, "source_revision": REVISION,
            "fixture_id": expected_fixture,
            "packets": sorted(normalized, key=lambda p: p["memory_id"])}


def review_snapshot(snapshot, expected_fixture):
    state = _canonical(snapshot, expected_fixture)
    return {"schema": "genomememory-sml-review/r0.5", "synthetic": True,
            "authority": "NONE", "packet_count": len(state["packets"]),
            "snapshot_sha256": _digest(DOMAIN, state)}


def stage_snapshot(snapshot, expected_fixture, reviewed_sha256):
    state = _canonical(snapshot, expected_fixture)
    digest = _digest(DOMAIN, state)
    if (not isinstance(reviewed_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", reviewed_sha256)
            or not hmac.compare_digest(digest, reviewed_sha256)):
        raise ValueError("review commitment mismatch")
    ids = {p["memory_id"] for p in state["packets"]}
    candidates = []
    for p in state["packets"]:
        candidates.append({
            "source_identity": {"system": "SML", "source_revision": REVISION,
                                "fixture_id": expected_fixture, "memory_id": p["memory_id"]},
            "source_metadata": p,
            "unresolved_links": sorted(set(p["links"]) - ids),
            "unresolved_parents": sorted(set(p["parent_ids"]) - ids),
            "policy": dict.fromkeys(POLICY),
            "status": "HELD", "eligible": False,
            "reason": "missing_explicit_genomememory_policy",
        })
    return {"schema": "genomememory-sml-staging/r0.5", "synthetic": True,
            "authority": "NONE", "snapshot_sha256": digest,
            "eligible_count": 0, "candidates": candidates}
