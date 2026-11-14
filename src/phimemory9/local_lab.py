"""R0.3 local, read-only HTTP window onto the real ΦMemory9 SQLite memory.

No remote binding, writes, CORS, filesystem browsing, or agent execution.
The browser reads a bounded snapshot from the same loopback origin as the
compiled React lab. Do not open databases containing secrets in R0.3.
"""
from __future__ import annotations

import json
import mimetypes
import re
import sqlite3
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

MAX_ROWS = 200
MAX_DETAIL_EVENTS = 100
MAX_STATIC_BYTES = 8_000_000
REPO_WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
MEMORY_ID = re.compile(r"^[0-9a-f]{32}$")


def _rows(db: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
    return [dict(item) for item in db.execute(query, params).fetchall()]


def _exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _count(db: sqlite3.Connection, table: str) -> int:
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] if _exists(db, table) else 0


def _events(db: sqlite3.Connection, where: str = "", args: tuple = (),
            limit: int = MAX_ROWS) -> list[dict]:
    result = _rows(
        db, "SELECT id,memory_id,stage,detail_json,recorded_at FROM events "
        + where + " ORDER BY id DESC LIMIT ?", args + (limit,)
    )
    for row in result:
        try:
            row["detail"] = json.loads(row.pop("detail_json"))
        except (ValueError, TypeError):
            row["detail"] = {"warning": "invalid event payload"}
    return result


class SnapshotReader:
    """Read snapshots only. Even its SQLite connection opens with mode=ro."""

    def __init__(self, database: str | Path):
        try:
            self.path = Path(database).expanduser().resolve(strict=True)
        except FileNotFoundError as exc:
            raise ValueError("SQLite file does not exist") from exc
        if not self.path.is_file():
            raise ValueError("A real SQLite file is required")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        # SQLite's URI open mode refuses to create a missing database.
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        try:
            if not _exists(db, "memories") or not _exists(db, "blobs") or not _exists(db, "events"):
                raise ValueError("Not a ΦMemory9 database")
            yield db
        finally:
            db.close()

    def status(self) -> dict[str, Any]:
        with self._connection() as db:
            return {
                "schema": "phi-memory9/local-lab-r0.3",
                "connected": True,
                "mode": "read_only",
                "origin": "operator_selected_local_sqlite",
                "counts": {
                    key: _count(db, table) for key, table in (
                        ("blobs", "blobs"), ("memories", "memories"),
                        ("events", "events"), ("claims", "e_claims"),
                        ("contradictions", "e_conflicts"), ("approvals", "g_approvals"),
                    )
                },
                "evidence_available": _exists(db, "e_claims"),
            }

    def snapshot(self) -> dict[str, Any]:
        with self._connection() as db:
            blobs = _rows(db, "SELECT id,label,parent_blob_id,created_at FROM blobs "
                             "ORDER BY created_at,id LIMIT ?", (MAX_ROWS,))
            memories = _rows(db, "SELECT id,blob_id,parent_memory_id,status,"
                                "content,source_ref,created_at FROM memories "
                                "ORDER BY created_at,id LIMIT ?", (MAX_ROWS,))
            events = _events(db)
            claims = (
                _rows(db, "SELECT id,memory_id,statement,created_at FROM e_claims "
                          "ORDER BY created_at,id LIMIT ?", (MAX_ROWS,))
                if _exists(db, "e_claims") else []
            )
            conflicts = (
                _rows(db, "SELECT id,left_claim,right_claim,reason,created_at "
                          "FROM e_conflicts ORDER BY created_at,id LIMIT ?", (MAX_ROWS,))
                if _exists(db, "e_conflicts") else []
            )
            approvals = (
                _rows(db, "SELECT fingerprint,action,reason,applied_at,result_json "
                          "FROM g_approvals ORDER BY applied_at DESC,fingerprint DESC LIMIT ?",
                      (MAX_ROWS,))
                if _exists(db, "g_approvals") else []
            )
            for item in approvals:
                try:
                    item["result"] = json.loads(item.pop("result_json"))
                except (ValueError, TypeError):
                    item["result"] = {"warning": "Unreadable approval result"}
            counts = {
                name: _count(db, table) for name, table in (
                    ("blobs", "blobs"), ("memories", "memories"),
                    ("events", "events"), ("claims", "e_claims"),
                    ("contradictions", "e_conflicts"), ("approvals", "g_approvals"),
                )
            }
            return {
                "schema": "phi-memory9/local-snapshot-r0.3",
                "mode": "read_only",
                "blobs": blobs, "memories": memories, "events": events,
                "claims": claims, "contradictions": conflicts, "approvals": approvals, "counts": counts,
                "truncated": {
                    k: counts[k] > MAX_ROWS for k in
                    ("blobs", "memories", "events", "claims", "contradictions", "approvals")
                },
                "caution": "Claims and sources are operator declarations, not verified facts.",
            }

    def memory_detail(self, memory_id: str) -> dict[str, Any]:
        if not MEMORY_ID.fullmatch(memory_id):
            raise ValueError("Invalid memory identifier")
        with self._connection() as db:
            current = db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            if current is None:
                raise KeyError("Memory not found")
            chain: list[dict] = []
            seen: set[str] = set()
            cursor: str | None = memory_id
            while cursor is not None and len(chain) < 64:
                if cursor in seen:
                    raise ValueError("Cycle in memory ancestry")
                seen.add(cursor)
                row = db.execute(
                    "SELECT id,blob_id,parent_memory_id,status,content,source_ref,"
                    "created_at FROM memories WHERE id=?", (cursor,)
                ).fetchone()
                if row is None:
                    raise ValueError("Broken memory ancestor")
                chain.append(dict(row))
                cursor = row["parent_memory_id"]
            if cursor is not None:
                raise ValueError("Lineage exceeds inspection budget")
            chain.reverse()
            claims = (
                _rows(db, "SELECT id,memory_id,statement,created_at FROM e_claims "
                          "WHERE memory_id=? ORDER BY created_at,id LIMIT ?",
                      (memory_id, MAX_ROWS))
                if _exists(db, "e_claims") else []
            )
            claim_ids = [row["id"] for row in claims]
            evidence: list[dict] = []
            contradictions: list[dict] = []
            if claim_ids and _exists(db, "e_links") and _exists(db, "e_sources"):
                placeholders = ",".join("?" for _ in claim_ids)
                evidence = _rows(
                    db, "SELECT l.claim_id,l.stance,l.excerpt,s.label,s.locator,"
                    "s.kind,s.independence_group FROM e_links AS l "
                    "JOIN e_sources AS s ON l.source_id=s.id "
                    f"WHERE l.claim_id IN ({placeholders}) "
                    "ORDER BY l.id LIMIT ?", (*claim_ids, MAX_ROWS),
                )
            if claim_ids and _exists(db, "e_conflicts"):
                placeholders = ",".join("?" for _ in claim_ids)
                contradictions = _rows(
                    db, "SELECT id,left_claim,right_claim,reason,created_at "
                    "FROM e_conflicts WHERE "
                    f"left_claim IN ({placeholders}) OR right_claim IN ({placeholders}) "
                    "ORDER BY id LIMIT ?",
                    (*claim_ids, *claim_ids, MAX_ROWS),
                )
            return {
                "schema": "phi-memory9/memory-detail-r0.3",
                "memory": dict(current), "lineage": chain,
                "events": _events(db, "WHERE memory_id=?", (memory_id,), MAX_DETAIL_EVENTS),
                "claims": claims, "evidence": evidence,
                "contradictions": contradictions,
                "event_history_truncated": _count_events(db, memory_id) > MAX_DETAIL_EVENTS,
                "caution": "Evidence is operator-declared; interpretation is not verified.",
            }


def _count_events(db: sqlite3.Connection, memory_id: str) -> int:
    return db.execute(
        "SELECT COUNT(*) FROM events WHERE memory_id=?", (memory_id,)
    ).fetchone()[0]


def make_server(database: str | Path, port: int = 8769,
                web_dir: str | Path | None = None) -> ThreadingHTTPServer:
    """Build a strictly loopback HTTP service. Caller explicitly starts it."""
    if not 0 <= port <= 65535:
        raise ValueError("Port must be 0..65535")
    reader = SnapshotReader(database)
    # Validate upfront, rather than starting a listener for an invalid DB.
    reader.status()
    public = Path(web_dir).resolve() if web_dir else REPO_WEB_DIST
    root = public.resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            # No query/body content or local database paths logged.
            return

        def _headers(self, code: int, mime: str, length: int) -> None:
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            )
            self.end_headers()

        def _json(self, status: int, data: dict) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self._headers(status, "application/json; charset=utf-8", len(body))
            self.wfile.write(body)

        def _allowed(self) -> bool:
            host = self.headers.get("Host", "")
            port_now = self.server.server_port
            if host not in (f"127.0.0.1:{port_now}", f"localhost:{port_now}"):
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin != f"http://{host}":
                return False
            if self.headers.get("Sec-Fetch-Site", "") in ("cross-site", "same-site"):
                return False
            return True

        def do_GET(self) -> None:
            if not self._allowed():
                self._json(403, {"error": "Only same-origin loopback requests are permitted"})
                return
            if len(self.path) > 2048:
                self._json(414, {"error": "Path too long"})
                return
            path = urlsplit(self.path).path
            try:
                if path == "/api/v1/status":
                    self._json(200, reader.status())
                elif path == "/api/v1/snapshot":
                    self._json(200, reader.snapshot())
                elif path.startswith("/api/v1/memory/"):
                    memory_id = path.removeprefix("/api/v1/memory/")
                    self._json(200, reader.memory_detail(memory_id))
                elif path == "/":
                    self.send_response(302)
                    self.send_header("Location", "/PhiMemory9/")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                elif path in ("/PhiMemory9", "/PhiMemory9/", "/PhiMemory9/index.html"):
                    self._static(root / "index.html")
                elif path.startswith("/PhiMemory9/assets/"):
                    rel = path.removeprefix("/PhiMemory9/")
                    if not re.fullmatch(r"assets/[a-zA-Z0-9_.-]+", rel):
                        self._json(404, {"error": "Not found"})
                        return
                    self._static(root / rel)
                else:
                    self._json(404, {"error": "Not found"})
            except (FileNotFoundError, IsADirectoryError):
                self._json(404, {"error": "Compiled visual lab assets missing"})
            except KeyError:
                self._json(404, {"error": "Memory not found"})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except sqlite3.DatabaseError:
                self._json(503, {"error": "Memory database could not be read"})

        def _static(self, file: Path) -> None:
            resolved = file.resolve()
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise FileNotFoundError
            if resolved.stat().st_size > MAX_STATIC_BYTES:
                self._json(413, {"error": "Asset exceeds static budget"})
                return
            data = resolved.read_bytes()
            mime, _ = mimetypes.guess_type(resolved.name)
            self._headers(200, mime or "application/octet-stream", len(data))
            self.wfile.write(data)

        def do_POST(self) -> None:
            self._json(405, {"error": "R0.3 local lab is read-only"})

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def seed_lab(database: str | Path) -> dict[str, Any]:
    """Explicit one-time write to a *new* database using synthetic fixtures only."""
    from .core import MemoryEngine
    from .evidence import EvidenceLedger

    path = Path(database).expanduser()
    if str(path) == ":memory:" or path.exists():
        raise ValueError("seed-lab requires a new, nonexistent file path")
    if not path.parent.exists():
        raise ValueError("Parent folder does not exist")
    with MemoryEngine(path) as memory:
        root = memory.create_blob("Research observation")
        obsolete = memory.enter(
            root, "Prototype sensor readings suggest a stable signal.",
            source_ref="synthetic:field-note-A",
        )
        revised = memory.renew(
            obsolete, "A later synthetic reading requires independent review.",
            reason="Recorded new observation; earlier interpretation retired.",
        )
        routing = memory.loop(revised, route="inward")
        child = routing["child_memory_id"]
        ledger = EvidenceLedger(memory)
        first = ledger.claim(child, "The test sensor is functioning correctly.")
        second = ledger.claim(child, "The test sensor has an intermittent fault.")
        source = ledger.source(
            "Synthetic reading", "synthetic:reading-A",
            kind="synthetic", independence_group="fixture-one",
        )
        ledger.attach(first, source, "context", excerpt="A reading was recorded.")
        ledger.contradiction(first, second, "Interpretations require further tests.")
        return {
            "schema": "phi-memory9/synthetic-seed-r0.3",
            "root_blob": root, "nested_blob": routing["target_blob_id"],
            "memory_id": child, "audit": ledger.audit(),
        }
