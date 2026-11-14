# ΦMemory9 R0.4 · Governed Memory Operations

R0.4 is **human-reviewed local mutation**. It does not add a browser write
endpoint or background automation. SQLite changes occur only from an
explicit operator CLI command with a matching reviewed plan fingerprint.

## From the React inspection interface

First, run R0.3's local reader with your **synthetic** database:

~~~sh
python -m pip install -e .
phi-memory9 seed-lab --db ./lab.sqlite3
cd web && npm install && npm run build && cd ..
phi-memory9 serve --db ./lab.sqlite3
~~~

Open http://127.0.0.1:8769/PhiMemory9/ and select a memory. In the **Operator Plan Builder**, choose Loop (or another supported operation), add a reason and download the resulting JSON plan. This is an offline file download, *not* a request to mutate SQLite.

In another terminal in the project directory, review the plan and get the canonical SHA-256:

~~~sh
phi-memory9 plan-review --db ./lab.sqlite3 --plan ./phi-r04-loop-EXAMPLE.json
~~~

Read the displayed target ID, target text/status, operation, route, reason and digest. If approved, perform that exact mutation:

~~~sh
phi-memory9 apply-plan --db ./lab.sqlite3 --plan ./phi-r04-loop-EXAMPLE.json --approve-sha256 REVIEWED_64_CHAR_DIGEST
~~~

Then use **Refresh Snapshot** in the browser. The real SQLite memory, its events and the approval receipt are stored together. A plan cannot be applied twice (replay refused). Changing even a single semantic plan field changes its approval SHA.

## Canonical plan contract

~~~json
{
  "schema": "phi-memory9/operator-plan-r0.4",
  "action": "loop",
  "reason": "Explicit human-reviewed lineage experiment",
  "memory_id": "REPLACE_WITH_32_HEX_MEMORY_ID",
  "route": "inward"
}
~~~

Supported operations: \`enter\`, \`death\`, \`restore\`, \`renew\`, \`rebirth\`, \`transfer\`, and \`loop\`. All plans require a nonempty operator reason. Unknown fields, malformed JSON, duplicate JSON keys, oversized files, invalid routes, missing targets, and mismatched approvals fail closed. The original nine-stage semantics remain intact: a memory need not follow all stages in order.

Plan fingerprints are content digests, **not cryptographic signatures or authentication**. The CLI trusts the local operator to select the correct database and verify the plan. A malicious local process with access to the SQLite file can bypass the CLI. Do not use this as a multi-user governance system.

To make the plan, application receipt and memory mutations atomic, the existing \`MemoryEngine\` uses nested-safe SQLite savepoints inside an explicit outer transaction. The \`g_approvals\` table is replay protection and an audit pointer, not a tamperproof ledger.

## Privacy-aware local exports

Default exports are metadata-only: identifiers, blob ancestry, statuses, SHA-256
content fingerprints, and event counts. Original content and source references are omitted.

~~~sh
phi-memory9 export-memory --db ./lab.sqlite3 --memory MEMORY_ID --out ./redacted-export.json
~~~

To include the full content, first review the precise content-bound digest:

~~~sh
phi-memory9 export-review --db ./lab.sqlite3 --memory MEMORY_ID
phi-memory9 export-memory --db ./lab.sqlite3 --memory MEMORY_ID --out ./full-export.json --include-content --approve-sha256 REVIEWED_DIGEST
~~~

Exports are local files created without overwriting existing destinations; they are never uploaded or published. **Metadata-only is not anonymity.** Identifiers, sizes, ancestry and SHA-256 hashes can still reveal information if correlated with other material. Source URLs/excerpts are excluded from the default export, and metadata is not proof of independent evidence.

## Boundaries and next steps

- Browser is read-only. The plan builder only downloads JSON.
- Server is localhost-only and still unauthenticated to other local programs; do not open sensitive databases or forward ports.
- No autonomous approval, model judgment, remote write APIs, or runtime connector execution.
- No external verification of truth claims; R0.2 evidence remains operator-declared.
- No proven improvement over standard memory retrieval.
- Future work: schema migrations, permissions and content-level redaction, held-out retrieval evaluations, stronger authenticated local IPC, and opt-in interoperability adapters.
