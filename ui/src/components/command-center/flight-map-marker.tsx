"use client";

import { cn } from "@/lib/utils";
import type { Flight } from "@/types/api";
import { hasReconciliationMismatch } from "@/lib/command-center/selectors";

interface FlightMapMarkerProps {
  flight: Flight;
  x: number;
  y: number;
  selected?: boolean;
  dim?: boolean;
  /** Part of operational impact chain (show impact ring) */
  impacted?: boolean;
  showPrediction?: boolean;
  showReconciliation?: boolean;
  onClick?: () => void;
}

/** Flight chip: small pill with flight code + delay indicator, rings for prediction/reconciliation. */
export function FlightMapMarker({
  flight,
  x,
  y,
  selected,
  dim,
  impacted = false,
  showPrediction = true,
  showReconciliation = true,
  onClick,
}: FlightMapMarkerProps) {
  const hasPrediction = flight.predicted_eta != null || flight.predicted_arrival_delay_min != null;
  const hasRecon = flight.reconciled_eta != null || flight.reconciled_gate != null;
  const mismatch = hasReconciliationMismatch(flight);
  const delayMin = flight.predicted_arrival_delay_min ?? 0;
  const showDelay = delayMin > 15;

  const baseOpacity = dim ? 0.4 : 1;
  const chipW = 36;
  const chipH = 18;

  return (
    <g
      transform={`translate(${x},${y})`}
      className="cursor-pointer"
      style={{ opacity: baseOpacity }}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      {/* Impact ring (amber) – when part of impact chain */}
      {impacted && (
        <ellipse
          rx={chipW / 2 + 14}
          ry={chipH / 2 + 14}
          className="fill-none stroke-amber-400/70 stroke-[2]"
          strokeDasharray="5 5"
        />
      )}
      {/* Reconciliation ring (sky) – outer */}
      {showReconciliation && hasRecon && (
        <ellipse
          rx={chipW / 2 + 10}
          ry={chipH / 2 + 10}
          className="fill-none stroke-sky-400/50 stroke-[1.5]"
          strokeDasharray="4 3"
        />
      )}
      {/* Prediction ring (violet) */}
      {showPrediction && hasPrediction && (
        <ellipse
          rx={chipW / 2 + 6}
          ry={chipH / 2 + 6}
          className="fill-none stroke-violet-400/60 stroke-[1.5]"
        />
      )}
      {/* Mismatch: amber ring */}
      {mismatch && (
        <ellipse
          rx={chipW / 2 + 3}
          ry={chipH / 2 + 3}
          className="fill-none stroke-amber-400/80 stroke-[2]"
        />
      )}
      {/* Chip background */}
      <rect
        x={-chipW / 2}
        y={-chipH / 2}
        width={chipW}
        height={chipH}
        rx={4}
        className={cn(
          "transition-all duration-200",
          selected ? "fill-primary stroke-2 stroke-primary-foreground" : "fill-primary/95 stroke-[1.5] stroke-slate-600"
        )}
      />
      {/* Flight code (last 4 chars or id) */}
      <text
        x={0}
        y={showDelay ? -2 : 0}
        textAnchor="middle"
        dominantBaseline="middle"
        className="fill-primary-foreground text-[9px] font-bold font-mono"
      >
        {flight.flight_code?.slice(-4) ?? `#${flight.id}`}
      </text>
      {/* Delay indicator */}
      {showDelay && (
        <text
          x={0}
          y={6}
          textAnchor="middle"
          className="fill-amber-300 text-[8px] font-semibold"
        >
          +{Math.round(delayMin)}
        </text>
      )}
      {/* Selected glow */}
      {selected && (
        <ellipse
          rx={chipW / 2 + 8}
          ry={chipH / 2 + 8}
          className="fill-none stroke-primary/60 stroke-[2]"
          filter="url(#mapGlow)"
        />
      )}
    </g>
  );
}

/** Compact variant: dot only (for very dense views). */
export function FlightMapMarkerCompact({
  flight,
  x,
  y,
  selected,
  dim,
  onClick,
}: {
  flight: Flight;
  x: number;
  y: number;
  selected?: boolean;
  dim?: boolean;
  onClick?: () => void;
}) {
  const mismatch = hasReconciliationMismatch(flight);
  const baseOpacity = dim ? 0.4 : 1;
  const r = selected ? 9 : 6;

  return (
    <g
      transform={`translate(${x},${y})`}
      className="cursor-pointer"
      style={{ opacity: baseOpacity }}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      {mismatch && (
        <circle r={r + 2} className="fill-none stroke-amber-400/70 stroke-[1.5]" />
      )}
      <circle
        r={r}
        className={cn(
          "fill-primary stroke-[2px] transition-all duration-200",
          selected ? "stroke-primary-foreground" : "stroke-slate-700"
        )}
      />
      {selected && (
        <circle
          r={r + 5}
          className="fill-none stroke-primary/50 stroke-[1.5]"
          filter="url(#mapGlow)"
        />
      )}
    </g>
  );
}
