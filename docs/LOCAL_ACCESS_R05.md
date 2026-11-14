# ΦMemory9 R0.5 · Token-Gated Local Reader

R0.4's local server exposed data to any same-machine process that could
contact the loopback port. R0.5 adds a per-launch, high-entropy bearer token
to **every** SQLite-data API call. This reduces accidental access and
cross-origin browser abuse. It does not protect against a hostile local
administrator or malware with access to the process, terminal, or database.

## Operator workflow

~~~sh
python -m pip install -e .
phi-memory9 seed-lab --db ./lab.sqlite3
cd web && npm install && npm run build && cd ..
phi-memory9 serve --db ./lab.sqlite3
~~~

Open \`http://127.0.0.1:8769/PhiMemory9/\` **on the same computer**.

The CLI prints a fresh random access key in that terminal. Paste it into the
**Local Access Key** field and select **Unlock Read-only Inspector**.

- The key exists only in the current browser tab's React state; it is
  not put into a URL, cookie, localStorage, file, or browser query string.
- API requests send \`Authorization: Bearer <key>\`. The server compares it
  to the generated secret and returns HTTP 401 if missing or incorrect.
- The access key changes whenever \`serve\` restarts. **Lock Inspector**
  clears the UI's key and currently displayed memory data.
- The static visual demonstration does not need a key, and the public
  Pages version never accesses local memory.
- Browser history and URLs do not contain the access key. Be mindful of
  screen shares, terminal recordings, clipboard history, browser extensions,
  and local malware; the key is printed only for explicit local operation.

## Remaining boundaries

- The listener is strictly \`127.0.0.1\`, not LAN or cloud-facing.
- The server still has **no data write API**. All governance and memory writes
  require the R0.4 separately reviewed local CLI plan.
- No CORS permissions, restrictive Host/Origin/Fetch-Site checks, CSP,
  no-store responses, and static asset allowlist remain in place.
- HTTP to 127.0.0.1 is not HTTPS, and this is not an authenticated multi-user
  production service. Another privileged process on the same device may be
  able to inspect or modify process state or read the SQLite file.
- Never port-forward, tunnel, or publish the local server.
- The UI reads source pointers and claim text that may be sensitive. For
  actual personal or regulated data, a stronger access-control and encryption
  design is required.
- The API token only gates **read access via the HTTP service**. It does not
  encrypt the database or authenticate user identity.

R0.5 should be treated as security hardening of an experimental, local-first
research workflow, not as a security certification.
