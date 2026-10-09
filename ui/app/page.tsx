"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  CorpusCase,
  FeedCaseGraphs,
  FeedCases,
  FeedRunResponse,
  GraphDoc,
  GraphIndexEntry,
  GraphTrace,
  InjectionScenario,
  LatestDigest,
  Meta,
  RunResponse,
} from "@/lib/types";
import {
  fetchCaseGraph,
  fetchCorpus,
  fetchFeedCaseGraphs,
  fetchFeedCases,
  fetchGraph,
  fetchGraphIndex,
  fetchLatestDigest,
  fetchMeta,
  runCase,
  runFeed,
  runInjectionScenario,
} from "@/lib/api";
import { isFeedAcceptedOnly, isFeedRejected, isFeedRunOk, isRejected } from "@/lib/types";
import GraphCanvas, { type WalkthroughHighlights } from "@/components/GraphCanvas";
import DetailPanel from "@/components/DetailPanel";
import Walkthrough, { walkthroughCanvasConfig } from "@/components/Walkthrough";
import { FeedCaseInfo, HostilePanel } from "@/components/FeedPanel";

// The inspector page. It owns only view state; every graph fact comes from the
// API (canonical JSON + traces), and every run happens server-side.

// The feed-triage service's canonical case, as the API names it (also the file
// stem of its graph, and the default `case` of `POST /api/feed/run`).
const FEED_CANONICAL = "feed-triage";

// One step down from a graph into the graph a node names. `element` is the
// index of the element run opened on a per-item node, or null: a plain
// sub-graph node, or a per-item node viewed with no trace to nest.
interface DrillStep {
  node: string;
  element: number | null;
}

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

  const [drillPath, setDrillPath] = useState<DrillStep[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // The feed-triage service: its cases, the selected one (null = the view is on
  // the customer-support corpus), the rewired graph pairs fetched so far, and
  // the last tick.
  const [feedCases, setFeedCases] = useState<FeedCases | null>(null);
  const [feedCaseName, setFeedCaseName] = useState<string | null>(null);
  const [feedGraphs, setFeedGraphs] = useState<Record<string, FeedCaseGraphs>>({});
  const [feedRun, setFeedRun] = useState<FeedRunResponse | null>(null);
  const [hostileOpen, setHostileOpen] = useState(false);
  const [hostileRunning, setHostileRunning] = useState<string | null>(null);
  const [latest, setLatest] = useState<LatestDigest | { error: string } | null>(null);
  const [showLatest, setShowLatest] = useState(false);

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
    // The feed routes load on their own, so a server without them still serves
    // the rest of the inspector.
    fetchFeedCases().then(setFeedCases, () => setFeedCases(null));
    fetchLatestDigest().then(setLatest, () => setLatest(null));
  }, []);

  // Graph declared-name → file stem, the same resolution rule the runtime uses
  // for sub-graph references (a node whose name is a graph's declared name).
  const nameToFile = useMemo(
    () => Object.fromEntries(graphIndex.map((g) => [g.name, g.file])),
    [graphIndex],
  );
  const subgraphNames = useMemo(() => new Set(Object.keys(nameToFile)), [nameToFile]);

  const inFeed = feedCaseName !== null;
  const currentCase = inFeed ? null : (corpus.find((c) => c.name === caseName) ?? null);
  const currentFeedCase = feedCases?.corpus.find((c) => c.name === feedCaseName) ?? null;
  // A rewiring renders the pair the API derived for it; the canonical case
  // renders the served files themselves.
  const feedRewired =
    currentFeedCase && currentFeedCase.kind !== "canonical"
      ? (feedGraphs[currentFeedCase.name] ?? null)
      : null;

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

  useEffect(() => {
    if (!currentFeedCase || currentFeedCase.kind === "canonical") return;
    if (feedGraphs[currentFeedCase.name]) return;
    const name = currentFeedCase.name;
    fetchFeedCaseGraphs(name).then(
      (g) => setFeedGraphs((all) => ({ ...all, [name]: g })),
      (e) => setError(String(e)),
    );
  }, [currentFeedCase, feedGraphs]);

  const baseDoc: GraphDoc | null = inFeed
    ? currentFeedCase?.kind === "canonical"
      ? (docs[currentFeedCase.name] ?? null)
      : (feedRewired?.parent ?? null)
    : currentCase
      ? (docs[caseKey(currentCase)] ?? null)
      : null;

  // ── Drill-down: resolve the doc and trace at the current altitude ──
  const feedOk = feedRun && isFeedRunOk(feedRun) ? feedRun : null;
  const runTrace: GraphTrace | null = inFeed
    ? (feedOk?.trace ?? null)
    : run && !isRejected(run)
      ? run.trace
      : null;

  const walkthroughActive = walkStep !== null && scenario !== null;
  const walkConfig: { trace: GraphTrace; highlights: WalkthroughHighlights } | null =
    walkthroughActive && scenario ? walkthroughCanvasConfig(walkStep, scenario) : null;

  // In walkthrough mode the canvas always shows the customer-support graph.
  const canvasRoot: GraphDoc | null = walkthroughActive
    ? (docs["customer-support"] ?? null)
    : baseDoc;
  const rootTrace = walkthroughActive ? (walkConfig?.trace ?? null) : runTrace;

  // The graph a node names: the rewired child where the selected feed case
  // carries one, otherwise the canonical file of that declared name.
  const childDoc = useCallback(
    (graphName: string): GraphDoc | undefined => {
      if (feedRewired && feedRewired.child.name === graphName) return feedRewired.child;
      const file = nameToFile[graphName];
      return file ? docs[file] : undefined;
    },
    [feedRewired, nameToFile, docs],
  );

  const { canvasDoc, canvasTrace } = useMemo(() => {
    let doc = canvasRoot;
    let trace = rootTrace;
    for (const step of drillPath) {
      const graphName = doc?.nodes.find((n) => n.name === step.node)?.name;
      const child = graphName ? childDoc(graphName) : undefined;
      if (!child) return { canvasDoc: doc, canvasTrace: trace };
      const nodeTrace = trace?.nodes.find((n) => n.node === step.node);
      trace =
        (step.element === null ? nodeTrace?.subgraph : nodeTrace?.elements?.[step.element]) ??
        null;
      doc = child;
    }
    return { canvasDoc: doc, canvasTrace: trace };
  }, [canvasRoot, rootTrace, drillPath, childDoc]);

  // How many element runs each step of the path was opened among — read from
  // the trace one level up, for the breadcrumb's "[2 of 5]".
  const elementCounts = useMemo(() => {
    const counts: (number | null)[] = [];
    let trace = rootTrace;
    for (const step of drillPath) {
      const nodeTrace = trace?.nodes.find((n) => n.node === step.node);
      counts.push(step.element === null ? null : (nodeTrace?.elements?.length ?? null));
      trace =
        (step.element === null ? nodeTrace?.subgraph : nodeTrace?.elements?.[step.element]) ??
        null;
    }
    return counts;
  }, [rootTrace, drillPath]);

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
      if (feedCaseName !== null) {
        setFeedRun(await runFeed({ case: feedCaseName, tier }));
      } else {
        setRun(await runCase({ case: caseName, message, tier }));
      }
    } catch (e) {
      setError(String(e));
      setRun(null);
      setFeedRun(null);
    } finally {
      setRunning(false);
    }
  }, [caseName, feedCaseName, message, tier]);

  const startWalkthrough = useCallback(async () => {
    setRunning(true);
    setError(null);
    setRun(null);
    setFeedRun(null);
    setFeedCaseName(null);
    setHostileOpen(false);
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

  const resetView = () => {
    setRun(null);
    setFeedRun(null);
    setError(null);
    setScenario(null);
    setWalkStep(null);
    setDrillPath([]);
    setSelectedNode(null);
  };

  const selectCase = (name: string) => {
    setCaseName(name);
    setFeedCaseName(null);
    setHostileOpen(false);
    resetView();
  };

  const selectFeedCase = (name: string) => {
    setFeedCaseName(name);
    setHostileOpen(false);
    resetView();
  };

  const openHostile = () => {
    setFeedCaseName(FEED_CANONICAL);
    setHostileOpen(true);
    resetView();
  };

  // One hostile feed through one tick of the canonical graph, on the chosen
  // tier; the trace it returns overlays the graph like any other run.
  const runHostile = useCallback(
    async (name: string) => {
      setHostileRunning(name);
      setError(null);
      setDrillPath([]);
      setSelectedNode(null);
      try {
        setFeedRun(await runFeed({ case: FEED_CANONICAL, tier, hostile: name }));
      } catch (e) {
        setError(String(e));
        setFeedRun(null);
      } finally {
        setHostileRunning(null);
      }
    },
    [tier],
  );

  // Opening a per-item node opens its first element run where the trace has
  // any; otherwise (and for a plain sub-graph node) the nested graph itself.
  const openSubgraph = useCallback(
    (nodeName: string) => {
      const elements = canvasTrace?.nodes.find((n) => n.node === nodeName)?.elements;
      setDrillPath((p) => [...p, { node: nodeName, element: elements?.length ? 0 : null }]);
      setSelectedNode(null);
    },
    [canvasTrace],
  );

  const openElement = useCallback((nodeName: string, index: number) => {
    setDrillPath((p) => [...p, { node: nodeName, element: index }]);
    setSelectedNode(null);
  }, []);

  const stepElement = (depth: number, delta: number) => {
    setDrillPath((p) =>
      p
        .slice(0, depth + 1)
        .map((s, i) =>
          i === depth && s.element !== null ? { ...s, element: s.element + delta } : s,
        ),
    );
    setSelectedNode(null);
  };

  const feedRejection = inFeed && feedRun && isFeedRejected(feedRun) ? feedRun : null;
  const rejection = inFeed ? feedRejection : run && isRejected(run) ? run : null;

  // ── Render ─────────────────────────────────────────────────────────
  const canonicalCases = corpus.filter((c) => c.kind === "canonical");
  const mutationCases = corpus.filter((c) => c.kind === "mutation");
  const latestOk = latest && !("error" in latest) ? latest : null;

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
                  className={`case-btn ${!inFeed && caseName === c.name ? "active" : ""}`}
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
            <h2>Faulty cases (from the evaluation corpus)</h2>
            <div className="case-list">
              {mutationCases.map((c) => (
                <button
                  key={c.name}
                  className={`case-btn ${!inFeed && caseName === c.name ? "active" : ""}`}
                  onClick={() => selectCase(c.name)}
                  data-testid={`case-${c.name}`}
                >
                  <span className="mono">{breakAtUnderscores(c.name)}</span>
                  <span className="verdict badge rejected">rejected</span>
                </button>
              ))}
            </div>
            <p className="note">
              The same cases the evaluation harness pins; running one shows the validator&apos;s
              rejection and its reason class.
            </p>
          </section>

          {/* The customer-support run controls; the feed-triage section below
              carries its own, since a tick takes no message. */}
          <section className="side-section" hidden={inFeed}>
            <h2>Run</h2>
            {!inFeed && (
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
                  <button
                    className="chip-btn"
                    onClick={() => meta && setMessage(meta.benign_message)}
                  >
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
            )}
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
            <button
              className="run-btn"
              onClick={doRun}
              disabled={running || hostileRunning !== null || !baseDoc}
              data-testid="run-btn"
            >
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

          {/* Last in the sidebar, below everything the paper's figures show. */}
          {feedCases && (
            <section className="side-section" data-testid="feed-section">
              <h2>Feed-triage service</h2>
              <div className="case-list">
                {feedCases.corpus.map((c) => (
                  <button
                    key={c.name}
                    className={`case-btn ${feedCaseName === c.name && !hostileOpen ? "active" : ""}`}
                    onClick={() => selectFeedCase(c.name)}
                    data-testid={`feed-case-${c.name}`}
                  >
                    <span className={c.kind === "canonical" ? undefined : "mono"}>
                      {breakAtUnderscores(c.name)}
                    </span>
                    <span className={`verdict badge ${c.expected}`}>{c.expected}</span>
                  </button>
                ))}
              </div>
              <p className="note">
                The service&apos;s graph and the rewirings of it that its evaluation pins; each
                badge is the verdict the API lists as expected.
              </p>
              <div className="field">
                <label>Enforcement tier</label>
                <div className="tier-row">
                  <button
                    className={`chip-btn ${tier === "host" ? "active" : ""}`}
                    onClick={() => setTier("host")}
                    data-testid="feed-tier-host"
                  >
                    host
                  </button>
                  <button
                    className={`chip-btn ${tier === "confined" ? "active" : ""}`}
                    onClick={() => setTier("confined")}
                    disabled={!meta?.confined_tier_available}
                    data-testid="feed-tier-confined"
                  >
                    confined
                  </button>
                </div>
              </div>
              <button
                className="run-btn"
                onClick={doRun}
                disabled={running || hostileRunning !== null || !inFeed || !baseDoc}
                title={inFeed ? undefined : "select a feed-triage case first"}
                data-testid="feed-run-btn"
              >
                {running && inFeed ? "Running…" : "Run one tick"}
              </button>
              <button
                className="walkthrough-btn feed-gap"
                onClick={openHostile}
                disabled={running}
                data-testid="hostile-btn"
              >
                Hostile-feed walkthrough
              </button>
              <p className="note" data-testid="latest-digest">
                {latestOk ? (
                  <>
                    Latest digest: {latestOk.date}{" "}
                    <button
                      className="link-btn"
                      onClick={() => setShowLatest(true)}
                      data-testid="latest-digest-view"
                    >
                      view
                    </button>
                  </>
                ) : latest && "error" in latest ? (
                  <>Latest digest: {latest.error}</>
                ) : (
                  "Latest digest: …"
                )}
              </p>
            </section>
          )}
        </aside>

        <div className="canvas-col">
          {(drillPath.length > 0 || subgraphInView(canvasDoc, subgraphNames)) && canvasRoot && (
            <nav className="breadcrumbs" data-testid="breadcrumbs">
              {drillPath.length === 0 ? (
                <span className="crumb-here">{canvasRoot.name}</span>
              ) : (
                <>
                  <button onClick={() => setDrillPath([])}>{canvasRoot.name}</button>
                  {drillPath.map((step, i) => {
                    const count = elementCounts[i];
                    const label =
                      step.element !== null && count !== null
                        ? `${step.node} [${step.element + 1} of ${count}]`
                        : step.node;
                    return (
                      <span key={`${i}-${step.node}`}>
                        <span className="sep"> ▸ </span>
                        {i === drillPath.length - 1 ? (
                          <span className="crumb-here">{label}</span>
                        ) : (
                          <button onClick={() => setDrillPath(drillPath.slice(0, i + 1))}>
                            {label}
                          </button>
                        )}
                        {step.element !== null && count !== null && (
                          <span className="element-nav">
                            <button
                              onClick={() => stepElement(i, -1)}
                              disabled={step.element === 0}
                              data-testid="element-prev"
                              title="previous element run"
                            >
                              ‹
                            </button>
                            <button
                              onClick={() => stepElement(i, 1)}
                              disabled={step.element >= count - 1}
                              data-testid="element-next"
                              title="next element run"
                            >
                              ›
                            </button>
                          </span>
                        )}
                      </span>
                    );
                  })}
                </>
              )}
            </nav>
          )}

          {canvasDoc ? (
            <GraphCanvas
              key={`${canvasDoc.name}-${feedCaseName ?? caseName}-${drillPath
                .map((s) => `${s.node}:${s.element ?? ""}`)
                .join("/")}-${walkthroughActive ? walkStep : "n"}`}
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
                {feedRejection ? "✗ Rejected" : "✗ Rejected at assembly time"}
                {rejection.reason_class && (
                  <span className="badge rejected" data-testid="reason-class">
                    caught by: {rejection.reason_class}
                  </span>
                )}
              </div>
              {feedRejection && (
                <p className="layer" data-testid="rejection-layer">
                  {feedRejection.validator_accepts ? (
                    <>
                      <b>The validator accepts this graph.</b>{" "}It is rejected only by the
                      service&apos;s own shape check (<code>poc/feed_policy.py</code>).
                    </>
                  ) : (
                    <>Rejected by the validator.</>
                  )}
                </p>
              )}
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

          {showLatest && latestOk && (
            <div className="digest-overlay" data-testid="latest-digest-overlay">
              <div className="head">
                <b>Latest digest: {latestOk.date}</b>
                <span className="note">as the live service wrote it; shown in a sandboxed frame</span>
                <span className="spacer" />
                <button className="chip-btn" onClick={() => setShowLatest(false)}>
                  close
                </button>
              </div>
              {/* Derived from third-party feed text: never injected into this page. */}
              <iframe
                title={`digest ${latestOk.date}`}
                sandbox=""
                srcDoc={latestOk.html}
                data-testid="latest-digest-frame"
              />
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
        ) : hostileOpen && feedCases && !selectedNode && drillPath.length === 0 ? (
          <HostilePanel
            cases={feedCases.hostile}
            run={feedOk?.hostile ? feedOk : null}
            running={hostileRunning}
            onRun={runHostile}
            onExit={() => {
              setHostileOpen(false);
              setFeedRun(null);
            }}
          />
        ) : (
          canvasDoc && (
            <DetailPanel
              doc={canvasDoc}
              corpusCase={currentCase}
              selectedNode={selectedNode}
              nodeTrace={selectedTrace}
              run={
                inFeed
                  ? drillPath.length === 0
                    ? feedOk
                    : null // the tick's terminal is the parent's, not an element run's
                  : run && !isRejected(run)
                    ? run
                    : null
              }
              onOpenElement={openElement}
            >
              {currentFeedCase && drillPath.length === 0 && (
                <FeedCaseInfo
                  feedCase={currentFeedCase}
                  run={feedOk}
                  acceptedOnly={Boolean(feedRun && isFeedAcceptedOnly(feedRun))}
                />
              )}
            </DetailPanel>
          )
        )}
      </div>
    </main>
  );
}

/** A long snake_case name, with break opportunities after each underscore, so it
 *  wraps at a word boundary instead of mid-word. The text content is unchanged. */
function breakAtUnderscores(name: string) {
  return name.split("_").map((part, i, parts) => (
    <span key={i}>
      {part}
      {i < parts.length - 1 ? (
        <>
          _<wbr />
        </>
      ) : null}
    </span>
  ));
}

function caseKey(c: CorpusCase): string {
  return c.kind === "canonical" ? c.name : `mutation:${c.name}`;
}

function subgraphInView(doc: GraphDoc | null, subgraphNames: Set<string>): boolean {
  return Boolean(doc?.nodes.some((n) => subgraphNames.has(n.name)));
}
