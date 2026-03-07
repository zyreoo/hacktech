import { Plane, AlertTriangle, Wind, Users } from "lucide-react";
import { MetricCard } from "@/components/shared/metric-card";
import type { OverviewResponse } from "@/types/api";

interface KpiStripProps {
  overview: OverviewResponse;
}

export function KpiStrip({ overview }: KpiStripProps) {
  const totalFlights = overview.current_flights.length;
  const activeAlerts = overview.active_alerts.filter((a) => !a.resolved);
  const criticalAlerts = activeAlerts.filter((a) => a.severity === "critical");
  const runwaysWithHazards = overview.runway_conditions.filter((r) => r.hazard_detected).length;
  const totalPassengers = overview.passenger_queues.reduce(
    (sum, q) => sum + q.check_in_count + q.security_queue_count + q.boarding_count,
    0
  );
  const delayedFlights = overview.current_flights.filter(
    (f) => f.status === "delayed" || (f.predicted_arrival_delay_min ?? 0) > 15
  ).length;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      <MetricCard
        title="Active Flights"
        value={totalFlights}
        icon={Plane}
        subtitle={`${delayedFlights} delayed`}
        highlight={delayedFlights > 0 ? "warning" : "default"}
      />
      <MetricCard
        title="Critical Alerts"
        value={criticalAlerts.length}
        icon={AlertTriangle}
        highlight={criticalAlerts.length > 0 ? "danger" : "default"}
        subtitle={`${activeAlerts.length} total active`}
      />
      <MetricCard
        title="Runways"
        value={overview.runway_conditions.length}
        icon={Wind}
        highlight={runwaysWithHazards > 0 ? "danger" : "default"}
        subtitle={`${runwaysWithHazards} hazards detected`}
      />
      <MetricCard
        title="Pax in Flow"
        value={totalPassengers.toLocaleString()}
        icon={Users}
        subtitle="check-in + security + boarding"
      />
      <MetricCard
        title="Resources"
        value={overview.resource_status.length}
        subtitle={`${overview.resource_status.filter((r) => r.status === "available").length} available`}
      />
      <MetricCard
        title="Infra Assets"
        value={overview.infrastructure_status.length}
        highlight={
          overview.infrastructure_status.some((a) => a.tamper_detected)
            ? "danger"
            : overview.infrastructure_status.some((a) => a.status === "degraded" || a.status === "offline")
            ? "warning"
            : "default"
        }
        subtitle={`${overview.infrastructure_status.filter((a) => a.tamper_detected).length} tamper flags`}
      />
    </div>
  );
}
