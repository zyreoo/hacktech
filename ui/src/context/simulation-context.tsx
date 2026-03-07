"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface SimulationOverrides {
  /** flight id -> simulated delay (minutes) */
  flightDelays: Record<number, number>;
  /** runway id -> closed */
  runwayClosed: Set<number>;
  /** zone/terminal id -> multiplier (e.g. 1.5 = 50% more load) */
  queueLoadMultiplier: Record<string, number>;
}

const defaultOverrides: SimulationOverrides = {
  flightDelays: {},
  runwayClosed: new Set(),
  queueLoadMultiplier: {},
};

interface SimulationContextValue {
  overrides: SimulationOverrides;
  applyFlightDelay: (flightId: number, delayMinutes: number) => void;
  clearFlightDelay: (flightId: number) => void;
  clearAllFlightDelays: () => void;
  applyRunwayClosed: (runwayId: number, closed: boolean) => void;
  clearAllRunwayClosed: () => void;
  applyQueueLoad: (zoneId: string, multiplier: number) => void;
  clearQueueLoad: (zoneId: string) => void;
  clearAllQueueLoads: () => void;
  clearAll: () => void;
  hasOverrides: boolean;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export function SimulationProvider({ children }: { children: ReactNode }) {
  const [overrides, setOverrides] = useState<SimulationOverrides>(defaultOverrides);

  const applyFlightDelay = useCallback((flightId: number, delayMinutes: number) => {
    setOverrides((prev) => ({
      ...prev,
      flightDelays: { ...prev.flightDelays, [flightId]: delayMinutes },
    }));
  }, []);

  const clearFlightDelay = useCallback((flightId: number) => {
    setOverrides((prev) => {
      const next = { ...prev.flightDelays };
      delete next[flightId];
      return { ...prev, flightDelays: next };
    });
  }, []);

  const clearAllFlightDelays = useCallback(() => {
    setOverrides((prev) => ({ ...prev, flightDelays: {} }));
  }, []);

  const applyRunwayClosed = useCallback((runwayId: number, closed: boolean) => {
    setOverrides((prev) => {
      const next = new Set(prev.runwayClosed);
      if (closed) next.add(runwayId);
      else next.delete(runwayId);
      return { ...prev, runwayClosed: next };
    });
  }, []);

  const applyQueueLoad = useCallback((zoneId: string, multiplier: number) => {
    setOverrides((prev) => ({
      ...prev,
      queueLoadMultiplier: { ...prev.queueLoadMultiplier, [zoneId]: multiplier },
    }));
  }, []);

  const clearQueueLoad = useCallback((zoneId: string) => {
    setOverrides((prev) => {
      const next = { ...prev.queueLoadMultiplier };
      delete next[zoneId];
      return { ...prev, queueLoadMultiplier: next };
    });
  }, []);

  const clearAllRunwayClosed = useCallback(() => {
    setOverrides((prev) => ({ ...prev, runwayClosed: new Set() }));
  }, []);

  const clearAllQueueLoads = useCallback(() => {
    setOverrides((prev) => ({ ...prev, queueLoadMultiplier: {} }));
  }, []);

  const clearAll = useCallback(() => {
    setOverrides({
      flightDelays: {},
      runwayClosed: new Set(),
      queueLoadMultiplier: {},
    });
  }, []);

  const hasOverrides =
    Object.keys(overrides.flightDelays).length > 0 ||
    overrides.runwayClosed.size > 0 ||
    Object.keys(overrides.queueLoadMultiplier).length > 0;

  const value = useMemo(
    () => ({
      overrides,
      applyFlightDelay,
      clearFlightDelay,
      clearAllFlightDelays,
      applyRunwayClosed,
      clearAllRunwayClosed,
      applyQueueLoad,
      clearQueueLoad,
      clearAllQueueLoads,
      clearAll,
      hasOverrides,
    }),
    [
      overrides,
      applyFlightDelay,
      clearFlightDelay,
      clearAllFlightDelays,
      applyRunwayClosed,
      clearAllRunwayClosed,
      applyQueueLoad,
      clearQueueLoad,
      clearAllQueueLoads,
      clearAll,
      hasOverrides,
    ]
  );

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const ctx = useContext(SimulationContext);
  if (!ctx) {
    throw new Error("useSimulation must be used within SimulationProvider");
  }
  return ctx;
}

export function useSimulationOptional() {
  return useContext(SimulationContext);
}
