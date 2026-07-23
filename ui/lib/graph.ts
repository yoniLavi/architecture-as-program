// Turning a canonical graph JSON into a renderable view: positions scaled from
// the graph's own layout block, edges parsed the same way the runtime parses
// them (a "From.port" source names the variant role), and — after a run — the
// trace overlaid. Layout is presentation computed *from* the JSON; no structural
// fact originates here.

import type { GraphDoc, GraphTrace, NodeTrace, Trust } from "./types";

export const GRID_X = 240;
export const GRID_Y = 168;
export const NODE_W = 190;
export const NODE_H = 74;

export interface ParsedEdge {
  id: string;
  source: string;
  port: string | null;
  target: string;
}

export function parseEdges(doc: GraphDoc): ParsedEdge[] {
  return doc.data_edges.map((e) => {
    const dot = e.from.lastIndexOf(".");
    const source = dot === -1 ? e.from : e.from.slice(0, dot);
    const port = dot === -1 ? null : e.from.slice(dot + 1);
    return { id: `${e.from}->${e.to}`, source, port, target: e.to };
  });
}

// Positions come from the canonical layout block (grid units, y down). A graph
// without one gets a simple layered fallback: depth along y, siblings along x.
export function positionsOf(doc: GraphDoc): Record<string, { x: number; y: number }> {
  const declared = doc.layout?.positions;
  if (declared) {
    return Object.fromEntries(
      Object.entries(declared).map(([n, [x, y]]) => [n, { x: x * GRID_X, y: y * GRID_Y }]),
    );
  }
  const edges = parseEdges(doc);
  const depth: Record<string, number> = {};
  const nodes = doc.nodes.map((n) => n.name);
  for (const n of nodes) depth[n] = 0;
  for (let i = 0; i < nodes.length; i++) {
    for (const e of edges) {
      depth[e.target] = Math.max(depth[e.target], depth[e.source] + 1);
    }
  }
  const perRow: Record<number, number> = {};
  const out: Record<string, { x: number; y: number }> = {};
  for (const n of nodes) {
    const row = depth[n];
    out[n] = { x: (perRow[row] ?? 0) * GRID_X, y: row * GRID_Y };
    perRow[row] = (perRow[row] ?? 0) + 1;
  }
  return out;
}

// The data input of a node is its one input that is not a declared capability;
// everything else is its `with` clause.
export function splitInputs(doc: GraphDoc, inputs: string[]) {
  const caps = new Set(doc.capabilities);
  return {
    data: inputs.filter((i) => !caps.has(i)),
    withClause: inputs.filter((i) => caps.has(i)),
  };
}

// ── Trace overlay ────────────────────────────────────────────────────

export interface EdgeOverlay {
  taken: boolean;
  trust: Trust | null; // the label of the value that flowed, from the trace
}

export interface TraceOverlay {
  byNode: Map<string, NodeTrace>;
  edges: Map<string, EdgeOverlay>;
  dischargedAt: string | null; // the node that raised untrusted → trusted
}

// Overlay a returned trace on the graph view. Edge facts are derived from the
// trace's own node records: an edge was taken iff both endpoints ran (each node
// runs at most once here, and variant branches are exclusive — only the taken
// port's target appears in the trace); the trust flowing on it is the label the
// destination's input carried.
export function overlayTrace(doc: GraphDoc, trace: GraphTrace): TraceOverlay {
  const byNode = new Map(trace.nodes.map((n) => [n.node, n]));
  const edges = new Map<string, EdgeOverlay>();
  for (const e of parseEdges(doc)) {
    const src = byNode.get(e.source);
    const dst = byNode.get(e.target);
    const taken = Boolean(src && dst);
    edges.set(e.id, { taken, trust: taken && dst ? dst.input_trust : null });
  }
  const discharged = trace.nodes.find(
    (n) => n.input_trust === "untrusted" && n.output_trust === "trusted",
  );
  return { byNode, edges, dischargedAt: discharged?.node ?? null };
}

// Every trust-raising node in a whole (possibly nested) trace — mirrors the
// harness's `_trust_raisers` pin, so the walkthrough can show it as data.
export function trustRaisers(trace: GraphTrace): string[] {
  const out: string[] = [];
  for (const n of trace.nodes) {
    if (n.input_trust === "untrusted" && n.output_trust === "trusted") out.push(n.node);
    if (n.subgraph) out.push(...trustRaisers(n.subgraph));
  }
  return out;
}

// Node names mentioned in validator error strings — how the rejection display
// knows where to point. Honest best-effort text matching, nothing more.
export function nodesInErrors(doc: GraphDoc, errors: string[]): Set<string> {
  const blob = errors.join(" ");
  return new Set(doc.nodes.map((n) => n.name).filter((name) => blob.includes(name)));
}
