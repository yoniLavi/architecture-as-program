"use client";

import type { CorpusCase, GraphDoc, NodeTrace, RunOk } from "@/lib/types";
import { splitInputs } from "@/lib/graph";

// The right-hand panel: everything shown here is parsed from the canonical
// JSON (signature, `with` clause, identities) or read from the returned trace
// (tier, trust, crossings) — nothing is annotated UI-side.

interface Props {
  doc: GraphDoc;
  corpusCase: CorpusCase | null;
  selectedNode: string | null;
  nodeTrace: NodeTrace | null;
  run: RunOk | null;
}

export default function DetailPanel({ doc, corpusCase, selectedNode, nodeTrace, run }: Props) {
  const gn = doc.nodes.find((n) => n.name === selectedNode) ?? null;

  if (!gn) {
    return (
      <div className="detail" data-testid="detail-panel">
        <h2>{doc.name}</h2>
        {corpusCase && corpusCase.kind === "mutation" && (
          <p className="note">
            Unsafe mutation <code>{corpusCase.name}</code>: {corpusCase.note}
          </p>
        )}
        <h3>Boundary parameters</h3>
        <ul className="plain">
          {doc.parameters.map((p) => (
            <li key={p}>
              <span className="cap-chip" title={p}>
                {p}
              </span>
            </li>
          ))}
        </ul>
        <h3>Declared capabilities</h3>
        <ul className="plain">
          {doc.capabilities.map((c) => (
            <li key={c}>
              <span className="cap-chip" title={c}>
                {c}
              </span>
            </li>
          ))}
        </ul>
        {run && (
          <>
            <h3>Terminals reached</h3>
            {Object.entries(run.terminals).map(([node, v]) => (
              <div key={node} className="terminal-box" data-testid="terminal">
                <div className="t-node">{node}</div>
                <div className="t-val">
                  {v.type}: {v.repr}
                </div>
              </div>
            ))}
          </>
        )}
        <h3>Reading the view</h3>
        <p className="note">
          Select a node for its signature, capabilities, and — after a run — its recorded tier,
          trust labels, and capability crossings. ⊼ marks the declared trust discharger. Red edges
          labelled ⚠ carry <code>Untrusted</code> values; animated edges are the path this run
          took.
        </p>
      </div>
    );
  }

  const { data: dataIn, withClause } = splitInputs(doc, gn.inputs);
  const identities = gn.capability_identities ?? {};

  return (
    <div className="detail" data-testid="detail-panel">
      <h2>{gn.name}</h2>
      {gn.discharges_trust && (
        <span className="badge trust-trusted">⊼ discharges trust</span>
      )}

      <h3>Signature</h3>
      <dl className="kv">
        <dt>consumes</dt>
        <dd>{dataIn.join(", ") || "(graph boundary input)"}</dd>
        <dt>emits</dt>
        <dd>{gn.output}</dd>
      </dl>

      <h3>Capabilities (with clause)</h3>
      {withClause.length === 0 ? (
        <p className="empty">None — this node holds no external authority.</p>
      ) : (
        <ul className="plain">
          {withClause.map((c) => (
            <li key={c}>
              <span className="cap-chip" title={c}>
                {c}
              </span>
              {identities[c] && (
                <span className="badge neutral" title="declared capability identity">
                  @{identities[c]}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {nodeTrace && (
        <>
          <h3>This run</h3>
          <dl className="kv">
            <dt>enforcement tier</dt>
            <dd>
              <span className={`badge tier-${nodeTrace.tier}`}>{nodeTrace.tier}</span>
            </dd>
            <dt>input trust</dt>
            <dd>
              <span className={`badge trust-${nodeTrace.input_trust}`}>{nodeTrace.input_trust}</span>
            </dd>
            <dt>output trust</dt>
            <dd>
              {nodeTrace.output_trust ? (
                <span className={`badge trust-${nodeTrace.output_trust}`}>{nodeTrace.output_trust}</span>
              ) : (
                "—"
              )}
            </dd>
          </dl>

          <h3>Capability crossings</h3>
          {nodeTrace.crossings.length === 0 ? (
            <p className="empty">No capability boundary was crossed by this node.</p>
          ) : (
            <ul className="plain">
              {nodeTrace.crossings.map((c) => (
                <li key={`${c.interface}:${c.instance}`} className="crossing" data-testid="crossing">
                  <span className="iface">{c.interface}</span>
                  <span className="inst">@ {c.instance}</span>
                </li>
              ))}
            </ul>
          )}
          {nodeTrace.subgraph && (
            <p className="note">
              This node ran as a nested sub-graph ({nodeTrace.subgraph.nodes.length} inner nodes) —
              open it to see the nested trace.
            </p>
          )}
        </>
      )}
    </div>
  );
}
