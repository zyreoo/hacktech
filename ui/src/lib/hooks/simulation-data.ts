/**
 * Hooks that merge API data with simulation overrides so every page sees the same simulated state.
 * Use these instead of raw useFlights/useRunways/useOverview when SimulationProvider is present.
 */

import { useMemo } from "react";
import { useFlights, useRunways, useOverview, usePassengerFlow } from "@/lib/hooks/queries";
import { useSimulationOptional } from "@/context/simulation-context";
import type { Flight, Runway, PassengerFlow } from "@/types/api";
import type { OverviewResponse } from "@/types/api";

function mergeFlights(flights: Flight[], flightDelays: Record<number, number>): Flight[] {
  if (Object.keys(flightDelays).length === 0) return flights;
  return flights.map((f) => {
    const override = flightDelays[f.id];
    if (override == null) return f;
    return { ...f, predicted_arrival_delay_min: override };
  });
}

function mergeRunways(runways: Runway[], runwayClosed: Set<number>): Runway[] {
  if (runwayClosed.size === 0) return runways;
  return runways.map((r) => {
    if (!runwayClosed.has(r.id)) return r;
    return { ...r, status: "closed" as const };
  });
}

function mergePassengerFlows(
  flows: PassengerFlow[],
  queueLoadMultiplier: Record<string, number>
): PassengerFlow[] {
  if (Object.keys(queueLoadMultiplier).length === 0) return flows;
  return flows.map((f) => {
    const zone = f.terminal_zone ?? "T2";
    const mult = queueLoadMultiplier[zone];
    if (mult == null || mult === 1) return f;
    return {
      ...f,
      security_queue_count: Math.round(f.security_queue_count * mult),
      check_in_count: Math.round(f.check_in_count * mult),
      boarding_count: Math.round(f.boarding_count * mult),
    };
  });
}

/** Flights with optional simulation overrides (delay minutes) applied. */
export function useFlightsWithSimulation(params?: { skip?: number; limit?: number }) {
  const query = useFlights(params);
  const sim = useSimulationOptional();
  const data = useMemo(() => {
    const raw = query.data ?? [];
    if (!sim?.overrides) return raw;
    return mergeFlights(raw, sim.overrides.flightDelays);
  }, [query.data, sim?.overrides?.flightDelays]);
  return { ...query, data };
}

/** Runways with optional simulation overrides (closed) applied. */
export function useRunwaysWithSimulation() {
  const query = useRunways();
  const sim = useSimulationOptional();
  const data = useMemo(() => {
    const raw = query.data ?? [];
    if (!sim?.overrides) return raw;
    return mergeRunways(raw, sim.overrides.runwayClosed);
  }, [query.data, sim?.overrides?.runwayClosed]);
  return { ...query, data };
}

/** Passenger flows with optional queue load multipliers applied. */
export function usePassengerFlowWithSimulation(params?: { limit?: number }) {
  const query = usePassengerFlow(params);
  const sim = useSimulationOptional();
  const data = useMemo(() => {
    const raw = query.data ?? [];
    if (!sim?.overrides) return raw;
    return mergePassengerFlows(raw, sim.overrides.queueLoadMultiplier);
  }, [query.data, sim?.overrides?.queueLoadMultiplier]);
  return { ...query, data };
}

/** Overview with simulation overrides merged into current_flights, runway_conditions, passenger_queues. */
export function useOverviewWithSimulation() {
  const query = useOverview();
  const sim = useSimulationOptional();
  const data = useMemo((): OverviewResponse | undefined => {
    const raw = query.data;
    if (!raw) return raw;
    if (!sim?.overrides) return raw;
    return {
      ...raw,
      current_flights: mergeFlights(raw.current_flights, sim.overrides.flightDelays),
      runway_conditions: mergeRunways(raw.runway_conditions, sim.overrides.runwayClosed),
      passenger_queues: mergePassengerFlows(raw.passenger_queues, sim.overrides.queueLoadMultiplier),
    };
  }, [
    query.data,
    sim?.overrides?.flightDelays,
    sim?.overrides?.runwayClosed,
    sim?.overrides?.queueLoadMultiplier,
  ]);
  return { ...query, data };
}
