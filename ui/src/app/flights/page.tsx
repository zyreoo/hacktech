"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { FlightsTable } from "@/components/flights/flights-table";
import { FlightFilters, type FlightFilterState } from "@/components/flights/flight-filters";
import { TableLoadingState } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { useFlights, useFlightIssues, useReassignFlight, useRunways, useResources } from "@/lib/hooks/queries";
import { Button } from "@/components/ui/button";
import { ShieldCheck, AlertTriangle } from "lucide-react";

const issueSeverityStyles: Record<string, string> = {
  critical: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 text-red-800 dark:text-red-200",
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
  low: "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300",
};

export default function FlightsPage() {
  const { data: flights, isLoading, isError, refetch } = useFlights({ limit: 200 });
  const { data: issues = [], isLoading: issuesLoading } = useFlightIssues({ limit: 500 });
  const { data: runways = [] } = useRunways();
  const { data: resources = [] } = useResources({ limit: 200 });
  const reassignFlightMutation = useReassignFlight();
  const activeRunwayId = runways.find((r) => r.status === "active")?.id ?? null;
  const availableGates = useMemo(
    () => resources
      .filter((r) => (r.resource_type || "").toLowerCase() === "gate" && (r.status || "").toLowerCase() === "available")
      .map((r) => r.resource_name)
      .filter((n): n is string => Boolean(n))
      .sort(),
    [resources]
  );
  const getAvailableGateForConflict = (conflictGate: string | undefined) =>
    conflictGate ? availableGates.find((g) => g !== conflictGate) ?? availableGates[0] : availableGates[0];

  const [filters, setFilters] = useState<FlightFilterState>({
    search: "",
    status: "all",
    airline: "all",
  });

  const airlines = useMemo(
    () => [...new Set(flights?.map((f) => f.airline) ?? [])].sort(),
    [flights]
  );

  const filtered = useMemo(() => {
    if (!flights) return [];
    return flights.filter((f) => {
      const q = filters.search.toLowerCase();
      const matchSearch =
        !q ||
        f.flight_code.toLowerCase().includes(q) ||
        f.origin.toLowerCase().includes(q) ||
        f.destination.toLowerCase().includes(q) ||
        f.airline.toLowerCase().includes(q);
      const matchStatus = filters.status === "all" || f.status === filters.status;
      const matchAirline = filters.airline === "all" || f.airline === filters.airline;
      return matchSearch && matchStatus && matchAirline;
    });
  }, [flights, filters]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header
        title="Flights / AODB"
        subtitle="Canonical flight list with raw, reconciled, and predicted data"
      />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Self-healing & conflicts */}
        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-slate-100">
            <ShieldCheck className="h-4 w-4 text-slate-500" />
            Self-healing & conflicts
          </h2>
          {issuesLoading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/50 px-4 py-3 text-sm text-slate-500">
              Checking for issues…
            </div>
          )}
          {!issuesLoading && issues.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-emerald-50/50 dark:border-slate-700 dark:bg-emerald-950/20 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              No flight conflicts. Runway and gate assignments are aligned with operational state.
            </div>
          )}
          {!issuesLoading && issues.length > 0 && (
            <ul className="mb-6 space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.flight_id}-${i}`}
                  className={`rounded-xl border px-4 py-3 text-sm ${issueSeverityStyles[issue.severity] ?? issueSeverityStyles.low}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Link
                          href={`/flights/${issue.flight_id}`}
                          className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs underline dark:bg-black/20 hover:opacity-80"
                        >
                          Flight #{issue.flight_id}
                        </Link>
                        {issue.flight_code && (
                          <span className="font-mono text-xs opacity-90">{issue.flight_code}</span>
                        )}
                        {issue.runway_code && (
                          <span className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">
                            {issue.runway_code}
                          </span>
                        )}
                        {issue.gate && (
                          <span className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">
                            Gate {issue.gate}
                          </span>
                        )}
                      </div>
                      {issue.type === "runway_unavailable" && issue.flight_id != null && activeRunwayId != null && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="mt-2 shrink-0 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
                          disabled={reassignFlightMutation.isPending}
                          onClick={() => reassignFlightMutation.mutate({ id: issue.flight_id!, runway_id: activeRunwayId })}
                        >
                          {reassignFlightMutation.isPending ? "Applying…" : "Reassign to active runway"}
                        </Button>
                      )}
                      {issue.type === "gate_conflict" && issue.flight_id != null && (() => {
                        const targetGate = getAvailableGateForConflict(issue.gate ?? undefined);
                        return (
                          <Button
                            size="sm"
                            variant="outline"
                            className="mt-2 shrink-0 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
                            disabled={reassignFlightMutation.isPending || !targetGate}
                            onClick={() => targetGate && reassignFlightMutation.mutate({
                              id: issue.flight_id!,
                              gate: targetGate,
                              reconciled_gate: targetGate,
                            })}
                          >
                            {reassignFlightMutation.isPending ? "Applying…" : targetGate ? `Reassign to ${targetGate}` : "No available gate"}
                          </Button>
                        );
                      })()}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="mb-5 flex items-center justify-between gap-4">
          <FlightFilters filters={filters} airlines={airlines} onChange={setFilters} />
          <p className="shrink-0 text-xs text-slate-500">
            {filtered.length} / {flights?.length ?? 0} flights
          </p>
        </div>

        {isLoading && <TableLoadingState rows={10} />}
        {isError && (
          <ErrorState message="Could not load flights." onRetry={() => refetch()} />
        )}
        {!isLoading && !isError && <FlightsTable flights={filtered} />}
      </main>
    </div>
  );
}
