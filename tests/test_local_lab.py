"""R0.3: real read-only SQLite bridge, loopback-only server, and seed tests."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from phimemory9 import MemoryEngine
from phimemory9.local_lab import SnapshotReader, make_server, seed_lab


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "data.sqlite3"
        self.seed = seed_lab(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_refuses_existing_database(self):
        with self.assertRaises(ValueError):
            seed_lab(self.path)

    def test_read_only_memory_and_lineage_with_real_loop(self):
        reader = SnapshotReader(self.path)
        status = reader.status()
        self.assertEqual(status["mode"], "read_only")
        self.assertEqual(status["counts"]["memories"], 3)
        self.assertEqual(status["counts"]["blobs"], 2)
        snapshot = reader.snapshot()
        self.assertTrue(any(e["stage"] == "LOOP" for e in snapshot["events"]))
        self.assertEqual(len(snapshot["contradictions"]), 1)
        details = reader.memory_detail(self.seed["memory_id"])
        self.assertEqual(len(details["lineage"]), 3)
        self.assertEqual(len(details["claims"]), 2)
        self.assertEqual(len(details["contradictions"]), 1)
        self.assertEqual(details["evidence"][0]["kind"], "synthetic")

    def test_governed_receipt_visible_in_read_only_snapshot(self):
        from phimemory9.governance import SCHEMA, apply, fingerprint
        with MemoryEngine(self.path) as engine:
            plan = {
                "schema": SCHEMA, "action": "loop", "route": "hold",
                "reason": "Synthetic operator review",
                "memory_id": self.seed["memory_id"],
            }
            apply(engine, plan, fingerprint(plan))
        reader = SnapshotReader(self.path)
        snapshot = reader.snapshot()
        self.assertEqual(snapshot["counts"]["approvals"], 1)
        self.assertEqual(snapshot["approvals"][0]["action"], "loop")
        self.assertEqual(snapshot["approvals"][0]["result"]["route"], "hold")
        self.assertEqual(reader.status()["counts"]["approvals"], 1)

    def test_reader_does_not_modify_file_or_event_count(self):
        before = self.path.read_bytes()
        reader = SnapshotReader(self.path)
        reader.snapshot()
        reader.status()
        reader.memory_detail(self.seed["memory_id"])
        self.assertEqual(before, self.path.read_bytes())
        with MemoryEngine(self.path) as db:
            self.assertTrue(db.verify()["ok"])

    def test_unknown_identifier_and_missing_database(self):
        with self.assertRaises(ValueError):
            SnapshotReader(self.path.with_name("missing.sqlite3"))
        with self.assertRaises(ValueError):
            SnapshotReader(self.path).memory_detail("bad-id")
        with self.assertRaises(KeyError):
            SnapshotReader(self.path).memory_detail("a" * 32)

    def test_empty_r01_database_without_evidence_tables(self):
        path = Path(self.tmp.name) / "bare.sqlite3"
        with MemoryEngine(path) as db:
            root = db.create_blob("root")
            mid = db.enter(root, "Plain memory")
        reader = SnapshotReader(path)
        self.assertEqual(reader.status()["counts"]["claims"], 0)
        self.assertEqual(reader.memory_detail(mid)["contradictions"], [])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.dbpath = root / "local.sqlite3"
        self.seed = seed_lab(self.dbpath)
        dist = root / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<html>local visual lab</html>", encoding="utf8")
        (dist / "assets" / "app.js").write_text("console.log('local')", encoding="utf8")
        self.server = make_server(self.dbpath, 0, dist)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.host = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def request(self, path, method="GET", headers=None, authorized=True):
        request_headers = dict(headers or {})
        if authorized and path.startswith("/api/v1/"):
            request_headers.setdefault(
                "Authorization", "Bearer " + self.server.access_token
            )
        req = urllib.request.Request(
            self.host + path, method=method, headers=request_headers
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()

    def test_access_key_required_for_all_database_endpoints(self):
        for endpoint in (
            "/api/v1/status", "/api/v1/snapshot",
            "/api/v1/memory/" + self.seed["memory_id"],
        ):
            status, _, _ = self.request(endpoint, authorized=False)
            self.assertEqual(status, 401)
            status, _, _ = self.request(
                endpoint, authorized=False,
                headers={"Authorization": "Bearer wrong"},
            )
            self.assertEqual(status, 401)
        status, _, _ = self.request(
            "/api/v1/snapshot?token=" + self.server.access_token,
            authorized=False,
        )
        self.assertEqual(status, 401)
        status, _, body = self.request("/api/v1/status")
        self.assertEqual(status, 200)
        self.assertNotIn(self.server.access_token.encode(), body)

    def test_static_assets_are_public_but_secret_is_not_embedded(self):
        status, _, html = self.request("/PhiMemory9/", authorized=False)
        self.assertEqual(status, 200)
        self.assertNotIn(self.server.access_token.encode(), html)
        self.assertGreaterEqual(len(self.server.access_token), 24)

    def test_short_operator_secret_refused(self):
        with self.assertRaises(ValueError):
            make_server(self.dbpath, 0, access_token="guessable")

    def test_json_and_browser_assets_share_local_origin(self):
        code, headers, body = self.request("/api/v1/status")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["mode"], "read_only")
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), None)
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        code, _, body = self.request("/PhiMemory9/")
        self.assertEqual(code, 200)
        self.assertIn(b"local visual lab", body)
        code, _, body = self.request("/PhiMemory9/assets/app.js")
        self.assertEqual(code, 200)
        self.assertIn(b"console.log", body)

    def test_snapshot_and_selected_memory_are_readable(self):
        code, _, body = self.request("/api/v1/snapshot")
        result = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(result["counts"]["contradictions"], 1)
        code, _, body = self.request(
            "/api/v1/memory/" + self.seed["memory_id"]
        )
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["memory"]["id"], self.seed["memory_id"])

    def test_cross_site_and_dangerous_methods_blocked(self):
        code, _, _ = self.request(
            "/api/v1/snapshot",
            headers={"Origin": "https://malicious.example"}
        )
        self.assertEqual(code, 403)
        code, _, _ = self.request(
            "/api/v1/snapshot",
            headers={"Sec-Fetch-Site": "cross-site"}
        )
        self.assertEqual(code, 403)
        code, _, _ = self.request("/api/v1/snapshot", method="POST")
        self.assertEqual(code, 405)
        code, _, _ = self.request("/api/v1/snapshot", method="DELETE")
        self.assertEqual(code, 405)
        code, _, _ = self.request("/PhiMemory9/../../../etc/passwd")
        self.assertEqual(code, 404)

    def test_invalid_host_header_blocked(self):
        code, _, _ = self.request(
            "/api/v1/snapshot", headers={"Host": "attacker.example"}
        )
        self.assertEqual(code, 403)

    def test_bad_and_unknown_memory_ids(self):
        code, _, _ = self.request("/api/v1/memory/../secret")
        self.assertEqual(code, 400)
        code, _, _ = self.request("/api/v1/memory/" + "a"*32)
        self.assertEqual(code, 404)

    def test_server_bound_only_to_ipv4_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
