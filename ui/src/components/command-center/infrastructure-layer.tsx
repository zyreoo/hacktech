"use client";

import { TERMINAL_ZONES, getTerminalZone } from "@/lib/command-center/map-config";
import type { InfrastructureAsset } from "@/types/api";
import { cn } from "@/lib/utils";

interface InfrastructureLayerProps {
  assets: InfrastructureAsset[];
  scale: number;
  selectedEntity?: { type: string; id: string } | null;
  dim?: boolean;
  className?: string;
}

const statusToClass: Record<string, string> = {
  operational: "fill-emerald-500/30 stroke-emerald-400/70",
  degraded: "fill-amber-500/30 stroke-amber-400/70",
  offline: "fill-red-500/30 stroke-red-400/70",
  default: "fill-slate-500/20 stroke-slate-400/50",
};

/** Simple icon by asset_type: camera (video), sensor, network. */
function AssetIcon({ assetType, tamper }: { assetType: string; tamper: boolean }) {
  const t = (assetType ?? "").toLowerCase();
  const size = 8;
  if (t.includes("camera") || t.includes("video")) {
    return (
      <g>
        <rect x={-size} y={-size * 0.6} width={size * 2} height={size * 1.2} rx={2} fill="currentColor" fillOpacity="0.25" stroke="currentColor" strokeWidth={1.5} />
        <circle cx={0} cy={0} r={2.5} fill="currentColor" fillOpacity="0.8" />
      </g>
    );
  }
  if (t.includes("sensor")) {
    return (
      <g>
        <circle r={size} fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth={1.5} />
        <path d="M0,-4 Q4,0 0,4 Q-4,0 0,-4" fill="none" stroke="currentColor" strokeWidth={1} strokeOpacity={0.9} />
      </g>
    );
  }
  if (t.includes("network")) {
    return (
      <g>
        <circle cx={0} cy={-3} r={2.5} fill="currentColor" fillOpacity="0.3" stroke="currentColor" strokeWidth={1} />
        <circle cx={-3} cy={3} r={2.5} fill="currentColor" fillOpacity="0.3" stroke="currentColor" strokeWidth={1} />
        <circle cx={3} cy={3} r={2.5} fill="currentColor" fillOpacity="0.3" stroke="currentColor" strokeWidth={1} />
        <line x1={0} y1={-1} x2={-2} y2={2} stroke="currentColor" strokeWidth={1} opacity={0.6} />
        <line x1={0} y1={-1} x2={2} y2={2} stroke="currentColor" strokeWidth={1} opacity={0.6} />
      </g>
    );
  }
  return <circle r={size} fill="currentColor" fillOpacity="0.2" stroke="currentColor" strokeWidth={2} />;
}

export function InfrastructureLayer({
  assets,
  scale,
  selectedEntity,
  dim,
  className,
}: InfrastructureLayerProps) {
  return (
    <g
      className={cn(
        "infrastructure-layer",
        dim && "opacity-50",
        "transition-opacity duration-200",
        className
      )}
    >
      {assets.map((asset) => {
        const zone = getTerminalZone(asset.location) ?? TERMINAL_ZONES[0];
        const { x, y } = zone.center;
        const status = asset.status ?? "operational";
        const colorClass = statusToClass[status] ?? statusToClass.default;
        const tamper = asset.tamper_detected;
        const selected =
          selectedEntity?.type === "infrastructure" && String(asset.id) === selectedEntity.id;

        return (
          <g
            key={asset.id}
            transform={`translate(${x},${y})`}
            className={cn("cursor-pointer", colorClass)}
          >
            {tamper && (
              <circle
                r={18}
                className="fill-red-500/15 stroke-red-500/60 stroke-[2] map-pulse-critical"
              />
            )}
            <AssetIcon assetType={asset.asset_type ?? ""} tamper={tamper} />
            {selected && (
              <circle
                r={16}
                className="fill-none stroke-primary stroke-[2]"
                filter="url(#mapGlow)"
              />
            )}
          </g>
        );
      })}
    </g>
  );
}
