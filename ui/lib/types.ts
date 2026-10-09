// Types mirroring the two upstream sources of truth this UI consumes:
// the canonical graph JSON (graphs/schema.json) and the execution trace
// (poc/trace-schema.json), plus the inspector API's envelope shapes.
// The UI adds no fields of its own to either — if a fact is missing here,
// the fix is upstream, never a UI-side annotation.

export interface GraphNode {
  name: string;
  inputs: string[];
  output: string;
  discharges_trust?: boolean;
  capability_identities?: Record<string, string>;
  // A per-item map: a sub-graph node applied to each element of a list, one
  // isolated child run per element.
  each?: boolean;
}

export interface GraphEdge {
  from: string;
  to: string;
  // The position, among the target's data inputs, that this edge feeds. A node
  // with several data inputs is a join.
  to_input?: number;
}

export interface GraphZone {
  label: string;
  color: string;
  background: string;
  nodes: string[];
}

export interface GraphLayout {
  zones?: Record<string, GraphZone>;
  positions?: Record<string, [number, number]>;
  edge_colors?: Record<string, string>;
  untrusted_label_color?: string;
}

export interface GraphDoc {
  name: string;
  parameters: string[];
  capabilities: string[];
  nodes: GraphNode[];
  data_edges: GraphEdge[];
  layout?: GraphLayout;
}

// ── Trace (poc/trace-schema.json) ────────────────────────────────────

export type Tier = "host" | "sandbox" | "graph";
export type Trust = "trusted" | "untrusted";

export interface Crossing {
  interface: string;
  instance: string;
}

export interface NodeTrace {
  node: string;
  tier: Tier;
  input_trust: Trust;
  output_trust: Trust | null;
  crossings: Crossing[];
  subgraph?: GraphTrace;
  // Present only on a per-item node: one nested run per list element, in order.
  elements?: GraphTrace[];
}

export interface GraphTrace {
  graph: string;
  nodes: NodeTrace[];
}

// ── API envelopes (poc/inspector_api.py) ─────────────────────────────

export interface GraphIndexEntry {
  name: string;
  file: string;
}

export interface CorpusCase {
  name: string;
  kind: "canonical" | "mutation";
  expected: "accepted" | "rejected";
  reason: string | null;
  note: string;
  base: string;
}

export interface ValueSummary {
  type: string;
  repr: string;
}

export interface RunOk {
  case: string;
  graph: string;
  tier: "host" | "confined";
  input: ValueSummary;
  trace: GraphTrace;
  terminals: Record<string, ValueSummary>;
}

export interface RunRejected {
  rejected: true;
  case: string;
  reason_class: string | null;
  errors: string[];
}

export type RunResponse = RunOk | RunRejected;

export interface InjectionSide {
  path: string[];
  tiers: Record<string, string>;
  received_type: string;
  is_untrusted: boolean;
  adversarial_text_present: boolean;
  out_of_scope_call_refused: boolean;
  trace: GraphTrace;
}

export interface InjectionScenario {
  adversarial_message: string;
  discharge_node: string;
  host: InjectionSide;
  confined: InjectionSide | null;
}

export interface Meta {
  confined_tier_available: boolean;
  sandboxed_nodes: string[];
  benign_message: string;
  adversarial_message: string;
}

export function isRejected(r: RunResponse): r is RunRejected {
  return (r as RunRejected).rejected === true;
}

// ── The feed-triage service (`/api/feed/…`) ──────────────────────────

export interface FeedCorpusCase {
  name: string;
  kind: "canonical" | "mutation" | "safe-variant";
  expected: "accepted" | "rejected";
  reason: string | null;
  note: string;
  // True when the general validator accepts the graph — a rejection is then the
  // service's own shape check (poc/feed_policy.py) and nothing else.
  validator_accepts: boolean;
}

export interface HostileCase {
  name: string;
  verdict: "impossible" | "bounded" | "residual";
  attack: string;
  outcome: string;
}

export interface FeedCases {
  corpus: FeedCorpusCase[];
  hostile: HostileCase[];
}

export interface FeedCaseGraphs {
  case: string;
  parent: GraphDoc;
  child: GraphDoc;
}

export interface FeedDigest {
  markdown: string;
  html: string;
}

// The facts the build pins for a hostile run, as returned. Rendered by key; the
// UI names no fact the payload does not carry.
export type FeedFactValue = string | number | boolean | string[] | null;
export type FeedFacts = Record<string, FeedFactValue>;

export interface FeedRunOk {
  case: string;
  graph: string;
  tier: "host" | "confined";
  hostile: string | null;
  verdict: string | null;
  facts: FeedFacts | null;
  trace: GraphTrace | null;
  terminals: Record<string, ValueSummary>;
  digest: FeedDigest;
}

export interface FeedRunRejected extends RunRejected {
  validator_accepts: boolean;
}

export interface FeedRunAccepted {
  case: string;
  accepted: true;
  ran: false;
}

export type FeedRunResponse = FeedRunOk | FeedRunRejected | FeedRunAccepted;

export interface LatestDigest {
  date: string;
  markdown: string;
  html: string;
}

export function isFeedRejected(r: FeedRunResponse): r is FeedRunRejected {
  return (r as FeedRunRejected).rejected === true;
}

export function isFeedAcceptedOnly(r: FeedRunResponse): r is FeedRunAccepted {
  return (r as FeedRunAccepted).ran === false;
}

export function isFeedRunOk(r: FeedRunResponse): r is FeedRunOk {
  return !isFeedRejected(r) && !isFeedAcceptedOnly(r);
}
