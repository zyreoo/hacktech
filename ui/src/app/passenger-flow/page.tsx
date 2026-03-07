"use client";

import { useMemo } from "react";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/shared/metric-card";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { usePassengerFlow } from "@/lib/hooks/queries";
import { formatDateTime } from "@/lib/utils";
import { Users, UserCheck, Shield, PlaneLanding } from "lucide-react";
import Link from "next/link";

export default function PassengerFlowPage() {
  const { data: flows = [], isLoading, isError, refetch } = usePassengerFlow({ limit: 200 });

  const totals = useMemo(() => ({
    checkIn:   flows.reduce((s, f) => s + f.check_in_count, 0),
    security:  flows.reduce((s, f) => s + f.security_queue_count, 0),
    boarding:  flows.reduce((s, f) => s + f.boarding_count, 0),
    avgQueue:  flows.length > 0
      ? flows.filter((f) => f.predicted_queue_time != null).reduce((s, f) => s + (f.predicted_queue_time ?? 0), 0) /
        Math.max(flows.filter((f) => f.predicted_queue_time != null).length, 1)
      : null,
  }), [flows]);

  const byTerminal = useMemo(() => {
    const map: Record<string, typeof flows> = {};
    flows.forEach((f) => {
      const zone = f.terminal_zone ?? "Unknown";
      if (!map[zone]) map[zone] = [];
      map[zone].push(f);
    });
    return map;
  }, [flows]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header title="Passenger Flow" subtitle="Real-time passenger queue data across terminals" />
      <main className="flex-1 overflow-y-auto p-6">
        {isLoading && <SpinnerLoader />}
        {isError && <ErrorState message="Could not load passenger flow." onRetry={() => refetch()} />}

        {!isLoading && !isError && flows.length === 0 && (
          <EmptyState icon={Users} title="No flow data" description="No passenger flow data available." />
        )}

        {flows.length > 0 && (
          <div className="space-y-6">
            {/* KPIs */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <MetricCard title="Check-in" value={totals.checkIn.toLocaleString()} icon={UserCheck} />
              <MetricCard
                title="Security Queue"
                value={totals.security.toLocaleString()}
                icon={Shield}
                highlight={totals.security > 200 ? "warning" : "default"}
              />
              <MetricCard title="Boarding" value={totals.boarding.toLocaleString()} icon={PlaneLanding} />
              <MetricCard
                title="Avg Queue Time"
                value={totals.avgQueue != null ? `${totals.avgQueue.toFixed(0)} min` : "—"}
                icon={Users}
              />
            </div>

            {/* Per-terminal breakdown */}
            {Object.entries(byTerminal).map(([zone, zoneFlows]) => (
              <div key={zone} className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    Terminal Zone: <span className="font-mono">{zone}</span>
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Flight</TableHead>
                        <TableHead>Check-in</TableHead>
                        <TableHead>Security Queue</TableHead>
                        <TableHead>Boarding</TableHead>
                        <TableHead>Queue Time (pred.)</TableHead>
                        <TableHead>Recorded At</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {zoneFlows.map((f) => (
                        <TableRow key={f.id} className="border-slate-100 dark:border-slate-800">
                          <TableCell>
                            <Link
                              href={`/flights/${f.flight_id}`}
                              className="font-mono font-semibold text-sky-600 hover:underline dark:text-sky-400"
                            >
                              #{f.flight_id}
                            </Link>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{f.check_in_count}</TableCell>
                          <TableCell>
                            <span className={`font-mono text-sm ${f.security_queue_count > 100 ? "font-bold text-amber-600" : ""}`}>
                              {f.security_queue_count}
                            </span>
                          </TableCell>
                          <TableCell className="font-mono text-sm">{f.boarding_count}</TableCell>
                          <TableCell className="font-mono text-sm">
                            {f.predicted_queue_time != null ? `${f.predicted_queue_time.toFixed(0)} min` : "—"}
                          </TableCell>
                          <TableCell className="text-xs text-slate-500">{formatDateTime(f.timestamp)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
