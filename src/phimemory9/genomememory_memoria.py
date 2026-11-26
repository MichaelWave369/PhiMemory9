"""Memoria-shaped synthetic metadata intake, never a live database adapter."""
from collections.abc import Mapping
from datetime import datetime
import hmac
import math
import re

from .genomememory_preview import _label, _labels
from .genomememory_integrity import _digest

SOURCE_REVISION = "9c480fcaea467615252d347956eac42ff038edf7"
SNAPSHOT_SCHEMA = "genomememory-memoria-fixture/r0.4"
SNAPSHOT_FIELDS = {"schema", "synthetic", "source_revision", "fixture_id", "rows"}
ROW_FIELDS = {"id", "app_name", "agent_id", "timestamp", "tags",
              "importance_score", "encrypted"}
POLICY_FIELDS = ("project", "privacy", "consent", "repair", "confidence",
                 "claim", "source_refs", "activate", "suppress")
DOMAIN = "genomememory/memoria-fixture/r0.4"
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                       r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?")


def _canonical(snapshot, expected_app):
    expected_app = _label(expected_app)
    if not isinstance(snapshot, Mapping) or set(snapshot) != SNAPSHOT_FIELDS:
        raise ValueError("invalid snapshot fields")
    if (snapshot["schema"] != SNAPSHOT_SCHEMA or snapshot["synthetic"] is not True
            or snapshot["source_revision"] != SOURCE_REVISION):
        raise ValueError("unsupported fixture contract or source revision")
    fixture_id = _label(snapshot["fixture_id"])
    if not fixture_id.startswith("fixture:"):
        raise ValueError("expected explicit fixture namespace")
    rows = snapshot["rows"]
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= 256:
        raise ValueError("invalid fixture size")
    canonical = []
    seen = set()
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != ROW_FIELDS:
            raise ValueError("invalid metadata fields; payload is forbidden")
        rid = row["id"]
        if type(rid) is not int or not 1 <= rid <= 2**63 - 1 or rid in seen:
            raise ValueError("invalid or duplicate row ID")
        seen.add(rid)
        if _label(row["app_name"]) != expected_app:
            raise ValueError("application scope mismatch")
        _label(row["agent_id"])
        stamp = row["timestamp"]
        if not isinstance(stamp, str) or not TIMESTAMP.fullmatch(stamp):
            raise ValueError("invalid timestamp")
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        score = row["importance_score"]
        if type(score) not in (int, float) or not 0 <= score <= 1 or not math.isfinite(score):
            raise ValueError("invalid importance")
        encrypted = row["encrypted"]
        if type(encrypted) is not int or encrypted not in (0, 1):
            raise ValueError("invalid encrypted flag")
        canonical.append({**row, "tags": sorted(_labels(row["tags"])),
                          "importance_score": float(score) if score else 0.0})
    return {"schema": SNAPSHOT_SCHEMA, "synthetic": True,
            "source_revision": SOURCE_REVISION, "fixture_id": fixture_id,
            "expected_app": expected_app,
            "rows": sorted(canonical, key=lambda r: r["id"])}


def review_snapshot(snapshot, expected_app):
    """Preview a commitment to exact normalized fixture metadata and scope."""
    state = _canonical(snapshot, expected_app)
    return {"schema": "genomememory-memoria-review/r0.4",
            "synthetic": True, "authority": "NONE",
            "row_count": len(state["rows"]),
            "snapshot_sha256": _digest(DOMAIN, state)}


def stage_snapshot(snapshot, expected_app, reviewed_sha256):
    """Return held records only after a matching explicit review commitment.

    A digest is not authentication, consent or proof that review occurred.
    No input is stored; callers must never provide actual personal metadata.
    """
    state = _canonical(snapshot, expected_app)
    digest = _digest(DOMAIN, state)
    if (not isinstance(reviewed_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", reviewed_sha256)
            or not hmac.compare_digest(digest, reviewed_sha256)):
        raise ValueError("review commitment mismatch")
    candidates = []
    for row in state["rows"]:
        candidates.append({
            "source_identity": {"system": "Memoria", "fixture_id": state["fixture_id"],
                                "row_id": row["id"], "source_revision": SOURCE_REVISION},
            "source_metadata": dict(row),
            "policy": dict.fromkeys(POLICY_FIELDS),
            "status": "HELD",
            "reason": "missing_explicit_genomememory_policy",
            "eligible": False,
        })
    return {"schema": "genomememory-memoria-staging/r0.4",
            "synthetic": True, "authority": "NONE",
            "snapshot_sha256": digest, "candidates": candidates,
            "eligible_count": 0}
