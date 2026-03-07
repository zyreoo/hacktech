"use client";

import { useState } from "react";
import { useSimulation } from "@/context/simulation-context";
import type { Flight, Runway } from "@/types/api";
import { cn } from "@/lib/utils";
import { Play, X, Plane, Circle, Users } from "lucide-react";

interface SimulationControlsProps {
  flights: Flight[];
  runways: Runway[];
  className?: string;
}

export function SimulationControls({ flights, runways, className }: SimulationControlsProps) {
  const {
    overrides,
    applyFlightDelay,
    clearAllFlightDelays,
    applyRunwayClosed,
    clearAllRunwayClosed,
    applyQueueLoad,
    clearAllQueueLoads,
    clearAll,
    hasOverrides,
  } = useSimulation();
  const [expanded, setExpanded] = useState(false);
  const [flightId, setFlightId] = useState<string>("");
  const [delayMin, setDelayMin] = useState(30);
  const [runwayId, setRunwayId] = useState<string>("");
  const [zoneId, setZoneId] = useState("T2");
  const [queueMult, setQueueMult] = useState(1.5);

  return (
    <div className={cn("rounded-lg border border-border bg-card/80 text-xs", className)}>
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="flex items-center gap-2">
          <Play className="h-3.5 w-3.5" />
          Simulation
        </span>
        {hasOverrides && (
          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">
            Active
          </span>
        )}
      </button>
      {expanded && (
        <div className="space-y-3 border-t border-border p-3">
          {/* Flight delay */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Plane className="h-3 w-3" /> Delay flight
            </span>
            <select
              value={flightId}
              onChange={(e) => setFlightId(e.target.value)}
              className="rounded border border-border bg-background px-2 py-1 text-xs"
            >
              <option value="">Select flight</option>
              {flights.slice(0, 30).map((f) => (
                <option key={f.id} value={f.id}>
                  {f.flight_code} ({f.gate ?? "—"})
                </option>
              ))}
            </select>
            <input
              type="number"
              min={5}
              max={120}
              value={delayMin}
              onChange={(e) => setDelayMin(Number(e.target.value) || 30)}
              className="w-12 rounded border border-border bg-background px-2 py-1 text-xs"
            />
            <span className="text-muted-foreground">min</span>
            <button
              type="button"
              onClick={() => flightId && applyFlightDelay(Number(flightId), delayMin)}
              className="rounded bg-primary px-2 py-1 text-primary-foreground hover:opacity-90"
            >
              Apply
            </button>
            {Object.keys(overrides.flightDelays).length > 0 && (
              <button
                type="button"
                onClick={clearAllFlightDelays}
                className="rounded border border-border px-2 py-1 hover:bg-muted"
              >
                Clear delays
              </button>
            )}
          </div>

          {/* Runway closed */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Circle className="h-3 w-3" /> Runway
            </span>
            <select
              value={runwayId}
              onChange={(e) => setRunwayId(e.target.value)}
              className="rounded border border-border bg-background px-2 py-1 text-xs"
            >
              <option value="">Select runway</option>
              {runways.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.runway_code}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => runwayId && applyRunwayClosed(Number(runwayId), true)}
              className="rounded bg-primary px-2 py-1 text-primary-foreground hover:opacity-90"
            >
              Close
            </button>
            {overrides.runwayClosed.size > 0 && (
              <button
                type="button"
                onClick={clearAllRunwayClosed}
                className="rounded border border-border px-2 py-1 hover:bg-muted"
              >
                Reopen all
              </button>
            )}
          </div>

          {/* Queue load */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Users className="h-3 w-3" /> Queue load
            </span>
            <select
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value)}
              className="rounded border border-border bg-background px-2 py-1 text-xs"
            >
              <option value="T1">T1</option>
              <option value="T2">T2</option>
              <option value="T3">T3</option>
            </select>
            <input
              type="number"
              min={1}
              max={3}
              step={0.25}
              value={queueMult}
              onChange={(e) => setQueueMult(Number(e.target.value) || 1)}
              className="w-12 rounded border border-border bg-background px-2 py-1 text-xs"
            />
            <span className="text-muted-foreground">×</span>
            <button
              type="button"
              onClick={() => applyQueueLoad(zoneId, queueMult)}
              className="rounded bg-primary px-2 py-1 text-primary-foreground hover:opacity-90"
            >
              Apply
            </button>
            {Object.keys(overrides.queueLoadMultiplier).length > 0 && (
              <button
                type="button"
                onClick={clearAllQueueLoads}
                className="rounded border border-border px-2 py-1 hover:bg-muted"
              >
                Clear queue
              </button>
            )}
          </div>

          {hasOverrides && (
            <button
              type="button"
              onClick={clearAll}
              className="flex items-center gap-1 rounded border border-red-500/50 bg-red-500/10 px-2 py-1 text-red-600 dark:text-red-400"
            >
              <X className="h-3 w-3" /> Clear all simulation
            </button>
          )}
        </div>
      )}
    </div>
  );
}
