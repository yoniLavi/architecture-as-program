"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  CorpusCase,
  GraphDoc,
  GraphIndexEntry,
  GraphTrace,
  InjectionScenario,
  Meta,
  RunResponse,
} from "@/lib/types";
import {
  fetchCaseGraph,
  fetchCorpus,
  fetchGraph,
  fetchGraphIndex,
  fetchMeta,
  runCase,
  runInjectionScenario,
} from "@/lib/api";
import { isRejected } from "@/lib/types";
import GraphCanvas, { type WalkthroughHighlights } from "@/components/GraphCanvas";
import DetailPanel from "@/components/DetailPanel";
import Walkthrough, { walkthroughCanvasConfig } from "@/components/Walkthrough";

// The inspector page. It owns only view state; every graph fact comes from the
// API (canonical JSON + traces), and every run happens server-side.

export default function Inspector() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [graphIndex, setGraphIndex] = useState<GraphIndexEntry[]>([]);
  const [corpus, setCorpus] = useState<CorpusCase[]>([]);
  const [docs, setDocs] = useState<Record<string, GraphDoc>>({});

  const [caseName, setCaseName] = useState("customer-support");
  const [message, setMessage] = useState("");
  const [tier, setTier] = useState<"host" | "confined">("host");

  const [run, setRun] = useState<RunResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [scenario, setScenario] = useState<InjectionScenario | null>(null);
  const [walkStep, setWalkStep] = useState<number | null>(null);

  const [drillPath, setDrillPath] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // ── Initial load: meta, canonical graphs, the corpus ───────────────
  useEffect(() => {
    (async () => {
      try {
        const [m, index, cases] = await Promise.all([
          fetchMeta(),
          fetchGraphIndex(),
          fetchCorpus(),
        ]);
        setMeta(m);
        setGraphIndex(index);
        setCorpus(cases);
        setMessage(m.benign_message);
        const canonical = await Promise.all(index.map((g) => fetchGraph(g.file)));
        setDocs(Object.fromEntries(canonical.map((d, i) => [index[i].file, d])));
      } catch (e) {
        setError(`Could not reach the inspector API — is it running? (${e})`);
      }
    })();
  }, []);

  // Graph declared-name → file stem, the same resolution rule the runtime uses
  // for sub-graph references (a node whose name is a graph's declared name).
  const nameToFile = useMemo(
    () => Object.fromEntries(graphIndex.map((g) => [g.name, g.file])),
    [graphIndex],
  );
  const subgraphNames = useMemo(() => new Set(Object.keys(nameToFile)), [nameToFile]);

  const currentCase = corpus.find((c) => c.name === caseName) ?? null;

  // The doc the selected case renders: canonical file, or the server-derived
  // mutated graph for a mutation case (fetched on demand, cached under the
  // case name).
  useEffect(() => {
    if (!currentCase || docs[caseKey(currentCase)]) return;
    (async () => {
      try {
        const doc =
          currentCase.kind === "canonical"
            ? await fetchGraph(currentCase.name)
            : await fetchCaseGraph(currentCase.name);
        setDocs((d) => ({ ...d, [caseKey(currentCase)]: doc }));
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [currentCase, docs]);

  const baseDoc: GraphDoc | null = currentCase ? (docs[caseKey(currentCase)] ?? null) : null;

  // ── Drill-down: resolve the doc and trace at the current altitude ──
  const runTrace: GraphTrace | null = run && !isRejected(run) ? run.trace : null;

  const walkthroughActive = walkStep !== null && scenario !== null;
  const walkConfig: { trace: GraphTrace; highlights: WalkthroughHighlights } | null =
    walkthroughActive && scenario ? walkthroughCanvasConfig(walkStep, scenario) : null;

  // In walkthrough mode the canvas always shows the customer-support graph.
  const canvasRoot: GraphDoc | null = walkthroughActive
    ? (docs["customer-support"] ?? null)
    : baseDoc;
  const rootTrace = walkthroughActive ? (walkConfig?.trace ?? null) : runTrace;

  const { canvasDoc, canvasTrace } = useMemo(() => {
    let doc = canvasRoot;
    let trace = rootTrace;
    for (const nodeName of drillPath) {
      const graphName = doc?.nodes.find((n) => n.name === nodeName)?.name;
      const file = graphName ? nameToFile[graphName] : undefined;
      const child = file ? docs[file] : undefined;
      if (!child) return { canvasDoc: doc, canvasTrace: trace };
      trace = trace?.nodes.find((n) => n.node === nodeName)?.subgraph ?? null;
      doc = child;
    }
    return { canvasDoc: doc, canvasTrace: trace };
  }, [canvasRoot, rootTrace, drillPath, nameToFile, docs]);

  const selectedTrace =
    (selectedNode && canvasTrace?.nodes.find((n) => n.node === selectedNode)) || null;

  // ── Actions ────────────────────────────────────────────────────────
  const doRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    setScenario(null);
    setWalkStep(null);
    setDrillPath([]);
    try {
      setRun(await runCase({ case: caseName, message, tier }));
    } catch (e) {
      setError(String(e));
      setRun(null);
    } finally {
      setRunning(false);
    }
  }, [caseName, message, tier]);

  const startWalkthrough = useCallback(async () => {
    setRunning(true);
    setError(null);
    setRun(null);
    setDrillPath([]);
    setSelectedNode(null);
    setCaseName("customer-support");
    try {
      setScenario(await runInjectionScenario());
      setWalkStep(0);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }, []);

  const selectCase = (name: string) => {
    setCaseName(name);
    setRun(null);
    setError(null);
    setScenario(null);
    setWalkStep(null);
    setDrillPath([]);
    setSelectedNode(null);
  };

  const openSubgraph = useCallback((nodeName: string) => {
    setDrillPath((p) => [...p, nodeName]);
    setSelectedNode(null);
  }, []);

  const rejection = run && isRejected(run) ? run : null;

  // ── Render ─────────────────────────────────────────────────────────
  const canonicalCases = corpus.filter((c) => c.kind === "canonical");
  const mutationCases = corpus.filter((c) => c.kind === "mutation");

  return (
    <main className="frame">
      <header className="topbar">
        <h1>Signal-graph inspector</h1>
        <span className="sub">
          canonical graphs, executed server-side; traces overlaid as recorded
        </span>
        <span className="spacer" />
        {meta && (
          <span
            className={`badge ${meta.confined_tier_available ? "tier-sandbox" : "neutral"}`}
            data-testid="tier-availability"
          >
            {meta.confined_tier_available
              ? "confined tier available (wasmtime)"
              : "host tier only — wasmtime not installed"}
          </span>
        )}
      </header>

      <div className="columns">
        <aside className="sidebar">
          <section className="side-section">
            <h2>Canonical graphs</h2>
            <div className="case-list">
              {canonicalCases.map((c) => (
                <button
                  key={c.name}
                  className={`case-btn ${caseName === c.name ? "active" : ""}`}
                  onClick={() => selectCase(c.name)}
                  data-testid={`case-${c.name}`}
                >
                  <span>{c.name}</span>
                  <span className="verdict badge accepted">validates</span>
                </button>
              ))}
            </div>
          </section>

          <section className="side-section">
            <h2>Unsafe mutations (from the evaluation corpus)</h2>
            <div className="case-list">
              {mutationCases.map((c) => (
                <button
                  key={c.name}
                  className={`case-btn ${caseName === c.name ? "active" : ""}`}
                  onClick={() => selectCase(c.name)}
                  data-testid={`case-${c.name}`}
                >
                  <span className="mono">{c.name}</span>
                  <span className="verdict badge rejected">rejected</span>
                </button>
              ))}
            </div>
            <p className="note">
              The same cases the evaluation harness pins; running one shows the validator&apos;s
              rejection and its reason class.
            </p>
          </section>

          <section className="side-section">
            <h2>Run</h2>
            <div className="field">
              <label htmlFor="msg">Customer message (boundary input)</label>
              <textarea
                id="msg"
                className="msg"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                data-testid="message-input"
              />
              <div className="preset-row">
                <button className="chip-btn" onClick={() => meta && setMessage(meta.benign_message)}>
                  benign
                </button>
                <button
                  className="chip-btn danger"
                  onClick={() => meta && setMessage(meta.adversarial_message)}
                  data-testid="preset-adversarial"
                >
                  adversarial
                </button>
              </div>
            </div>
            <div className="field">
              <label>Enforcement tier</label>
              <div className="tier-row">
                <button
                  className={`chip-btn ${tier === "host" ? "active" : ""}`}
                  onClick={() => setTier("host")}
                  data-testid="tier-host"
                >
                  host
                </button>
                <button
                  className={`chip-btn ${tier === "confined" ? "active" : ""}`}
                  onClick={() => setTier("confined")}
                  disabled={!meta?.confined_tier_available}
                  title={
                    meta?.confined_tier_available
                      ? "run the ported nodes as WASM components"
                      : "wasmtime is not installed on the server"
                  }
                  data-testid="tier-confined"
                >
                  confined
                </button>
              </div>
            </div>
            <button className="run-btn" onClick={doRun} disabled={running || !baseDoc} data-testid="run-btn">
              {running ? "Running…" : "Run graph"}
            </button>
          </section>

          <section className="side-section">
            <h2>Guided scenario</h2>
            <button
              className="walkthrough-btn"
              onClick={startWalkthrough}
              disabled={running}
              data-testid="walkthrough-btn"
            >
              Prompt-injection walkthrough
            </button>
            <p className="note">
              Runs the adversarial message on both tiers and steps through what the trace shows:
              taint, discharge, capability scope, and the honest residual.
            </p>
          </section>
        </aside>

        <div className="canvas-col">
          {(drillPath.length > 0 || subgraphInView(canvasDoc, subgraphNames)) && canvasRoot && (
            <nav className="breadcrumbs" data-testid="breadcrumbs">
              {drillPath.length === 0 ? (
                <span className="crumb-here">{canvasRoot.name}</span>
              ) : (
                <>
                  <button onClick={() => setDrillPath([])}>{canvasRoot.name}</button>
                  {drillPath.map((n, i) => (
                    <span key={n}>
                      <span className="sep"> ▸ </span>
                      {i === drillPath.length - 1 ? (
                        <span className="crumb-here">{n}</span>
                      ) : (
                        <button onClick={() => setDrillPath(drillPath.slice(0, i + 1))}>{n}</button>
                      )}
                    </span>
                  ))}
                </>
              )}
            </nav>
          )}

          {canvasDoc ? (
            <GraphCanvas
              key={`${canvasDoc.name}-${drillPath.join("/")}-${walkthroughActive ? walkStep : "n"}`}
              doc={canvasDoc}
              trace={canvasTrace}
              subgraphNames={subgraphNames}
              rejectionErrors={rejection?.errors ?? null}
              selectedNode={selectedNode}
              onSelect={setSelectedNode}
              onOpenSubgraph={openSubgraph}
              highlights={walkConfig?.highlights}
            />
          ) : (
            <p style={{ padding: 24 }} className="note">
              {error ?? "Loading canonical graphs…"}
            </p>
          )}

          {rejection && (
            <div className="rejection-banner" data-testid="rejection-banner">
              <div className="head">
                ✗ Rejected at assembly time
                {rejection.reason_class && (
                  <span className="badge rejected" data-testid="reason-class">
                    caught by: {rejection.reason_class}
                  </span>
                )}
              </div>
              <ul className="errors">
                {rejection.errors.map((e) => (
                  <li key={e} className="mono">
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && canvasDoc && (
            <div className="rejection-banner">
              <div className="head">✗ {error}</div>
            </div>
          )}
        </div>

        {walkthroughActive && scenario ? (
          <Walkthrough
            scenario={scenario}
            step={walkStep}
            onStep={setWalkStep}
            onExit={() => {
              setWalkStep(null);
              setScenario(null);
            }}
          />
        ) : (
          canvasDoc && (
            <DetailPanel
              doc={canvasDoc}
              corpusCase={currentCase}
              selectedNode={selectedNode}
              nodeTrace={selectedTrace}
              run={run && !isRejected(run) ? run : null}
            />
          )
        )}
      </div>
    </main>
  );
}

function caseKey(c: CorpusCase): string {
  return c.kind === "canonical" ? c.name : `mutation:${c.name}`;
}

function subgraphInView(doc: GraphDoc | null, subgraphNames: Set<string>): boolean {
  return Boolean(doc?.nodes.some((n) => subgraphNames.has(n.name)));
}
