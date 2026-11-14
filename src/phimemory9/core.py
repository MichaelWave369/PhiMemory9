"""A small, local-first prototype of nine-stage nested memory.

No AI model is required or invoked. No external action is authorized.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = (
    "ENTER", "BIRTH", "DEATH", "TRANSFER", "REBIRTH",
    "RESTORE", "RENEW", "LIBERATION", "LOOP",
)
MAX_DEPTH = 6
MAX_BLOBS = 512
MAX_LOOPS_PER_MEMORY = 9
MAX_TEXT_LENGTH = 8192


class MemoryError9(ValueError):
    """Rejected memory operation: invalid state, duplicate, or resource budget."""


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return uuid.uuid4().hex


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class MemoryEngine:
    """SQLite-backed, evidence-preserving, operator-governed memory graph."""

    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS blobs (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                parent_blob_id TEXT REFERENCES blobs(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                blob_id TEXT NOT NULL REFERENCES blobs(id),
                content TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                source_ref TEXT,
                parent_memory_id TEXT REFERENCES memories(id),
                status TEXT NOT NULL CHECK (status IN ('active', 'retired')),
                created_at TEXT NOT NULL,
                UNIQUE (blob_id, fingerprint)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL REFERENCES memories(id),
                stage TEXT NOT NULL,
                detail_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_origin ON memories(parent_memory_id);
            CREATE INDEX IF NOT EXISTS idx_events_memory ON events(memory_id, id);
        """)

    @contextmanager
    def transaction(self):
        """Nested-safe atomic transaction; outer scope owns final commit.

        Required for approved plans: a memory event and its approval receipt
        must commit or roll back together. No existing transaction is silently
        committed by a nested memory operation.
        """
        if self.db.in_transaction:
            marker = "phi_" + uuid.uuid4().hex
            self.db.execute(f"SAVEPOINT {marker}")
            try:
                yield
            except BaseException:
                self.db.execute(f"ROLLBACK TO SAVEPOINT {marker}")
                self.db.execute(f"RELEASE SAVEPOINT {marker}")
                raise
            else:
                self.db.execute(f"RELEASE SAVEPOINT {marker}")
        else:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self.db.rollback()
                raise
            else:
                self.db.commit()

    def __enter__(self) -> "MemoryEngine":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self.db.close()

    def _row(self, table: str, key: str) -> sqlite3.Row:
        if table not in ("blobs", "memories"):
            raise MemoryError9("Unsupported table")
        row = self.db.execute(f"SELECT * FROM {table} WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise MemoryError9(f"Unknown {table[:-1]}: {key}")
        return row

    def _event(self, memory_id: str, stage: str, **detail: Any) -> None:
        if stage not in STAGES:
            raise MemoryError9(f"Unknown stage: {stage}")
        self.db.execute(
            "INSERT INTO events(memory_id,stage,detail_json,recorded_at) VALUES (?,?,?,?)",
            (memory_id, stage, json.dumps(detail, sort_keys=True), _utc()),
        )

    def blob(self, blob_id: str) -> dict[str, Any]:
        return dict(self._row("blobs", blob_id))

    def memory(self, memory_id: str) -> dict[str, Any]:
        return dict(self._row("memories", memory_id))

    def events(self, memory_id: str) -> list[dict[str, Any]]:
        self._row("memories", memory_id)
        return [
            {**dict(row), "detail": json.loads(row["detail_json"])}
            for row in self.db.execute(
                "SELECT * FROM events WHERE memory_id=? ORDER BY id", (memory_id,)
            ).fetchall()
        ]

    def depth(self, blob_id: str) -> int:
        current: str | None = blob_id
        seen: set[str] = set()
        depth = 0
        while current is not None:
            if current in seen:
                raise MemoryError9("Cycle in blob ancestry")
            seen.add(current)
            row = self._row("blobs", current)
            current = row["parent_blob_id"]
            if current is not None:
                depth += 1
        return depth

    def create_blob(self, label: str, parent_blob_id: str | None = None) -> str:
        if not label.strip() or len(label) > 128:
            raise MemoryError9("Blob label must be 1..128 characters")
        if parent_blob_id is not None and self.depth(parent_blob_id) >= MAX_DEPTH:
            raise MemoryError9("Nested blob depth limit reached")
        count = self.db.execute("SELECT COUNT(*) FROM blobs").fetchone()[0]
        if count >= MAX_BLOBS:
            raise MemoryError9("Blob budget exhausted")
        blob_id = _id()
        with self.transaction():
            self.db.execute(
                "INSERT INTO blobs VALUES(?,?,?,?)",
                (blob_id, label.strip(), parent_blob_id, _utc()),
            )
        return blob_id

    def _enter(
        self, blob_id: str, content: str, source_ref: str | None = None,
        parent_memory_id: str | None = None,
    ) -> str:
        self._row("blobs", blob_id)
        if parent_memory_id is not None:
            self._row("memories", parent_memory_id)
        if not content.strip() or len(content) > MAX_TEXT_LENGTH:
            raise MemoryError9("Memory content must be 1..8192 characters")
        if source_ref is not None and len(source_ref) > 1024:
            raise MemoryError9("Source reference exceeds 1024 characters")
        fingerprint = _digest(content)
        if self.db.execute(
            "SELECT 1 FROM memories WHERE blob_id=? AND fingerprint=?",
            (blob_id, fingerprint),
        ).fetchone():
            raise MemoryError9("Duplicate content in target blob")
        memory_id = _id()
        self.db.execute(
            """INSERT INTO memories
            (id,blob_id,content,fingerprint,source_ref,parent_memory_id,status,created_at)
            VALUES (?,?,?,?,?,?,'active',?)""",
            (memory_id, blob_id, content, fingerprint, source_ref, parent_memory_id, _utc()),
        )
        self._event(memory_id, "ENTER", source_ref=source_ref)
        self._event(memory_id, "BIRTH", parent_memory_id=parent_memory_id)
        return memory_id

    def enter(self, blob_id: str, content: str, source_ref: str | None = None) -> str:
        with self.transaction():
            return self._enter(blob_id, content, source_ref)

    def death(self, memory_id: str, reason: str) -> None:
        memory = self._row("memories", memory_id)
        if memory["status"] != "active" or not reason.strip():
            raise MemoryError9("DEATH requires an active memory and an explicit reason")
        with self.transaction():
            self.db.execute(
                "UPDATE memories SET status='retired' WHERE id=?", (memory_id,)
            )
            self._event(memory_id, "DEATH", reason=reason)

    def restore(self, memory_id: str, reason: str) -> None:
        memory = self._row("memories", memory_id)
        if memory["status"] != "retired" or not reason.strip():
            raise MemoryError9("RESTORE requires retired memory and explicit evidence/reason")
        with self.transaction():
            self.db.execute(
                "UPDATE memories SET status='active' WHERE id=?", (memory_id,)
            )
            self._event(memory_id, "RESTORE", reason=reason)

    def transfer(self, memory_id: str, target_blob_id: str) -> str:
        source = self._row("memories", memory_id)
        if source["blob_id"] == target_blob_id:
            raise MemoryError9("TRANSFER must change blob context")
        with self.transaction():
            child = self._enter(
                target_blob_id, source["content"], source["source_ref"], memory_id
            )
            self._event(memory_id, "TRANSFER", target_blob_id=target_blob_id,
                        child_memory_id=child)
        return child

    def rebirth(self, memory_id: str, content: str, target_blob_id: str) -> str:
        source = self._row("memories", memory_id)
        with self.transaction():
            child = self._enter(target_blob_id, content, source["source_ref"], memory_id)
            self._event(memory_id, "REBIRTH", child_memory_id=child,
                        target_blob_id=target_blob_id)
        return child

    def renew(self, memory_id: str, revised_content: str, reason: str) -> str:
        source = self._row("memories", memory_id)
        if source["status"] != "active" or not reason.strip():
            raise MemoryError9("RENEW requires active memory and stated reason")
        with self.transaction():
            child = self._enter(
                source["blob_id"], revised_content, source["source_ref"], memory_id
            )
            self.db.execute(
                "UPDATE memories SET status='retired' WHERE id=?", (memory_id,)
            )
            self._event(memory_id, "RENEW", reason=reason, child_memory_id=child)
            self._event(memory_id, "DEATH", reason="Superseded by " + child)
        return child

    def lineage(self, memory_id: str) -> list[str]:
        ancestry: list[str] = []
        cursor: str | None = memory_id
        while cursor is not None:
            if cursor in ancestry:
                raise MemoryError9("Cycle in memory ancestry")
            ancestry.append(cursor)
            cursor = self._row("memories", cursor)["parent_memory_id"]
        return list(reversed(ancestry))

    def liberation(self, memory_id: str) -> dict[str, Any]:
        """Explicit portable export; does not send any data over the network."""
        with self.transaction():
            source = self.memory(memory_id)
            ancestors = [self.memory(mid) for mid in self.lineage(memory_id)]
            self._event(memory_id, "LIBERATION", format="phi-memory9/v0.1")
            events = self.events(memory_id)
        return {
            "schema": "phi-memory9/v0.1",
            "memory": source,
            "lineage": ancestors,
            "events": events,
            "notice": "Provenance pointers are not source verification. Review before sharing.",
        }

    def loop(
        self, memory_id: str, route: str = "hold",
        target_blob_id: str | None = None,
    ) -> dict[str, Any]:
        """The ninth gear. Always an explicit route; 'hold' is safe default."""
        source = self._row("memories", memory_id)
        allowed = {"hold", "inward", "outward", "lateral", "seed"}
        if route not in allowed:
            raise MemoryError9(f"Unknown LOOP route: {route}")
        loops = self.db.execute(
            "SELECT COUNT(*) FROM events WHERE memory_id=? AND stage='LOOP'",
            (memory_id,),
        ).fetchone()[0]
        if loops >= MAX_LOOPS_PER_MEMORY:
            raise MemoryError9("LOOP budget exhausted for memory")
        current_blob = self._row("blobs", source["blob_id"])
        with self.transaction():
            next_blob_id: str | None = None
            next_memory_id: str | None = None
            if route == "inward":
                next_blob_id = self.create_blob(
                    f"Nested from {source['id'][:8]}", current_blob["id"]
                )
            elif route == "outward":
                next_blob_id = current_blob["parent_blob_id"]
                if next_blob_id is None:
                    raise MemoryError9("Root blob cannot route outward")
            elif route == "lateral":
                if target_blob_id is None:
                    raise MemoryError9("Lateral LOOP needs explicit target_blob_id")
                next_blob_id = target_blob_id
            elif route == "seed":
                next_blob_id = self.create_blob(f"Seed from {source['id'][:8]}")
            if next_blob_id is not None:
                next_memory_id = self.transfer(memory_id, next_blob_id)
            self._event(memory_id, "LOOP", route=route,
                        target_blob_id=next_blob_id, child_memory_id=next_memory_id)
        return {
            "route": route, "source_memory_id": memory_id,
            "target_blob_id": next_blob_id, "child_memory_id": next_memory_id,
        }

    def verify(self) -> dict[str, Any]:
        integrity = self.db.execute("PRAGMA integrity_check").fetchone()[0]
        bad_refs = self.db.execute("PRAGMA foreign_key_check").fetchall()
        rows = self.db.execute("SELECT id,content,fingerprint FROM memories").fetchall()
        mismatch = [
            row["id"] for row in rows if _digest(row["content"]) != row["fingerprint"]
        ]
        for row in rows:
            self.lineage(row["id"])
        blobs = self.db.execute("SELECT id FROM blobs").fetchall()
        for row in blobs:
            if self.depth(row["id"]) > MAX_DEPTH:
                raise MemoryError9("Blob exceeds depth budget")
        stages = [
            row["stage"] for row in self.db.execute("SELECT stage FROM events")
        ]
        unknown = [stage for stage in stages if stage not in STAGES]
        valid = integrity == "ok" and not bad_refs and not mismatch and not unknown
        return {
            "ok": valid, "integrity": integrity,
            "blobs": len(blobs), "memories": len(rows), "events": len(stages),
            "fingerprint_mismatches": mismatch, "unknown_stages": unknown,
            "foreign_key_errors": len(bad_refs),
        }
