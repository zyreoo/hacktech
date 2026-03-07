"use client";

import { useState, useMemo } from "react";
import { Header } from "@/components/layout/header";
import { FlightsTable } from "@/components/flights/flights-table";
import { FlightFilters, type FlightFilterState } from "@/components/flights/flight-filters";
import { TableLoadingState } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { useFlightsWithSimulation } from "@/lib/hooks/simulation-data";

export default function FlightsPage() {
  const { data: flights, isLoading, isError, refetch } = useFlightsWithSimulation({ limit: 200 });

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
