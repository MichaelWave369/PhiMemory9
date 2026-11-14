import React, { useMemo, useState } from "react";

const STAGES = [
  { name: "ENTER", subtitle: "Receive", description: "Information crosses into the selected memory blob with a source pointer." },
  { name: "BIRTH", subtitle: "Identify", description: "A new addressable memory gains identity, origin, and provenance." },
  { name: "DEATH", subtitle: "Retire", description: "An obsolete interpretation retires. Its original evidence remains preserved." },
  { name: "TRANSFER", subtitle: "Transmit", description: "Surviving knowledge moves across a context boundary with traceable ancestry." },
  { name: "REBIRTH", subtitle: "Reinterpret", description: "An existing memory inspires a new interpretation with distinct lineage." },
  { name: "RESTORE", subtitle: "Recover", description: "A prior interpretation or relationship can be recovered with a recorded reason." },
  { name: "RENEW", subtitle: "Revise", description: "A new version supersedes an interpretation without rewriting history." },
  { name: "LIBERATION", subtitle: "Portable", description: "A source-linked portable snapshot becomes available for explicit review." },
  { name: "LOOP", subtitle: "Route", description: "The ninth gear chooses the next nested blob, creating a new entry point." },
];
const START_BLOB = { id: "blob-0", parentId: null, level: 0, label: "Origin" };
const INITIAL_EVENTS = [
  { id: 0, stage: "ENTER", blob: "blob-0", text: "Synthetic observation enters Origin" },
];
const MAX_DEPTH = 6, MAX_BLOBS = 32;

function StageRing({ phase, onStageHover }) {
  return (
    <div className="gear" aria-label="Nine-stage memory gear">
      <div className="orbit orbit-one" />
      <div className="orbit orbit-two" />
      {STAGES.slice(0, 8).map((stage, index) => {
        const angle = (index * 45 - 90) * Math.PI / 180;
        return (
          <div
            key={stage.name}
            className={"stage-node" + (index === phase ? " selected" : "")}
            style={{ left: (50 + 39 * Math.cos(angle)) + "%", top: (50 + 39 * Math.sin(angle)) + "%" }}
            onMouseEnter={() => onStageHover(index)}
            title={stage.description}
            aria-label={(index + 1) + ": " + stage.name}
          >
            <strong>{index + 1}</strong><span>{stage.name}</span>
          </div>
        );
      })}
      <div className={"central-gear" + (phase === 8 ? " selected" : "")} title={STAGES[8].description}>
        <span className="phi">Φ</span><strong>9 · LOOP</strong><small>ALTERMATH GEAR</small>
      </div>
    </div>
  );
}

function App() {
  const [phase, setPhase] = useState(0);
  const [blobs, setBlobs] = useState([START_BLOB]);
  const [activeId, setActiveId] = useState(START_BLOB.id);
  const [route, setRoute] = useState("inward");
  const [targetId, setTargetId] = useState("");
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [cycle, setCycle] = useState(1);
  const [hover, setHover] = useState(null);

  const active = useMemo(() => blobs.find(blob => blob.id === activeId) || START_BLOB, [blobs, activeId]);
  const selectedStage = STAGES[hover ?? phase];
  const canLoop = phase !== 8 || route === "hold" ||
    (route === "inward" && active.level < MAX_DEPTH && blobs.length < MAX_BLOBS) ||
    (route === "outward" && active.parentId !== null) ||
    (route === "lateral" && !!targetId && targetId !== activeId && blobs.some(b => b.id === targetId)) ||
    (route === "seed" && blobs.length < MAX_BLOBS);
  const log = (stage, blob, text) => setEvents(previous => [
    ...previous, { id: previous.length ? previous[previous.length - 1].id + 1 : 0, stage, blob, text },
  ].slice(-50));

  const next = () => {
    if (!canLoop) return;
    if (phase < 8) {
      const following = phase + 1;
      setPhase(following);
      log(STAGES[following].name, activeId,
        "Cycle " + cycle + ": " + STAGES[following].subtitle.toLowerCase() + " in " + active.label);
      return;
    }
    let destination = activeId;
    let nextBlob = null;
    if (route === "inward") {
      nextBlob = {
        id: "blob-" + blobs.length, parentId: activeId,
        level: active.level + 1, label: "Nested " + blobs.length,
      };
      destination = nextBlob.id;
    } else if (route === "outward") {
      destination = active.parentId;
    } else if (route === "lateral") {
      destination = targetId;
    } else if (route === "seed") {
      nextBlob = {
        id: "blob-" + blobs.length, parentId: null,
        level: 0, label: "New root " + blobs.length,
      };
      destination = nextBlob.id;
    }
    if (nextBlob) setBlobs(previous => [...previous, nextBlob]);
    const chosen = nextBlob || blobs.find(blob => blob.id === destination);
    log("LOOP", activeId, "Gear routes " + route + " → " + chosen.label);
    setActiveId(destination);
    setCycle(previous => previous + 1);
    setPhase(0);
  };

  const reset = () => {
    setPhase(0);
    setBlobs([START_BLOB]);
    setActiveId(START_BLOB.id);
    setEvents(INITIAL_EVENTS);
    setCycle(1);
    setRoute("inward");
    setTargetId("");
    setHover(null);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><span className="brand-symbol">Φ</span><span><strong>PHIMEMORY9</strong><small>RECURSIVE ALTERMATH MEMORY</small></span></div>
        <a href="https://github.com/MichaelWave369/PhiMemory9" target="_blank" rel="noreferrer">VIEW SOURCE ↗</a>
      </header>

      <main className="layout">
        <section className="intro">
          <div className="eyebrow">ΦPMA-9 / R0.1 · SYNTHETIC VISUAL LAB</div>
          <h1>Memory isn't a shelf.<br /><em>It's a living sequence.</em></h1>
          <p>Explore eight transformations and a ninth routing gear. Each completed loop can carry knowledge to another nested context while preserving the path home.</p>
          <div className="warning">SIMULATION ONLY · This visualization is not connected to the persistent Python engine. No factual claims, AI models, or private data are processed.</div>
        </section>

        <section className="panel visual">
          <div className="panel-heading"><span>01 / NINE-STAGE GEAR</span><span>CYCLE {String(cycle).padStart(2, "0")}</span></div>
          <StageRing phase={phase} onStageHover={setHover} />
          <div className="stage-info" onMouseLeave={() => setHover(null)}>
            <div className="stage-index">{String((hover ?? phase) + 1).padStart(2, "0")} / 09</div>
            <div><h2>{selectedStage.name}</h2><p>{selectedStage.description}</p></div>
          </div>
          <div className="controls">
            <button className="primary" onClick={next} disabled={!canLoop}>
              {phase === 8 ? "EXECUTE NINTH GEAR" : "ADVANCE SEQUENCE"} <span>→</span>
            </button>
            <button className="secondary" onClick={reset}>RESET</button>
          </div>
        </section>

        <section className="right">
          <div className="panel route">
            <div className="panel-heading"><span>02 / GEAR ROUTING</span><span>OPERATOR-CONTROLLED</span></div>
            <div className="field">
              <label htmlFor="route">NINTH-STAGE DESTINATION</label>
              <select id="route" value={route} onChange={event => setRoute(event.target.value)}>
                <option value="hold">Hold · Stay in current blob</option>
                <option value="inward">Inward · Create nested blob</option>
                <option value="outward">Outward · Return to parent</option>
                <option value="lateral">Lateral · Transfer to known blob</option>
                <option value="seed">Seed · Start a new root</option>
              </select>
            </div>
            {route === "lateral" && (
              <div className="field"><label htmlFor="target">SELECT TARGET BLOB</label>
                <select id="target" value={targetId} onChange={event => setTargetId(event.target.value)}>
                  <option value="">Select destination…</option>
                  {blobs.filter(b => b.id !== activeId).map(b => <option key={b.id} value={b.id}>{b.label}</option>)}
                </select>
              </div>
            )}
            <div className="stat"><span>ACTIVE BLOB</span><strong>{active.label}</strong></div>
            <div className="stat"><span>NESTING DEPTH</span><strong>{active.level} / {MAX_DEPTH}</strong></div>
            <div className="stat"><span>MEMORY CONTEXTS</span><strong>{blobs.length} / {MAX_BLOBS}</strong></div>
            {!canLoop && <p className="alert">Route unavailable. Select a valid destination or change the route.</p>}
          </div>

          <div className="panel tree">
            <div className="panel-heading"><span>03 / MEMORY BLOBS</span><span>ANCESTRY MAP</span></div>
            <div className="tree-nodes">
              {blobs.map(blob => (
                <div key={blob.id} className={"blob " + (blob.id === activeId ? "active" : "")}
                  style={{ marginLeft: Math.min(blob.level * 15, 90) + "px" }}>
                  <span className="blob-symbol">{blob.id === activeId ? "◆" : "◇"}</span>
                  <div><strong>{blob.label}</strong><small>{blob.parentId ? "CHILD OF " + blob.parentId.toUpperCase() : "ROOT CONTEXT"} · {blob.id.toUpperCase()}</small></div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel journal">
            <div className="panel-heading"><span>04 / EVENT LEDGER</span><span>{events.length} ENTRIES</span></div>
            <div className="entries" aria-live="polite">
              {events.slice().reverse().slice(0, 12).map(event => (
                <div className="entry" key={event.id}>
                  <span className={"tag " + (event.stage === "LOOP" ? "tag-loop" : "")}>{event.stage}</span>
                  <div><p>{event.text}</p><small>{event.blob.toUpperCase()}</small></div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <footer>ΦPMA-9 R0.1 · RESEARCH ARCHITECTURE, NOT A CLAIM OF VERIFIED COGNITION OR NATURAL LAW.</footer>
    </div>
  );
}
export default App;
