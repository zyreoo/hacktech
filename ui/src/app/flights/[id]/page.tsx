"use client";

import { use } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { FlightInfoPanel } from "@/components/flight-detail/flight-info-panel";
import { PredictionPanel } from "@/components/flight-detail/prediction-panel";
import { PredictionHistory } from "@/components/flight-detail/prediction-history";
import { FlightUpdatesPanel } from "@/components/flight-detail/flight-updates-panel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { useFlight, useFlightUpdates, usePredictionsForFlight } from "@/lib/hooks/queries";
import { flightStatusVariant } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";

interface Props {
  params: Promise<{ id: string }>;
}

export default function FlightDetailPage({ params }: Props) {
  const { id } = use(params);
  const flightId = Number(id);

  const { data: flight, isLoading, isError, refetch } = useFlight(flightId);
  const { data: updates = [] } = useFlightUpdates(flightId);
  const { data: predictions = [] } = usePredictionsForFlight(flightId);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header
        title={flight ? `${flight.flight_code} — ${flight.origin} → ${flight.destination}` : "Flight Detail"}
        subtitle={flight ? flight.airline : "Loading…"}
      />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Back link */}
        <Link
          href="/flights"
          className="mb-5 inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to Flights
        </Link>

        {isLoading && <SpinnerLoader />}
        {isError && (
          <ErrorState message="Could not load flight." onRetry={() => refetch()} />
        )}

        {flight && (
          <div className="space-y-6">
            {/* Page title strip */}
            <div className="flex items-center gap-3">
              <h2 className="font-mono text-2xl font-bold text-slate-900 dark:text-slate-100">
                {flight.flight_code}
              </h2>
              <StatusBadge
                label={flight.reconciled_status ?? flight.status}
                variant={flightStatusVariant(flight.reconciled_status ?? flight.status)}
                dot
              />
            </div>

            {/* Info panels (raw / reconciled / predicted) */}
            <FlightInfoPanel flight={flight} />

            {/* Tabs: updates / predictions */}
            <Tabs defaultValue="run-prediction">
              <TabsList>
                <TabsTrigger value="run-prediction">Run Prediction</TabsTrigger>
                <TabsTrigger value="source-updates">Source Updates ({updates.length})</TabsTrigger>
                <TabsTrigger value="prediction-history">Prediction History ({predictions.length})</TabsTrigger>
              </TabsList>

              <TabsContent value="run-prediction" className="mt-4">
                <PredictionPanel flightId={flightId} />
              </TabsContent>

              <TabsContent value="source-updates" className="mt-4">
                <FlightUpdatesPanel updates={updates} />
              </TabsContent>

              <TabsContent value="prediction-history" className="mt-4">
                <PredictionHistory records={predictions} />
              </TabsContent>
            </Tabs>
          </div>
        )}
      </main>
    </div>
  );
}
