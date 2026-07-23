"use client";

import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import type { GraphNode, NodeTrace } from "@/lib/types";

// One graph node, rendered from the canonical JSON: name, signature, `with`
// clause, declared identities, discharge marker. After a run, the trace adds a
// tier badge and trust labels; every color here is doubled by text.

export type SignalNodeData = {
  node: GraphNode;
  dataIn: string[];
  withClause: string[];
  identities: Record<string, string>;
  isSubgraph: boolean;
  trace: NodeTrace | null;
  contrastTiers: { host: string; confined: string } | null;
  tainted: boolean;
  discharge: boolean;
  rejectedAt: boolean;
  dimmed: boolean;
  emphasized: boolean;
  onOpenSubgraph?: (name: string) => void;
};

export type SignalNodeType = Node<SignalNodeData, "signal">;

function shortType(t: string): string {
  return t.length > 34 ? t.slice(0, 33) + "…" : t;
}

export default function SignalNode({ data, selected }: NodeProps<SignalNodeType>) {
  const { node, dataIn, withClause, trace, isSubgraph } = data;
  const cls = [
    "signal-node",
    selected ? "selected" : "",
    data.dimmed ? "dimmed" : "",
    data.tainted ? "tainted" : "",
    data.discharge ? "discharge-point" : "",
    data.rejectedAt ? "rejected-at" : "",
    isSubgraph ? "subgraph-node" : "",
    data.emphasized ? "emphasized" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={cls} data-testid={`node-${node.name}`}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="head">
        <span className="name">{node.name}</span>
        {node.discharges_trust && (
          <span className="discharge-mark" title="discharges_trust: the sole node licensed to raise trust">
            ⊼
          </span>
        )}
      </div>
      <div className="sig" title={`${dataIn.join(", ") || "(boundary)"} → ${node.output}`}>
        {shortType(dataIn[0] ?? "·")} → {shortType(node.output)}
      </div>
      {withClause.length > 0 && (
        <div className="caps">
          {withClause.map((c) => (
            <span key={c} className="cap-chip" title={data.identities[c] ? `${c} as ${data.identities[c]}` : c}>
              {data.identities[c] ? `${shortType(c)} @${data.identities[c]}` : shortType(c)}
            </span>
          ))}
        </div>
      )}
      {(trace || data.contrastTiers) && (
        <div className="badges">
          {data.contrastTiers ? (
            <>
              <span className={`badge tier-${data.contrastTiers.host}`}>host run: {data.contrastTiers.host}</span>
              <span className={`badge tier-${data.contrastTiers.confined}`}>
                confined run: {data.contrastTiers.confined}
              </span>
            </>
          ) : (
            trace && (
              <>
                <span className={`badge tier-${trace.tier}`}>{trace.tier}</span>
                <span className={`badge trust-${trace.input_trust}`}>in: {trace.input_trust}</span>
                {trace.output_trust && (
                  <span className={`badge trust-${trace.output_trust}`}>out: {trace.output_trust}</span>
                )}
                {trace.crossings.length > 0 && (
                  <span className="badge neutral">⇄ {trace.crossings.length}</span>
                )}
              </>
            )
          )}
        </div>
      )}
      {isSubgraph && data.onOpenSubgraph && (
        <button
          className="open-sub"
          data-testid={`open-${node.name}`}
          onClick={(e) => {
            e.stopPropagation();
            data.onOpenSubgraph?.(node.name);
          }}
        >
          open sub-graph ▸
        </button>
      )}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}
