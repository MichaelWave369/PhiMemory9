# ΦMemory9 R0.3 · Living Memory Inspector

A real **read-only** connection between the existing SQLite runtime and the React visual lab, served from **one explicit IPv4 loopback origin**.

## Quick start

Use a **new synthetic** database first. Run from a fresh checkout of PhiMemory9:

~~~sh
python -m pip install -e .
phi-memory9 seed-lab --db ./lab.sqlite3
cd web
npm install
npm run build
cd ..
phi-memory9 serve --db ./lab.sqlite3
~~~

Open **http://127.0.0.1:8769/PhiMemory9/** in a browser on that same computer.

The upper **Living Memory Inspector** reads actual database blobs, memories, event receipts, ancestry and R0.2 evidence/contradiction records. The lower nine-stage ring **remains a labeled synthetic simulator**. No control in the browser modifies SQLite. The sample database contains invented fixture claims only.

For an existing local ΦMemory9 database, omit \`seed-lab\` and pass its explicit file path to \`serve --db\`. You may specify another port with \`--port\`, and a separate compiled static folder with \`--web-dir\`.

## Security and scope

- Service listens on **127.0.0.1 only**, not 0.0.0.0 or LAN; no tunneling or cloud setup.
- The browser and API are served from the **same origin**. No CORS headers are provided. Strict Host/Origin/Fetch-Site checking and a restrictive CSP are included.
- The database connection uses SQLite \`mode=ro\` and \`query_only=ON\`. The server exposes GET status, snapshot, and details endpoints; POST/PUT/PATCH/DELETE are rejected.
- A local browser tab or local process with access to this loopback port can read the data while the server is running. **This is not an authenticated multi-user service**; avoid secrets, personal data and real sensitive memories. Never port-forward or publish the service.
- Compiled static assets are restricted to \`/PhiMemory9/\` and a flat allowlisted \`assets/\` path; no filesystem directory listing.
- Lists are capped at 200 entries per collection and 100 events per detail. Counts remain full. This is a UI preview, not a complete export or unlimited query API.
- All source stances and independence groups remain **operator declarations**, not verified evidence.
- Hash-chain/audit reports do not make the database tamperproof.
- GitHub Pages and other public hosting cannot read your local database. The local read-only inspector appears only from the explicitly started loopback server.

## GET API

- \`/api/v1/status\`: capability/status, count summaries, no file paths.
- \`/api/v1/snapshot\`: bounded data previews of blobs, memories, events, claims and contradictions.
- \`/api/v1/memory/<32-character-memory-id>\`: one memory, lineage, per-memory stage events, evidence links, contradictions.

Every response is JSON with \`Cache-Control: no-store\`. The API never writes, runs a model, fetches from the internet, or forwards data.

## Tests and limits

~~~sh
python -m unittest discover -s tests -v
cd web && npm run build
~~~

R0.3 is a **local visualization bridge**, not a general-purpose memory management server. No browser mutation, multi-user auth, real remote transport, permissions policies, vector-search integration, or production deployment is claimed. A browser view of an event is not proof of scientific validity.

Next milestone: a separately permissioned local mutation protocol, durable redaction/privacy controls, verified export contracts, and a larger held-out retrieval benchmark before live integrations.
