"""R0.4 explicit operator-plan approval, replay prevention and safe exports.

Local CLI only; no browser write endpoint or automatic routing. A plan must be
reviewed and approved by exact canonical SHA-256 before any mutation. This is
NOT cryptographic user authentication or a substitute for OS file permissions.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from .core import MemoryEngine, MemoryError9, _utc

SCHEMA = "phi-memory9/operator-plan-r0.4"
MAX_PLAN_BYTES = 16384
HEX256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = {"schema", "action", "reason"}
FIELDS = {
    "enter": {"blob_id", "content", "source_ref"},
    "death": {"memory_id"},
    "restore": {"memory_id"},
    "renew": {"memory_id", "content"},
    "rebirth": {"memory_id", "content", "target_blob_id"},
    "transfer": {"memory_id", "target_blob_id"},
    "loop": {"memory_id", "route", "target_blob_id"},
}
MANDATORY = {
    "enter": {"blob_id", "content"},
    "death": {"memory_id"},
    "restore": {"memory_id"},
    "renew": {"memory_id", "content"},
    "rebirth": {"memory_id", "content", "target_blob_id"},
    "transfer": {"memory_id", "target_blob_id"},
    "loop": {"memory_id", "route"},
}


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MemoryError9(f"Duplicate plan field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise MemoryError9(f"Non-JSON constant rejected: {value}")


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def validate_plan(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise MemoryError9("Plan must be a JSON object")
    if data.get("schema") != SCHEMA:
        raise MemoryError9("Unknown plan schema")
    action = data.get("action")
    if action not in FIELDS:
        raise MemoryError9("Unsupported plan action")
    valid_keys = REQUIRED | FIELDS[action]
    if set(data) - valid_keys:
        raise MemoryError9("Unknown plan fields: " + ", ".join(sorted(set(data) - valid_keys)))
    if (REQUIRED | MANDATORY[action]) - set(data):
        raise MemoryError9("Missing required plan fields")
    for key in data:
        if not isinstance(data[key], str) or (not data[key].strip() and key != "source_ref"):
            raise MemoryError9(f"Plan field {key} must be a nonempty string")
        if len(data[key]) > (8192 if key == "content" else 1024):
            raise MemoryError9(f"Plan field {key} exceeds length limit")
    if len(data["reason"].strip()) > 512:
        raise MemoryError9("Operator reason must be at most 512 characters")
    if action == "loop":
        if data["route"] not in ("hold", "inward", "outward", "lateral", "seed"):
            raise MemoryError9("Invalid gear route")
        if data["route"] == "lateral" and not data.get("target_blob_id"):
            raise MemoryError9("Lateral route requires a target blob")
        if data["route"] != "lateral" and "target_blob_id" in data:
            raise MemoryError9("Target blob is only valid for lateral routing")
    return data


def load_plan(file: str | Path) -> dict[str, Any]:
    path = Path(file)
    if not path.is_file() or path.stat().st_size > MAX_PLAN_BYTES:
        raise MemoryError9("Plan file missing or exceeds 16 KiB")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw, object_pairs_hook=_pairs_unique, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MemoryError9("Plan file is not valid UTF-8 JSON") from exc
    return validate_plan(data)


def _init(engine: MemoryEngine) -> None:
    engine.db.execute("""
        CREATE TABLE IF NOT EXISTS g_approvals (
            fingerprint TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            reason TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            result_json TEXT NOT NULL
        )
    """)
    engine.db.commit()


def review(engine: MemoryEngine, plan: dict[str, Any]) -> dict[str, Any]:
    data = validate_plan(plan)
    _init(engine)
    identity = data.get("memory_id")
    ref = engine.memory(identity) if identity else None
    blob = engine.blob(data["blob_id"]) if data["action"] == "enter" else None
    if "target_blob_id" in data:
        engine.blob(data["target_blob_id"])
    consumed = engine.db.execute(
        "SELECT 1 FROM g_approvals WHERE fingerprint=?", (fingerprint(data),)
    ).fetchone() is not None
    return {
        "schema": SCHEMA,
        "sha256": fingerprint(data),
        "action": data["action"],
        "reason": data["reason"],
        "previously_applied": consumed,
        "target_memory_id": identity,
        "target_status": ref["status"] if ref else None,
        "target_preview": ref["content"][:160] if ref else None,
        "blob_label": blob["label"] if blob else None,
        "route": data.get("route"),
        "new_content_preview": data.get("content", "")[:160] if data.get("content") else None,
        "warning": "Review this plan and the selected database before explicitly applying its SHA-256.",
    }


def apply(engine: MemoryEngine, plan: dict[str, Any], approved_sha256: str) -> dict[str, Any]:
    data = validate_plan(plan)
    if not isinstance(approved_sha256, str) or not HEX256.fullmatch(approved_sha256):
        raise MemoryError9("Must supply lowercase full SHA-256 approval")
    key = fingerprint(data)
    if key != approved_sha256:
        raise MemoryError9("Approval fingerprint does not match current plan")
    _init(engine)
    if not engine.verify()["ok"]:
        raise MemoryError9("Memory storage integrity check failed")
    action = data["action"]
    with engine.transaction():
        if engine.db.execute(
            "SELECT 1 FROM g_approvals WHERE fingerprint=?", (key,)
        ).fetchone():
            raise MemoryError9("Plan already applied; replay refused")
        # Reserve the fingerprint before any operation. Both reservation and
        # all core mutations participate in the SAME outer transaction.
        engine.db.execute(
            "INSERT INTO g_approvals VALUES(?,?,?,?,?)",
            (key, action, data["reason"], _utc(), "{}"),
        )
        result: dict[str, Any]
        if action == "enter":
            result = {"memory_id": engine.enter(
                data["blob_id"], data["content"], data.get("source_ref")
            )}
        elif action == "death":
            engine.death(data["memory_id"], data["reason"])
            result = {"memory_id": data["memory_id"], "status": "retired"}
        elif action == "restore":
            engine.restore(data["memory_id"], data["reason"])
            result = {"memory_id": data["memory_id"], "status": "active"}
        elif action == "renew":
            result = {"memory_id": engine.renew(
                data["memory_id"], data["content"], data["reason"]
            )}
        elif action == "rebirth":
            result = {"memory_id": engine.rebirth(
                data["memory_id"], data["content"], data["target_blob_id"]
            )}
        elif action == "transfer":
            result = {"memory_id": engine.transfer(
                data["memory_id"], data["target_blob_id"]
            )}
        elif action == "loop":
            result = engine.loop(
                data["memory_id"], data["route"], data.get("target_blob_id")
            )
        else:
            raise MemoryError9("Unsupported action")
        engine.db.execute(
            "UPDATE g_approvals SET result_json=? WHERE fingerprint=?",
            (canonical_json(result), key),
        )
    return {"schema": SCHEMA, "sha256": key, "action": action, "result": result,
            "applied": True, "approval_kind": "explicit_local_cli"}


def approval_history(engine: MemoryEngine, limit: int = 100) -> list[dict[str, Any]]:
    if limit < 1 or limit > 200:
        raise ValueError("limit must be 1..200")
    _init(engine)
    return [
        {**dict(row), "result": json.loads(row["result_json"])}
        for row in engine.db.execute(
            "SELECT * FROM g_approvals ORDER BY applied_at DESC,fingerprint DESC LIMIT ?",
            (limit,),
        )
    ]


def redact_export(engine: MemoryEngine, memory_id: str,
                  include_content: bool = False) -> dict[str, Any]:
    """A metadata-only preview by default. Explicit full export is local only."""
    ancestry = [engine.memory(i) for i in engine.lineage(memory_id)]
    event_count = sum(len(engine.events(i["id"])) for i in ancestry)
    packet = {
        "schema": "phi-memory9/privacy-export-r0.4",
        "memory_id": memory_id,
        "mode": "full_operator_approved" if include_content else "metadata_only",
        "lineage": [
            {
                "id": item["id"], "parent_memory_id": item["parent_memory_id"],
                "blob_id": item["blob_id"], "status": item["status"],
                "content_sha256": item["fingerprint"],
                **({
                    "content": item["content"],
                    "source_ref": item["source_ref"],
                } if include_content else {}),
            }
            for item in ancestry
        ],
        "event_count": event_count,
        "warning": "No data has been sent externally. Inspect before sharing.",
    }
    return packet


def export_digest(engine: MemoryEngine, memory_id: str) -> str:
    packet = redact_export(engine, memory_id, include_content=True)
    return fingerprint(packet)


def save_export(
    engine: MemoryEngine, memory_id: str, destination: str | Path, *,
    include_content: bool = False, approved_sha256: str | None = None,
) -> dict[str, Any]:
    if include_content and export_digest(engine, memory_id) != approved_sha256:
        raise MemoryError9("Full export needs an exact approved SHA-256 from export-review")
    packet = redact_export(engine, memory_id, include_content)
    data = (json.dumps(packet, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    dest = Path(destination)
    # No overwrites, no implicit directory creation, owner-only file mode on POSIX.
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return {
        "schema": packet["schema"], "memory_id": memory_id,
        "mode": packet["mode"], "saved": True,
        "bytes": len(data), "no_network": True,
    }
