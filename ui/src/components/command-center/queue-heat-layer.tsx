"use client";

import { TERMINAL_ZONES } from "@/lib/command-center/map-config";
import type { QueueHotspot } from "@/lib/command-center/selectors";
import { cn } from "@/lib/utils";

interface QueueHeatLayerProps {
  hotspots: QueueHotspot[];
  scale: number;
  dim?: boolean;
  className?: string;
}

const levelToOpacity = {
  high: 0.4,
  medium: 0.2,
  low: 0.06,
};

const levelToFill: Record<string, string> = {
  high: "rgb(239, 68, 68)",
  medium: "rgb(245, 158, 11)",
  low: "rgb(59, 130, 246)",
};

export function QueueHeatLayer({ hotspots, scale, dim, className }: QueueHeatLayerProps) {
  return (
    <g className={cn("queue-heat-layer", dim && "opacity-60", "transition-opacity duration-200", className)}>
      {TERMINAL_ZONES.map((zone) => {
        const hotspot = hotspots.find(
          (h) => zone.id === h.zone || zone.label === h.zone || h.zone?.includes(zone.id)
        );
        const level = hotspot?.level ?? "low";
        const opacity = levelToOpacity[level];
        const fill = levelToFill[level];
        const points = zone.polygon.map((p) => `${p.x},${p.y}`).join(" ");

        return (
          <polygon
            key={zone.id}
            points={points}
            fill={fill}
            opacity={opacity}
            className={cn("transition-opacity duration-500", level !== "low" && "map-heat-shimmer")}
          />
        );
      })}
    </g>
  );
}
