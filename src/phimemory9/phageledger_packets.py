"""PhageLedger-inspired synthetic software envelope, not transport or authorization."""

from collections.abc import Mapping
import hmac
import re

from .genomememory_preview import _label
from .genomememory_integrity import _digest

SCHEMA = "phageledger-software-envelope/r0.6"
DOMAIN = "phageledger/software-envelope/r0.6"
REPORT_DOMAIN = "phageledger/software-check/r0.6"
FIELDS = {"schema", "synthetic", "packet_id", "source", "destination",
          "purpose", "not_before", "expires_at", "payload_kind",
          "payload_sha256", "policy_sha256", "authority"}
PURPOSES = {"metadata_review", "integrity_review"}
MAX_TTL = 3600
MAX_TIME = 2**53 - 1


def _hex(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid digest")
    return value


def _time(value):
    if type(value) is not int or not 0 <= value <= MAX_TIME:
        raise ValueError("invalid integer epoch seconds")
    return value


def _fixture_label(value):
    value = _label(value)
    if not value.startswith("fixture:") or len(value) == len("fixture:"):
        raise ValueError("expected fixture namespace")
    return value


def _canonical(envelope):
    if not isinstance(envelope, Mapping) or set(envelope) != FIELDS:
        raise ValueError("invalid envelope fields")
    if (envelope["schema"] != SCHEMA or envelope["synthetic"] is not True
            or envelope["authority"] != "NONE"
            or envelope["payload_kind"] != "synthetic_metadata_digest"):
        raise ValueError("unsupported envelope contract")
    for key in ("packet_id", "source", "destination"):
        _fixture_label(envelope[key])
    if envelope["source"] == envelope["destination"]:
        raise ValueError("source and destination must differ")
    purpose = envelope["purpose"]
    if not isinstance(purpose, str) or purpose not in PURPOSES:
        raise ValueError("unsupported purpose")
    start, end = _time(envelope["not_before"]), _time(envelope["expires_at"])
    if not 0 < end - start <= MAX_TTL:
        raise ValueError("invalid lifetime")
    _hex(envelope["payload_sha256"])
    _hex(envelope["policy_sha256"])
    return dict(envelope)


def seal(envelope):
    """Commit to declared metadata. No signing key or actual payload is used."""
    state = _canonical(envelope)
    return {"schema": "phageledger-software-seal/r0.6", "synthetic": True,
            "authority": "NONE", "envelope_sha256": _digest(DOMAIN, state)}


def inspect(envelope, expected_sha256, *, expected_source, expected_destination,
            expected_purpose, expected_payload_sha256, expected_policy_sha256, now):
    """Check against caller-supplied expectations and an explicit fixture clock.

    Even a matching packet is HELD; this function never releases or executes it.
    """
    state = _canonical(envelope)
    digest = _digest(DOMAIN, state)
    expected_sha256 = _hex(expected_sha256)
    expected_source = _fixture_label(expected_source)
    expected_destination = _fixture_label(expected_destination)
    if not isinstance(expected_purpose, str) or expected_purpose not in PURPOSES:
        raise ValueError("unsupported expected purpose")
    expected_payload_sha256 = _hex(expected_payload_sha256)
    expected_policy_sha256 = _hex(expected_policy_sha256)
    now = _time(now)
    checks = {
        "integrity": hmac.compare_digest(digest, expected_sha256),
        "source": state["source"] == expected_source,
        "destination": state["destination"] == expected_destination,
        "purpose": state["purpose"] == expected_purpose,
        "payload_reference": hmac.compare_digest(state["payload_sha256"], expected_payload_sha256),
        "policy_reference": hmac.compare_digest(state["policy_sha256"], expected_policy_sha256),
        "time_window": state["not_before"] <= now < state["expires_at"],
    }
    reason = "compatible_but_held" if all(checks.values()) else "compatibility_failed"
    body = {
        "schema": "phageledger-software-check/r0.6", "synthetic": True,
        "authority": "NONE", "status": "HELD", "eligible": False,
        "compatible": all(checks.values()), "reason": reason, "checks": checks,
        "envelope_sha256": digest, "expected_sha256": expected_sha256,
        "expectations_sha256": _digest("phageledger/expectations/r0.6", {
            "source": expected_source, "destination": expected_destination,
            "purpose": expected_purpose, "payload_sha256": expected_payload_sha256,
            "policy_sha256": expected_policy_sha256, "now": now,
        }),
    }
    return {**body, "receipt_sha256": _digest(REPORT_DOMAIN, body)}
