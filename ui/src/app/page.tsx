"use client";

import { Header } from "@/components/layout/header";
import { KpiStrip } from "@/components/dashboard/kpi-strip";
import { ActiveAlertsCard } from "@/components/dashboard/active-alerts-card";
import { FlightsSummary } from "@/components/dashboard/flights-summary";
import { RunwaySummary } from "@/components/dashboard/runway-summary";
import { PassengerQueueSummary } from "@/components/dashboard/passenger-queue-summary";
import { InfrastructureSummary } from "@/components/dashboard/infrastructure-summary";
import { CardLoadingState, SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { useOverview } from "@/lib/hooks/queries";

export default function DashboardPage() {
  const { data: overview, isLoading, isError, refetch } = useOverview();

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header
        title="Operations Dashboard"
        subtitle="Real-time airport operational state"
      />
      <main className="flex-1 overflow-y-auto p-6">
        {isLoading && (
          <div className="space-y-6">
            <CardLoadingState rows={6} />
            <SpinnerLoader />
          </div>
        )}
        {isError && (
          <ErrorState
            message="Could not load operations overview. Is the backend running?"
            onRetry={() => refetch()}
          />
        )}
        {overview && (
          <div className="space-y-6">
            {/* KPI strip */}
            <KpiStrip overview={overview} />

            {/* Alerts + Flights */}
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <FlightsSummary flights={overview.current_flights} />
              </div>
              <div>
                <ActiveAlertsCard alerts={overview.active_alerts} />
              </div>
            </div>

            {/* Runways + Passenger Flow */}
            <div className="grid gap-6 lg:grid-cols-2">
              <RunwaySummary runways={overview.runway_conditions} />
              <PassengerQueueSummary flows={overview.passenger_queues} />
            </div>

            {/* Infrastructure */}
            <InfrastructureSummary assets={overview.infrastructure_status} />
          </div>
        )}
      </main>
    </div>
  );
}
