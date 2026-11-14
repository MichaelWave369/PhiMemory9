"""R0.2 source/claim ledger: operator-declared evidence, never truth promotion.

Runs against a MemoryEngine's local SQLite database; no network, models, or
automatic adjudication. Its hashes detect accidental mutation, not malicious
database rewrites. Source independence is a DECLARATION, not independently proven.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .core import MemoryEngine, MemoryError9

STANCES = ("support", "challenge", "context")
KINDS = ("document", "observation", "dataset", "synthetic")
MAX_STATEMENT = 8192
MAX_EXCERPT = 2048


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(_json(data).encode("utf-8")).hexdigest()


def _uid() -> str:
    return uuid.uuid4().hex


def _text(value: str, limit: int, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise MemoryError9(f"{name} must contain 1..{limit} characters")
    return value.strip()


class EvidenceLedger:
    """Optional claim and contradiction tables attached to a MemoryEngine.

    Does not modify R0.1 memories, their lifecycle, or the nine stage names.
    """

    def __init__(self, memory: MemoryEngine):
        self.memory = memory
        self.db = memory.db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS e_sources (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                locator TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                independence_group TEXT NOT NULL,
                declared_sha256 TEXT,
                row_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS e_claims (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL REFERENCES memories(id),
                statement TEXT NOT NULL,
                row_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS e_links (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES e_claims(id),
                source_id TEXT NOT NULL REFERENCES e_sources(id),
                stance TEXT NOT NULL CHECK(stance IN ('support','challenge','context')),
                excerpt TEXT NOT NULL,
                row_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(claim_id,source_id,stance)
            );
            CREATE TABLE IF NOT EXISTS e_conflicts (
                id TEXT PRIMARY KEY,
                left_claim TEXT NOT NULL REFERENCES e_claims(id),
                right_claim TEXT NOT NULL REFERENCES e_claims(id),
                reason TEXT NOT NULL,
                row_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                CHECK(left_claim < right_claim),
                UNIQUE(left_claim,right_claim)
            );
            CREATE TABLE IF NOT EXISTS e_log (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_e_claims_memory ON e_claims(memory_id);
            CREATE INDEX IF NOT EXISTS idx_e_links_claim ON e_links(claim_id);
        """)

    def _get(self, table: str, identity: str) -> dict[str, Any]:
        if table not in ("e_sources", "e_claims", "e_links", "e_conflicts"):
            raise MemoryError9("Unknown evidence table")
        row = self.db.execute(
            f"SELECT * FROM {table} WHERE id=?", (identity,)
        ).fetchone()
        if row is None:
            raise MemoryError9(f"Unknown {table} identifier")
        return dict(row)

    def _log(self, action: str, payload: dict[str, Any]) -> None:
        previous = self.db.execute(
            "SELECT event_hash FROM e_log ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = previous["event_hash"] if previous else "0" * 64
        encoded = _json(payload)
        created = _now()
        event_hash = _hash({
            "action": action, "payload": encoded,
            "prev_hash": prev_hash, "created_at": created,
        })
        self.db.execute(
            "INSERT INTO e_log(action,payload,prev_hash,event_hash,created_at) "
            "VALUES(?,?,?,?,?)",
            (action, encoded, prev_hash, event_hash, created),
        )

    def source(
        self, label: str, locator: str, *,
        kind: str = "document",
        independence_group: str = "unverified",
        declared_sha256: str | None = None,
    ) -> str:
        label = _text(label, 160, "Source label")
        locator = _text(locator, 1024, "Source locator")
        independence_group = _text(independence_group, 160, "Independence group")
        if kind not in KINDS:
            raise MemoryError9(f"Source kind must be one of {KINDS}")
        if declared_sha256 is not None:
            if not re.fullmatch(r"[0-9a-f]{64}", declared_sha256):
                raise MemoryError9("Declared digest must be lowercase hex SHA-256")
        data = {
            "label": label, "locator": locator, "kind": kind,
            "independence_group": independence_group,
            "declared_sha256": declared_sha256,
        }
        identity = _uid()
        with self.db:
            try:
                self.db.execute(
                    "INSERT INTO e_sources VALUES(?,?,?,?,?,?,?,?)",
                    (identity, label, locator, kind, independence_group,
                     declared_sha256, _hash(data), _now()),
                )
            except sqlite3.IntegrityError as err:
                raise MemoryError9("Source locator already registered") from err
            self._log("SOURCE", {"source_id": identity, "row_hash": _hash(data)})
        return identity

    def claim(self, memory_id: str, statement: str) -> str:
        self.memory.memory(memory_id)
        statement = _text(statement, MAX_STATEMENT, "Claim statement")
        data = {"memory_id": memory_id, "statement": statement}
        identity = _uid()
        with self.db:
            self.db.execute(
                "INSERT INTO e_claims VALUES(?,?,?,?,?)",
                (identity, memory_id, statement, _hash(data), _now()),
            )
            self._log("CLAIM", {"claim_id": identity, "row_hash": _hash(data)})
        return identity

    def attach(
        self, claim_id: str, source_id: str, stance: str, *,
        excerpt: str = "",
    ) -> str:
        self._get("e_claims", claim_id)
        self._get("e_sources", source_id)
        if stance not in STANCES:
            raise MemoryError9(f"Stance must be one of {STANCES}")
        if not isinstance(excerpt, str) or len(excerpt) > MAX_EXCERPT:
            raise MemoryError9("Excerpt exceeds the 2048 character limit")
        data = {
            "claim_id": claim_id, "source_id": source_id,
            "stance": stance, "excerpt": excerpt,
        }
        identity = _uid()
        with self.db:
            try:
                self.db.execute(
                    "INSERT INTO e_links VALUES(?,?,?,?,?,?,?)",
                    (identity, claim_id, source_id, stance, excerpt,
                     _hash(data), _now()),
                )
            except sqlite3.IntegrityError as err:
                raise MemoryError9("Duplicate claim/source/stance attachment") from err
            self._log("ATTACH", {"link_id": identity, "row_hash": _hash(data)})
        return identity

    def contradiction(self, claim_a: str, claim_b: str, reason: str) -> str:
        if claim_a == claim_b:
            raise MemoryError9("Claim cannot contradict itself")
        self._get("e_claims", claim_a)
        self._get("e_claims", claim_b)
        reason = _text(reason, 2048, "Contradiction reason")
        left, right = sorted((claim_a, claim_b))
        data = {"left_claim": left, "right_claim": right, "reason": reason}
        identity = _uid()
        with self.db:
            try:
                self.db.execute(
                    "INSERT INTO e_conflicts VALUES(?,?,?,?,?,?)",
                    (identity, left, right, reason, _hash(data), _now()),
                )
            except sqlite3.IntegrityError as err:
                raise MemoryError9("Contradiction pair already declared") from err
            self._log("CONTRADICTION", {"conflict_id": identity,
                                         "row_hash": _hash(data)})
        return identity

    def report(self, claim_id: str) -> dict[str, Any]:
        claim = self._get("e_claims", claim_id)
        links = [
            dict(r) for r in self.db.execute(
                """SELECT e_links.*, e_sources.label AS source_label,
                e_sources.locator AS locator,
                e_sources.kind AS source_kind,
                e_sources.independence_group AS independence_group
                FROM e_links JOIN e_sources ON e_links.source_id=e_sources.id
                WHERE e_links.claim_id=? ORDER BY e_links.created_at,e_links.id""",
                (claim_id,),
            )
        ]
        conflicts = [
            dict(r) for r in self.db.execute(
                "SELECT * FROM e_conflicts WHERE left_claim=? OR right_claim=? "
                "ORDER BY id", (claim_id, claim_id)
            )
        ]
        groups = {
            stance: sorted(set(l["independence_group"] for l in links
                               if l["stance"] == stance))
            for stance in STANCES
        }
        return {
            "claim": claim, "memory": self.memory.memory(claim["memory_id"]),
            "evidence_links": links, "contradictions": conflicts,
            "declared_groups_by_stance": groups,
            "classification": (
                "explicitly_contested" if groups["challenge"] or conflicts
                else "source_pointers_attached" if links else "unreviewed"
            ),
            "caution": "Source independence is declared, not verified. "
                       "No recorded stance establishes truth.",
        }

    def export(self, claim_id: str) -> dict[str, Any]:
        """Explicit local export, no write or external transmission."""
        report = self.report(claim_id)
        sources = [
            self._get("e_sources", sid)
            for sid in sorted({link["source_id"]
                               for link in report["evidence_links"]})
        ]
        return {
            "schema": "phi-memory9/evidence-r0.2",
            **report,
            "sources": sources,
            "lineage": [
                self.memory.memory(mid) for mid in
                self.memory.lineage(report["claim"]["memory_id"])
            ],
        }

    def audit(self) -> dict[str, Any]:
        problems: list[str] = []
        specs = {
            "e_sources": ("label", "locator", "kind",
                          "independence_group", "declared_sha256"),
            "e_claims": ("memory_id", "statement"),
            "e_links": ("claim_id", "source_id", "stance", "excerpt"),
            "e_conflicts": ("left_claim", "right_claim", "reason"),
        }
        for table, columns in specs.items():
            for row in self.db.execute(f"SELECT * FROM {table}"):
                data = {column: row[column] for column in columns}
                if _hash(data) != row["row_hash"]:
                    problems.append(f"{table} fingerprint mismatch: {row['id']}")
        prev_hash = "0" * 64
        count = 0
        for row in self.db.execute("SELECT * FROM e_log ORDER BY seq"):
            count += 1
            expected_hash = _hash({
                "action": row["action"], "payload": row["payload"],
                "prev_hash": row["prev_hash"], "created_at": row["created_at"],
            })
            if row["prev_hash"] != prev_hash or row["event_hash"] != expected_hash:
                problems.append(f"Event hash-chain mismatch: seq {row['seq']}")
            prev_hash = row["event_hash"]
        bad_refs = self.db.execute("PRAGMA foreign_key_check").fetchall()
        if bad_refs:
            problems.append(f"Foreign key violations: {len(bad_refs)}")
        base = self.memory.verify()
        if not base["ok"]:
            problems.append("Base memory integrity check failed")
        return {
            "ok": not problems,
            "problems": problems,
            "events": count,
            "sources": self.db.execute("SELECT COUNT(*) FROM e_sources").fetchone()[0],
            "claims": self.db.execute("SELECT COUNT(*) FROM e_claims").fetchone()[0],
            "links": self.db.execute("SELECT COUNT(*) FROM e_links").fetchone()[0],
            "contradictions": self.db.execute(
                "SELECT COUNT(*) FROM e_conflicts"
            ).fetchone()[0],
            "base_verified": base["ok"],
        }
