"use client";

import { useMemo } from "react";
import {
  Background,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
  type NodeTypes,
} from "@xyflow/react";
import type { GraphDoc, GraphTrace } from "@/lib/types";
import {
  NODE_H,
  NODE_W,
  nodesInErrors,
  overlayTrace,
  parseEdges,
  positionsOf,
  splitInputs,
} from "@/lib/graph";
import SignalNode, { type SignalNodeData } from "./SignalNode";
import ZoneLabel from "./ZoneLabel";

// The graph view: canonical JSON in, React Flow nodes/edges out. Structure and
// positions come from the served file; the trace overlay and the rejection
// highlights are the only run-dependent additions.

const nodeTypes: NodeTypes = {
  signal: SignalNode as NodeTypes[string],
  zoneLabel: ZoneLabel as NodeTypes[string],
};

// Presentation mapping for the canonical layout colors: the JSON's semantic
// role colors keep their meaning, re-toned to the CVD-validated accents
// (the canonical red/green pair is indistinguishable under deuteranopia).
const ACCENTS: Record<string, string> = {
  "#b33": "var(--untrusted)",
  "#272": "var(--trusted)",
  "#c80": "var(--warn)",
  "#46c": "var(--info)",
};
const accent = (c: string | undefined, fallback: string) =>
  c ? (ACCENTS[c] ?? c) : fallback;

export interface WalkthroughHighlights {
  emphasize?: string[]; // node names to ring
  taintOnly?: boolean; // dim everything not on the untrusted path or its border
  contrastTiers?: Record<string, { host: string; confined: string }>;
}

interface Props {
  doc: GraphDoc;
  trace: GraphTrace | null; // the trace at *this* graph's altitude
  subgraphNames: Set<string>;
  rejectionErrors: string[] | null;
  selectedNode: string | null;
  onSelect: (name: string | null) => void;
  onOpenSubgraph: (name: string) => void;
  highlights?: WalkthroughHighlights;
}

export default function GraphCanvas({
  doc,
  trace,
  subgraphNames,
  rejectionErrors,
  selectedNode,
  onSelect,
  onOpenSubgraph,
  highlights,
}: Props) {
  const { nodes, edges } = useMemo(() => {
    const positions = positionsOf(doc);
    const overlay = trace ? overlayTrace(doc, trace) : null;
    const rejectedNodes = rejectionErrors ? nodesInErrors(doc, rejectionErrors) : new Set<string>();

    const nodes: Node[] = [];

    // Zones from the canonical layout: a dashed container behind its members,
    // labelled with the zone's own label and colors.
    for (const [key, zone] of Object.entries(doc.layout?.zones ?? {})) {
      const members = zone.nodes.filter((n) => positions[n]);
      if (!members.length) continue;
      const xs = members.map((n) => positions[n].x);
      const ys = members.map((n) => positions[n].y);
      const pad = 26;
      const x = Math.min(...xs) - pad;
      const y = Math.min(...ys) - pad - 6;
      nodes.push({
        id: `zone-${key}`,
        type: "group",
        position: { x, y },
        data: {},
        draggable: false,
        selectable: false,
        style: {
          width: Math.max(...xs) + NODE_W + pad - x,
          height: Math.max(...ys) + NODE_H + pad - y,
          background: zone.background,
          border: `1.5px dashed ${accent(zone.color, zone.color)}`,
          borderRadius: 12,
          pointerEvents: "none" as const,
        },
        zIndex: -10,
      });
      nodes.push({
        id: `zone-label-${key}`,
        type: "zoneLabel",
        position: { x: x + 12, y: y + 6 },
        data: { label: zone.label, color: accent(zone.color, zone.color) },
        draggable: false,
        selectable: false,
        zIndex: -9,
      });
    }

    for (const gn of doc.nodes) {
      const { data: dataIn, withClause } = splitInputs(doc, gn.inputs);
      const nodeTrace = overlay?.byNode.get(gn.name) ?? null;
      const tainted = nodeTrace?.input_trust === "untrusted";
      const emphasize = highlights?.emphasize?.includes(gn.name) ?? false;
      const dimmed =
        (overlay !== null && nodeTrace === null) ||
        (highlights?.taintOnly === true &&
          !tainted &&
          nodeTrace?.output_trust !== "untrusted" &&
          overlay?.dischargedAt !== gn.name);
      const data: SignalNodeData = {
        node: gn,
        dataIn,
        withClause,
        identities: gn.capability_identities ?? {},
        isSubgraph: subgraphNames.has(gn.name),
        trace: nodeTrace,
        contrastTiers: highlights?.contrastTiers?.[gn.name] ?? null,
        tainted,
        discharge: overlay?.dischargedAt === gn.name,
        rejectedAt: rejectedNodes.has(gn.name),
        dimmed,
        emphasized: emphasize,
        onOpenSubgraph,
      };
      nodes.push({
        id: gn.name,
        type: "signal",
        position: positions[gn.name] ?? { x: 0, y: 0 },
        data: data as unknown as Record<string, unknown>,
        selected: selectedNode === gn.name,
      });
    }

    const edgeColors = doc.layout?.edge_colors ?? {};
    const edges: Edge[] = parseEdges(doc).map((e) => {
      const ov = trace ? (overlayTrace(doc, trace).edges.get(e.id) ?? null) : null;
      const untrusted = ov?.trust === "untrusted";
      const taken = ov?.taken ?? false;
      const base = accent(e.port ? edgeColors[e.port] : undefined, "var(--line-2)");
      const color = untrusted ? "var(--untrusted)" : taken ? "var(--trusted)" : base;
      const label = untrusted
        ? `⚠ Untrusted${e.port ? ` · ${e.port}` : ""}`
        : (e.port ?? undefined);
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label,
        animated: taken,
        style: {
          stroke: color,
          strokeWidth: taken ? 2.2 : 1.4,
          strokeDasharray: untrusted ? "7 4" : undefined,
          opacity: trace && !taken ? 0.35 : 1,
        },
        labelStyle: { fill: untrusted ? "var(--untrusted)" : "var(--ink-2)" },
        markerEnd: { type: MarkerType.ArrowClosed, color },
        zIndex: taken ? 1 : 0,
      };
    });

    return { nodes, edges };
  }, [doc, trace, subgraphNames, rejectionErrors, selectedNode, highlights, onOpenSubgraph]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.15, maxZoom: 1.05 }}
      minZoom={0.3}
      maxZoom={1.6}
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, node) => {
        if (node.type === "signal") onSelect(node.id);
      }}
      onPaneClick={() => onSelect(null)}
      nodesDraggable={false}
      nodesConnectable={false}
      edgesFocusable={false}
    >
      <Background gap={22} size={1.2} color="var(--line)" />
    </ReactFlow>
  );
}
