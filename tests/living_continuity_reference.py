"""Separate, offline read-only continuity reference for closed synthetic stores.

No producer helpers, no runtime admission, no external authority claim.
"""
import hashlib
import hmac
import json
import sqlite3
import struct
from pathlib import Path


def reference_digest(main, guard, key):
    """Reference framing from the v1 contract; both files must be quiescent.

    Not a concurrent snapshot facility. Never run on personal databases.
    """
    if type(key) is not bytes or len(key) != 32:
        raise ValueError("fixture key required")
    frames = []
    total = 0

    def encode(value):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"),
                          sort_keys=True, allow_nan=False).encode("ascii")

    def frame(raw):
        nonlocal total
        total += 8 + len(raw)
        if total > 16 * 1024 * 1024:
            raise ValueError("reference byte budget")
        frames.append(struct.pack(">Q", len(raw)) + raw)

    store_id = None
    for label, path in (("main", main), ("lm_guard", guard)):
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        try:
            metadata_table = "lm_meta" if label == "main" else "meta"
            identity = db.execute("SELECT value FROM "+metadata_table+
                                  " WHERE key='store_id'").fetchone()[0]
            if label == "main":
                store_id = identity
            elif identity != store_id:
                raise ValueError("reference store mismatch")
            catalog = sorted(db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master").fetchall(),
                key=lambda row: (row[0], row[1]))
            if len(catalog) > 64:
                raise ValueError("reference schema budget")
            frame(encode([label, catalog]))
            for kind, name, _, _ in catalog:
                if kind != "table":
                    continue
                quoted = '"' + name.replace('"', '""') + '"'
                records = []
                for row in db.execute("SELECT * FROM "+quoted):
                    if len(records) >= 4096:
                        raise ValueError("reference row budget")
                    if any(type(value) not in (str, int, type(None)) for value in row):
                        raise ValueError("reference row type")
                    records.append(encode(row))
                frame(encode([name, len(records)]))
                for raw in sorted(records):
                    frame(raw)
        finally:
            db.close()
    prefix = b"living-memory-continuity/v1\0" + store_id.encode("ascii") + b"\0"
    return hmac.digest(key, prefix+b"".join(frames), "sha256").hex()
