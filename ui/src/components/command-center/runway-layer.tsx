"use client";

import { RUNWAY_POSITIONS } from "@/lib/command-center/map-config";
import type { Runway } from "@/types/api";
import { cn } from "@/lib/utils";

interface RunwayLayerProps {
  runways: Runway[];
  scale: number;
  selectedEntity?: { type: string; id: string } | null;
  dim?: boolean;
  /** Runway ids that are part of operational impact chain */
  impactedRunwayIds?: Set<number>;
  className?: string;
}

const statusToStroke: Record<string, string> = {
  active: "stroke-emerald-500/70",
  closed: "stroke-red-500/70",
  maintenance: "stroke-amber-500/70",
  default: "stroke-slate-500/50",
};

const RUNWAY_WIDTH = 14; // stroke width in viewBox units

export function RunwayLayer({
  runways,
  scale,
  selectedEntity,
  dim,
  impactedRunwayIds,
  className,
}: RunwayLayerProps) {
  const impactedSet = impactedRunwayIds ?? new Set<number>();
  return (
    <g className={cn("runway-layer", dim && "opacity-50", "transition-opacity duration-200", className)}>
      {RUNWAY_POSITIONS.map((pos) => {
        const runway = runways.find(
          (r) => r.runway_code === pos.runwayCode || String(r.id) === pos.runwayCode
        );
        const status = runway?.status ?? "active";
        const strokeClass = statusToStroke[status] ?? statusToStroke.default;
        const selected =
          selectedEntity?.type === "runway" && runway && String(runway.id) === selectedEntity.id;
        const impacted = runway && impactedSet.has(runway.id);

        return (
          <g key={pos.runwayCode}>
            {/* Impact highlight (dashed overlay) */}
            {impacted && (
              <line
                x1={pos.start.x}
                y1={pos.start.y}
                x2={pos.end.x}
                y2={pos.end.y}
                strokeWidth={RUNWAY_WIDTH + 4}
                strokeDasharray="8 6"
                className="fill-none stroke-amber-400/50"
                strokeLinecap="round"
              />
            )}
            {/* Runway strip: thick line with rounded visual */}
            <line
              x1={pos.start.x}
              y1={pos.start.y}
              x2={pos.end.x}
              y2={pos.end.y}
              strokeWidth={RUNWAY_WIDTH}
              className={cn("transition-colors", strokeClass)}
              strokeLinecap="round"
            />
            {/* Centerline hint */}
            <line
              x1={pos.start.x}
              y1={pos.start.y}
              x2={pos.end.x}
              y2={pos.end.y}
              strokeWidth={2}
              strokeDasharray="8 6"
              className="stroke-slate-400/30"
              strokeLinecap="round"
            />
            {/* Minimal label at one end (spatial, not a card) */}
            <text
              x={pos.end.x}
              y={pos.end.y - 4}
              textAnchor="middle"
              className="fill-slate-500 text-[9px] font-medium"
            >
              {pos.runwayCode}
            </text>
          </g>
        );
      })}
    </g>
  );
}
