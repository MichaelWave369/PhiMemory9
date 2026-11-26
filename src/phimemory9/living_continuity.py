"""Bounded, keyed logical fixture snapshot for a separately held witness.

No network, automatic promotion, runtime gate, or external action authority.
Only the digest leaves the trusted local fixture process.
"""
import hashlib
import hmac
import json

from .living_contract import fixture_id

SCHEMA = "living-memory-continuity/v1"
DOMAIN = b"living-memory-continuity/v1\0"
MAX_TABLES = 64
MAX_ROWS = 4096
MAX_BYTES = 16 * 1024 * 1024


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _identifier(name):
    return '"' + name.replace('"', '""') + '"'


def snapshot(store):
    """Commit both attached databases in one locked fixture transaction.

    Row order is normalized; SQLite page layout and filesystem metadata
    are excluded. The operator key is not given to the witness.
    """
    with store.engine.transaction():
        store.authenticate(store.operator)
        sid = fixture_id(store._meta("store_id"))
        mac = hmac.new(store.operator.key, DOMAIN + sid.encode("ascii") + b"\0",
                       hashlib.sha256)
        size = 0

        def emit(value):
            nonlocal size
            raw = _wire(value)
            size += len(raw) + 8
            if size > MAX_BYTES:
                raise ValueError("continuity snapshot byte budget")
            mac.update(len(raw).to_bytes(8, "big"))
            mac.update(raw)

        for db in ("main", "lm_guard"):
            # Include the logical schema and SQLite's event sequence, not
            # file pages, journal bytes, or external copies.
            schema = store.db.execute(
                f"SELECT type,name,tbl_name,sql FROM {db}.sqlite_master "
                "ORDER BY type,name LIMIT ?", (MAX_TABLES+1,)).fetchall()
            if len(schema) > MAX_TABLES:
                raise ValueError("continuity schema budget")
            emit([db, [list(row) for row in schema]])
            for entry in schema:
                if entry["type"] != "table":
                    continue
                name = entry["name"]
                rows = store.db.execute(
                    f"SELECT * FROM {db}.{_identifier(name)} LIMIT ?", (MAX_ROWS+1,)).fetchall()
                if len(rows) > MAX_ROWS:
                    raise ValueError("continuity row budget")
                # Fixture schema stores text, integers and null. No blob or
                # floating-point interpretation is defined in this contract.
                for row in rows:
                    if any(type(v) not in (str, int, type(None)) for v in row):
                        raise ValueError("unsupported continuity row type")
                encoded = sorted(_wire(list(row)) for row in rows)
                emit([name, len(encoded)])
                for raw in encoded:
                    # Length framing and byte order are explicit. Decode to
                    # keep the same framing path and enforce the total budget.
                    emit(json.loads(raw))
        return {"schema": SCHEMA, "synthetic": True, "authority": "NONE",
                "witness_sha256": mac.hexdigest()}


def compare(snapshot_record, pinned_digest):
    """Advisory equality only; pin freshness and custody are external."""
    if (type(snapshot_record) is not dict or set(snapshot_record) !=
            {"schema", "synthetic", "authority", "witness_sha256"}
            or snapshot_record["schema"] != SCHEMA
            or snapshot_record["synthetic"] is not True
            or snapshot_record["authority"] != "NONE"):
        raise ValueError("invalid continuity snapshot")
    for value in (snapshot_record["witness_sha256"], pinned_digest):
        if (type(value) is not str or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value)):
            raise ValueError("invalid continuity digest")
    return {"matches": hmac.compare_digest(snapshot_record["witness_sha256"], pinned_digest),
            "authority": "NONE", "status": "HELD"}
