"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  getPointForGateOrStand,
  TERMINAL_ZONES,
  LANDSIDE_POLYGON,
  APRON_POLYGON,
  TAXIWAY_SEGMENTS,
  VIEWBOX_SIZE,
} from "@/lib/command-center/map-config";
import { getQueueHotspots } from "@/lib/command-center/selectors";
import type {
  Flight,
  Alert,
  Runway,
  PassengerFlow,
  InfrastructureAsset,
} from "@/types/api";
import { FlightMapMarker } from "./flight-map-marker";
import { RunwayLayer } from "./runway-layer";
import { QueueHeatLayer } from "./queue-heat-layer";
import { InfrastructureLayer } from "./infrastructure-layer";
import type { LayerVisibility } from "./layer-controls";

export interface ImpactConnectionLine {
  from: { x: number; y: number };
  to: { x: number; y: number };
}

interface AirportDigitalTwinMapProps {
  flights: Flight[];
  alerts: Alert[];
  runways: Runway[];
  passengerFlows: PassengerFlow[];
  infrastructure: InfrastructureAsset[];
  layerVisibility: LayerVisibility;
  selectedEntity?: { type: string; id: string } | null;
  onSelectFlight?: (flight: Flight) => void;
  onSelectAlert?: (alert: Alert) => void;
  onSelectRunway?: (runway: Runway) => void;
  onSelectInfrastructure?: (asset: InfrastructureAsset) => void;
  onMapClick?: () => void;
  /** When set, highlight affected flights and runways and draw connection lines */
  impactHighlight?: { affectedFlightIds: Set<number>; affectedRunwayIds: Set<number> };
  connectionLines?: ImpactConnectionLine[];
  className?: string;
}

/** Whether we should dim non-selected entities (when something is selected). */
function shouldDimLayers(selectedEntity: { type: string; id: string } | null | undefined): boolean {
  return selectedEntity != null;
}

export function AirportDigitalTwinMap({
  flights,
  alerts,
  runways,
  passengerFlows,
  infrastructure,
  layerVisibility,
  selectedEntity,
  onSelectFlight,
  onSelectAlert,
  onSelectRunway,
  onSelectInfrastructure,
  onMapClick,
  impactHighlight,
  connectionLines = [],
  className,
}: AirportDigitalTwinMapProps) {
  const hotspots = useMemo(() => getQueueHotspots(passengerFlows), [passengerFlows]);
  const scale = 1;
  const dimLayers = shouldDimLayers(selectedEntity);
  const affectedFlightIds = impactHighlight?.affectedFlightIds ?? new Set<number>();
  const affectedRunwayIds = impactHighlight?.affectedRunwayIds ?? new Set<number>();

  return (
    <div
      className={cn(
        "relative h-full w-full overflow-hidden rounded-xl border-2 border-slate-600/90 bg-slate-950 shadow-2xl ring-2 ring-slate-800/50",
        className
      )}
      onClick={onMapClick}
    >
      <svg
        viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
        preserveAspectRatio="xMidYMid meet"
        className="h-full w-full"
      >
        <defs>
          <filter id="mapGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ─── Base: landside (dark strip at bottom) ───────────────────────── */}
        <polygon
          points={LANDSIDE_POLYGON.map((p) => `${p.x},${p.y}`).join(" ")}
          className="fill-slate-900/90 stroke-slate-700/40 stroke-[1]"
        />

        {/* ─── Base: apron / airside ──────────────────────────────────────── */}
        <polygon
          points={APRON_POLYGON.map((p) => `${p.x},${p.y}`).join(" ")}
          className="fill-slate-800/70 stroke-slate-600/40 stroke-[1]"
        />

        {/* ─── Taxiways (apron links to runways/terminals) ─────────────────── */}
        <g className="taxiways" strokeWidth={4} strokeLinecap="round">
          {TAXIWAY_SEGMENTS.map((seg, i) => (
            <line
              key={i}
              x1={seg.start.x}
              y1={seg.start.y}
              x2={seg.end.x}
              y2={seg.end.y}
              className="stroke-slate-600/50"
            />
          ))}
        </g>

        {/* ─── Base: terminal buildings (stronger contrast) ───────────────── */}
        <g className="terminal-structure">
          {TERMINAL_ZONES.map((zone) => (
            <polygon
              key={zone.id}
              points={zone.polygon.map((p) => `${p.x},${p.y}`).join(" ")}
              className="fill-slate-800 stroke-slate-500/60 stroke-[1.5]"
            />
          ))}
        </g>

        {/* ─── Concourses (spine lines inside terminals) ───────────────────── */}
        <g className="concourse-lines stroke-slate-400/50" strokeWidth={1.5}>
          {TERMINAL_ZONES.flatMap((zone) =>
            zone.concourses.map((c, i) => (
              <line
                key={`${zone.id}-${i}`}
                x1={c.start.x}
                y1={c.start.y}
                x2={c.end.x}
                y2={c.end.y}
              />
            ))
          )}
        </g>

        {/* ─── Gate ticks (small marks along gate side) ───────────────────── */}
        {TERMINAL_ZONES.map((zone) => {
          const row = zone.gateRow;
          if (!row) return null;
          const count = row.count;
          const step = (row.yMax - row.yMin) / Math.max(count - 1, 1);
          const x = row.side === "left" ? zone.polygon[0].x + 12 : zone.polygon[1].x - 12;
          return (
            <g key={`gates-${zone.id}`} className="fill-slate-500/30">
              {Array.from({ length: count }).map((_, i) => {
                const y = row.yMin + step * i;
                return <circle key={i} cx={x} cy={y} r={2} />;
              })}
            </g>
          );
        })}

        {/* ─── Queue heat overlay (spatial only) ───────────────────────────── */}
        {layerVisibility.queues && (
          <QueueHeatLayer
            hotspots={hotspots}
            scale={scale}
            dim={dimLayers}
          />
        )}

        {/* ─── Impact connection lines (root → affected) ───────────────────── */}
        {connectionLines.length > 0 && (
          <g className="impact-lines" strokeWidth={1.5} strokeDasharray="6 4" stroke="rgba(251,191,36,0.6)">
            {connectionLines.map((line, i) => (
              <line
                key={i}
                x1={line.from.x}
                y1={line.from.y}
                x2={line.to.x}
                y2={line.to.y}
                className="pointer-events-none"
              />
            ))}
          </g>
        )}

        {/* ─── Runways ────────────────────────────────────────────────────── */}
        {layerVisibility.runways && (
          <RunwayLayer
            runways={runways}
            scale={scale}
            selectedEntity={selectedEntity}
            dim={dimLayers}
            impactedRunwayIds={affectedRunwayIds}
          />
        )}

        {/* ─── Infrastructure markers ─────────────────────────────────────── */}
        {layerVisibility.infrastructure && (
          <InfrastructureLayer
            assets={infrastructure}
            scale={scale}
            selectedEntity={selectedEntity}
            dim={dimLayers}
          />
        )}

        {/* ─── Flights at gates (spatial only: dot + rings) ────────────────── */}
        {layerVisibility.flights &&
          flights.map((flight) => {
            const point = getPointForGateOrStand(flight.gate ?? flight.stand ?? null);
            const selected =
              selectedEntity?.type === "flight" && String(flight.id) === selectedEntity.id;
            const dim = dimLayers && !selected;
            const impacted = affectedFlightIds.has(flight.id);
            return (
              <FlightMapMarker
                key={flight.id}
                flight={flight}
                x={point.x}
                y={point.y}
                selected={selected}
                dim={dim}
                impacted={impacted}
                showPrediction={layerVisibility.prediction}
                showReconciliation={layerVisibility.reconciliation}
                onClick={() => onSelectFlight?.(flight)}
              />
            );
          })}

        {/* ─── Alert markers (spatial only: triangle, critical = pulse) ────── */}
        {layerVisibility.alerts &&
          alerts.filter((a) => !a.resolved).map((alert) => {
            const entityId = alert.related_entity_id;
            const flight = entityId ? flights.find((f) => String(f.id) === entityId) : null;
            const point = flight
              ? getPointForGateOrStand(flight.gate ?? flight.stand ?? null)
              : { x: 500, y: 180 };
            const isCritical = alert.severity === "critical";
            const selected =
              selectedEntity?.type === "alert" && String(alert.id) === selectedEntity.id;
            const dim = dimLayers && !selected;
            const size = 6;
            return (
              <g
                key={alert.id}
                transform={`translate(${point.x},${point.y - 24})`}
                className="cursor-pointer"
                style={{ opacity: dim ? 0.45 : 1 }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectAlert?.(alert);
                }}
              >
                {/* Triangle pointing up (alert icon) */}
                <polygon
                  points={`0,${-size} ${size},${size} ${-size},${size}`}
                  className={
                    isCritical
                      ? "fill-red-500 stroke-red-300 stroke-[2] map-pulse-critical"
                      : "fill-amber-500 stroke-amber-400/80 stroke-[1.5]"
                  }
                />
                {selected && (
                  <polygon
                    points={`0,${-size - 4} ${size + 4},${size + 4} ${-size - 4},${size + 4}`}
                    className="fill-none stroke-primary stroke-[2]"
                    filter="url(#mapGlow)"
                  />
                )}
              </g>
            );
          })}
      </svg>
    </div>
  );
}
