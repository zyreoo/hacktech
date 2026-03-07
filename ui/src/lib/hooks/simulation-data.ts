/**
 * Hooks that merge API data with simulation overrides so every page sees the same simulated state.
 * Use these instead of raw useFlights/useRunways/useOverview when SimulationProvider is present.
 */

import { useMemo } from "react";
import { useFlights, useRunways, useOverview, usePassengerFlow } from "@/lib/hooks/queries";
import { useSimulationOptional } from "@/context/simulation-context";
import type { PassengerFlow } from "@/types/api";
import type { OverviewResponse } from "@/types/api";

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

/** Flights: from API only (delay/runway simulation is persisted to DB). */
export function useFlightsWithSimulation(params?: { skip?: number; limit?: number }) {
  return useFlights(params);
}

/** Runways: from API only (status simulation is persisted to DB). */
export function useRunwaysWithSimulation() {
  return useRunways();
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

/** Overview: flight/runway from API; queue load multiplier applied in frontend only. */
export function useOverviewWithSimulation() {
  const query = useOverview();
  const sim = useSimulationOptional();
  const data = useMemo((): OverviewResponse | undefined => {
    const raw = query.data;
    if (!raw) return raw;
    if (!sim?.overrides?.queueLoadMultiplier || Object.keys(sim.overrides.queueLoadMultiplier).length === 0)
      return raw;
    return {
      ...raw,
      passenger_queues: mergePassengerFlows(raw.passenger_queues, sim.overrides.queueLoadMultiplier),
    };
  }, [query.data, sim?.overrides?.queueLoadMultiplier]);
  return { ...query, data };
}
