"use client";

import type { Node, NodeProps } from "@xyflow/react";

// The floating label of a trust zone, from the canonical layout's `zones` block.

export type ZoneLabelData = { label: string; color: string };
export type ZoneLabelType = Node<ZoneLabelData, "zoneLabel">;

export default function ZoneLabel({ data }: NodeProps<ZoneLabelType>) {
  return (
    <div
      style={{
        color: data.color,
        fontSize: 10.5,
        fontWeight: 700,
        letterSpacing: "0.08em",
        pointerEvents: "none",
      }}
    >
      {data.label}
    </div>
  );
}
