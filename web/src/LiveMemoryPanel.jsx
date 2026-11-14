import React, { useCallback, useEffect, useMemo, useState } from "react";
import GovernedPlanPanel from "./GovernedPlanPanel.jsx";

/** R0.3 inspection surface. There are intentionally NO write actions here. */
function LiveMemoryPanel() {
  const isLocal = useMemo(() => {
    const host = window.location.hostname;
    return (host === "127.0.0.1" || host === "localhost")
      && window.location.pathname.startsWith("/PhiMemory9");
  }, []);
  const [bridge, setBridge] = useState("disconnected");
  const [snapshot, setSnapshot] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!isLocal) return;
    setBridge("checking");
    setError("");
    try {
      const status = await fetch("/api/v1/status", { cache: "no-store" });
      if (!status.ok || !(status.headers.get("content-type") || "").includes("application/json")) {
        throw new Error("No local ΦMemory9 service is available.");
      }
      const state = await status.json();
      if (!state.connected || state.mode !== "read_only") {
        throw new Error("Local service did not report a read-only connection.");
      }
      const response = await fetch("/api/v1/snapshot", { cache: "no-store" });
      if (!response.ok) throw new Error("The SQLite snapshot could not be read.");
      const payload = await response.json();
      if (payload.schema !== "phi-memory9/local-snapshot-r0.3") {
        throw new Error("Unsupported snapshot format.");
      }
      setSnapshot(payload);
      setSelectedId(old => payload.memories.some(m => m.id === old)
        ? old : (payload.memories[0]?.id || ""));
      setBridge("connected");
    } catch (err) {
      setBridge("disconnected");
      setError(err.message || "Local bridge unavailable.");
    }
  }, [isLocal]);

  useEffect(() => {
    if (isLocal) refresh();
  }, [isLocal, refresh]);

  useEffect(() => {
    if (bridge !== "connected" || !selectedId) {
      setDetail(null);
      return;
    }
    const controller = new AbortController();
    setDetail(null);
    fetch("/api/v1/memory/" + encodeURIComponent(selectedId), {
      cache: "no-store", signal: controller.signal,
    })
      .then(response => {
        if (!response.ok) throw new Error("Memory details unavailable");
        return response.json();
      })
      .then(setDetail)
      .catch(err => {
        if (err.name !== "AbortError") setError(err.message || "Detail lookup failed");
      });
    return () => controller.abort();
  }, [selectedId, bridge]);

  const loopEvents = (snapshot?.events || []).filter(event => event.stage === "LOOP");
  const summaries = snapshot?.counts || {};
  const activeMemory = snapshot?.memories.find(memory => memory.id === selectedId);

  return (
    <section className="panel live-panel" aria-label="Real local memory inspection">
      <div className="panel-heading">
        <span>00 / LIVING MEMORY INSPECTOR</span>
        <span>{bridge === "connected" ? "LOCAL SQLITE · READ ONLY" : "LOCAL BRIDGE · OFF"}</span>
      </div>
      <div className="live-head">
        <div>
          <h2>Inside the actual memory.</h2>
          <p>Inspectable SQLite ancestry, operator-declared evidence, contradictions and ninth-gear receipts.</p>
        </div>
        {bridge === "connected" && (
          <button className="secondary" onClick={refresh} type="button">REFRESH SNAPSHOT</button>
        )}
      </div>
      {bridge !== "connected" ? (
        <div className="offline-note">
          <strong>{bridge === "checking" ? "Connecting to local memory…" : "Static simulator only"}</strong>
          <p>The public visual lab cannot connect to your computer or read its databases. Open the separate local read-only server to view real records.</p>
          {error && <p className="error-message">{error}</p>}
          <code>phi-memory9 serve --db ./lab.sqlite3</code>
        </div>
      ) : (
        <>
          <div className="live-metrics">
            {[
              ["BLOBS", summaries.blobs],
              ["MEMORIES", summaries.memories],
              ["EVENTS", summaries.events],
              ["CLAIMS", summaries.claims],
              ["CONTRADICTIONS", summaries.contradictions],
            ].map(([name, value]) => (
              <div className="live-metric" key={name}><strong>{value ?? 0}</strong><span>{name}</span></div>
            ))}
          </div>
          {Object.values(snapshot.truncated || {}).some(Boolean) && (
            <p className="alert">Large database: preview is capped at 200 entries per collection. Counts remain complete.</p>
          )}
          <div className="live-grid">
            <div className="live-column">
              <h3>Stored memory</h3>
              {snapshot.memories.length ? (
                <>
                  <label className="live-select-label" htmlFor="stored-memory">SELECT AN ACTUAL RECORD</label>
                  <select id="stored-memory" value={selectedId} onChange={event => setSelectedId(event.target.value)}>
                    {snapshot.memories.map(memory => (
                      <option key={memory.id} value={memory.id}>
                        {memory.status === "retired" ? "[retired] " : ""}
                        {memory.content.slice(0, 80)}
                      </option>
                    ))}
                  </select>
                  <div className="real-content">
                    <strong>{activeMemory?.status === "retired" ? "RETIRED INTERPRETATION" : "ACTIVE MEMORY"}</strong>
                    <p>{detail?.memory?.content ?? activeMemory?.content}</p>
                    <small>SOURCE POINTER: {detail?.memory?.source_ref || activeMemory?.source_ref || "None declared"}</small>
                    <small>MEMORY ID: {selectedId}</small>
                  </div>
                </>
              ) : <p className="muted">Database contains no stored memories.</p>}
              {detail && (
                <>
                  <h3>Memory ancestry</h3>
                  <div className="live-history">
                    {detail.lineage.map((memory, index) => (
                      <div className="live-lineage" key={memory.id}>
                        <span>{index + 1}</span>
                        <div><strong>{memory.status.toUpperCase()} · {memory.id.slice(0, 10)}</strong>
                          <p>{memory.content}</p></div>
                      </div>
                    ))}
                  </div>
                  <h3>Evidence & disagreements</h3>
                  <p className="muted">Source stances and independence groups are declared, not verified.</p>
                  {detail.claims.length ? detail.claims.map(claim => (
                    <div className="claim-item" key={claim.id}>
                      <strong>CLAIM</strong><p>{claim.statement}</p>
                    </div>
                  )) : <p className="muted">No claims have been attached to this memory.</p>}
                  {detail.evidence.map((item, index) => (
                    <div className="evidence-item" key={index}>
                      <strong>{item.stance.toUpperCase()} · {item.kind.toUpperCase()}</strong>
                      <p>{item.label}: {item.excerpt || "No excerpt supplied"}</p>
                      <small>GROUP: {item.independence_group} · {item.locator}</small>
                    </div>
                  ))}
                  {detail.contradictions.map(item => (
                    <div className="contradiction" key={item.id}>
                      <strong>RECORDED CONTRADICTION</strong>
                      <p>{item.reason}</p>
                      <small>{item.left_claim.slice(0, 10)} ↔ {item.right_claim.slice(0, 10)}</small>
                    </div>
                  ))}
                </>
              )}
            </div>
            <div className="live-column">
              <h3>Real ninth-gear events</h3>
              {loopEvents.length ? loopEvents.map(event => (
                <div className="loop-record" key={event.id}>
                  <strong>{String(event.detail?.route || "unknown").toUpperCase()}</strong>
                  <p>FROM: {event.memory_id.slice(0, 12)}</p>
                  <p>TO BLOB: {event.detail?.target_blob_id?.slice(0, 12) || "HOLD"}</p>
                  <p>CHILD: {event.detail?.child_memory_id?.slice(0, 12) || "None"}</p>
                  <small>{event.recorded_at}</small>
                </div>
              )) : <p className="muted">No ninth-gear routing events have been recorded.</p>}
              <h3>Selected memory events</h3>
              {detail?.events?.length ? detail.events.map(event => (
                <div className="event-line" key={event.id}>
                  <span className="tag">{event.stage}</span>
                  <p>{event.recorded_at}</p>
                </div>
              )) : <p className="muted">Choose a memory to view its real event history.</p>}
            </div>
          </div>
          {activeMemory && <GovernedPlanPanel key={activeMemory.id} memory={activeMemory} blobs={snapshot.blobs} />}
          <p className="read-only-warning">READ ONLY. The loop controls below still run the independent synthetic simulator; they do not mutate SQLite. No agent or external system has memory authority.</p>
        </>
      )}
    </section>
  );
}
export default LiveMemoryPanel;
