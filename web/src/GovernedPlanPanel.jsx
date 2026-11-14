import React, { useMemo, useState } from "react";

/**
 * R0.4 produces a JSON proposal to save locally.
 * It NEVER calls the Python apply endpoint (there is none).
 * The operator must review the SHA-256 and run the CLI separately.
 */
export default function GovernedPlanPanel({ memory, blobs }) {
  const [action, setAction] = useState("loop");
  const [route, setRoute] = useState("inward");
  const [target, setTarget] = useState("");
  const [content, setContent] = useState("");
  const [reason, setReason] = useState("");
  const [downloaded, setDownloaded] = useState(false);

  const canWriteContent = ["renew", "rebirth"].includes(action);
  const needsTarget = action === "rebirth" || action === "transfer" ||
    (action === "loop" && route === "lateral");
  const isValid = memory && reason.trim().length > 0 && reason.length <= 512
    && (!canWriteContent || (content.trim() && content.length <= 8192))
    && (!needsTarget || !!target)
    && (action !== "restore" || memory.status === "retired")
    && (action !== "death" && action !== "renew" || memory.status === "active");

  const proposal = useMemo(() => {
    if (!memory || !isValid) return null;
    const p = {
      schema: "phi-memory9/operator-plan-r0.4",
      action,
      reason: reason.trim(),
      memory_id: memory.id,
    };
    if (action === "loop") {
      p.route = route;
      if (route === "lateral") p.target_blob_id = target;
    } else if (action === "transfer") {
      p.target_blob_id = target;
    } else if (action === "renew") {
      p.content = content;
    } else if (action === "rebirth") {
      p.content = content;
      p.target_blob_id = target;
    }
    return p;
  }, [memory, isValid, action, route, target, reason, content]);

  function downloadProposal() {
    if (!proposal) return;
    const payload = new Blob([JSON.stringify(proposal, null, 2) + "\n"],
      { type: "application/json" });
    const href = URL.createObjectURL(payload);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = "phi-r04-" + action + "-" + memory.id.slice(0, 8) + ".json";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(href);
    setDownloaded(true);
  }

  return (
    <div className="governance-panel">
      <div className="panel-heading">
        <span>OPERATOR PLAN BUILDER · R0.4</span>
        <span>NO BROWSER WRITES</span>
      </div>
      <p className="muted">
        Create a proposed memory operation as a local JSON file. Inspect the plan
        from the terminal and explicitly approve its exact fingerprint.
        This page never submits a mutation or grants an agent authority.
      </p>
      <div className="gov-form">
        <label>
          ACTION
          <select value={action} onChange={event => {
            setAction(event.target.value); setDownloaded(false);
          }}>
            <option value="loop">9 · Loop / Altermath gear</option>
            <option value="renew">7 · Renew / replace interpretation</option>
            <option value="death">3 · Death / retire interpretation</option>
            <option value="restore">6 · Restore retired interpretation</option>
            <option value="rebirth">5 · Rebirth / reinterpret descendant</option>
            <option value="transfer">4 · Transfer to another blob</option>
          </select>
        </label>
        {action === "loop" && (
          <label>
            NINTH GEAR ROUTE
            <select value={route} onChange={event => {
              setRoute(event.target.value); setDownloaded(false);
            }}>
              <option value="hold">Hold · remain</option>
              <option value="inward">Inward · create child</option>
              <option value="outward">Outward · parent</option>
              <option value="lateral">Lateral · choose target</option>
              <option value="seed">Seed · new root</option>
            </select>
          </label>
        )}
        {needsTarget && (
          <label>
            TARGET MEMORY BLOB
            <select value={target} onChange={event => {
              setTarget(event.target.value); setDownloaded(false);
            }}>
              <option value="">Choose an existing blob</option>
              {blobs.filter(blob => blob.id !== memory.blob_id).map(blob => (
                <option value={blob.id} key={blob.id}>{blob.label} · {blob.id.slice(0, 9)}</option>
              ))}
            </select>
          </label>
        )}
        {canWriteContent && (
          <label>
            PROPOSED NEW CONTENT
            <textarea rows="3" maxLength={8192} value={content}
              placeholder="A new interpretation, not an overwrite of the old record."
              onChange={event => {
                setContent(event.target.value); setDownloaded(false);
              }} />
          </label>
        )}
        <label>
          OPERATOR REASON · REQUIRED
          <input value={reason} maxLength={512}
            placeholder="Why should this memory change or move?"
            onChange={event => {
              setReason(event.target.value); setDownloaded(false);
            }} />
        </label>
      </div>
      {proposal && <pre className="gov-preview">{JSON.stringify(proposal, null, 2)}</pre>}
      <button type="button" className="primary gov-download"
        disabled={!proposal} onClick={downloadProposal}>
        DOWNLOAD APPROVAL PLAN <span>↓</span>
      </button>
      {downloaded && (
        <div className="gov-help">
          <strong>Plan file downloaded, not applied.</strong>
          <p>Review it using <code>phi-memory9 plan-review --db ./lab.sqlite3 --plan ./YOUR-PLAN.json</code></p>
          <p>Then consciously apply the exact reviewed digest with <code>phi-memory9 apply-plan --db ./lab.sqlite3 --plan ./YOUR-PLAN.json --approve-sha256 DIGEST</code></p>
          <p>Use <strong>REFRESH SNAPSHOT</strong> above to view the real result.</p>
        </div>
      )}
    </div>
  );
}
