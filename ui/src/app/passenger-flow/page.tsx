"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/shared/metric-card";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { usePassengerFlow, usePassengerFlowIssues, useOverview } from "@/lib/hooks/queries";
import { formatDateTime } from "@/lib/utils";
import { Users, UserCheck, Shield, PlaneLanding, Activity, ShieldCheck, AlertTriangle } from "lucide-react";

const issueSeverityStyles: Record<string, string> = {
  critical: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 text-red-800 dark:text-red-200",
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
};

export default function PassengerFlowPage() {
  const { data, isLoading, isError, refetch } = usePassengerFlow({ limit: 200 });
  const { data: overview } = useOverview();
  const flowsFromApi = Array.isArray(data) ? data : [];
  const flowsFromOverview = overview?.passenger_queues ?? [];
  const flows = flowsFromApi.length > 0 ? flowsFromApi : flowsFromOverview;
  const { data: issues = [], isLoading: issuesLoading } = usePassengerFlowIssues({ limit: 300 });

  // Add update tracking
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [updateCount, setUpdateCount] = useState(0);
  
  useEffect(() => {
    if (flows.length > 0) {
      const latest = [...flows].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
      setLastUpdate(new Date(latest.timestamp).toLocaleTimeString());
      setUpdateCount(c => c + 1);
    }
  }, [flows]);

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
      <Header 
        title="Passenger Flow" 
        subtitle={
          <div className="flex items-center gap-2">
            <span>Real-time passenger queue data across terminals</span>
            {lastUpdate && (
              <div className="flex items-center gap-1 text-xs text-emerald-600">
                <Activity className="h-3 w-3 animate-pulse" />
                <span>{lastUpdate}</span>
                <span className="text-slate-400">#{updateCount}</span>
              </div>
            )}
          </div>
        } 
      />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Self-healing & data quality */}
        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-slate-100">
            <ShieldCheck className="h-4 w-4 text-slate-500" />
            Self-healing & data quality
          </h2>
          {issuesLoading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/50 px-4 py-3 text-sm text-slate-500">
              Checking for issues…
            </div>
          )}
          {!issuesLoading && Array.isArray(issues) && issues.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-emerald-50/50 dark:border-slate-700 dark:bg-emerald-950/20 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              No flow data quality issues. No stale, orphan, or invalid counts.
            </div>
          )}
          {!issuesLoading && Array.isArray(issues) && issues.length > 0 && (
            <ul className="mb-6 space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.flow_id}-${i}`}
                  className={`rounded-xl border px-4 py-3 text-sm ${issueSeverityStyles[issue.severity] ?? "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300"}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Link href={`/flights/${issue.flight_id}`} className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs underline dark:bg-black/20 hover:opacity-80">
                          Flight #{issue.flight_id}
                        </Link>
                        <span className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">Flow #{issue.flow_id}</span>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {isLoading && <SpinnerLoader />}
        {isError && <ErrorState message="Could not load passenger flow." onRetry={() => refetch()} />}

        {!isLoading && !isError && flows.length === 0 && (
          <EmptyState
            icon={Users}
            title="No flow data"
            description="No passenger flow data available. Start the backend (uvicorn airport_data_hub.main:app --reload from repo root) and wait a few seconds for the synthetic feeder to add data."
          />
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
                highlight={totals.security > 200 ? "warning" : totals.security > 100 ? "default" : "default"}
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
                            <span className={`font-mono text-sm transition-colors duration-300 ${
                              f.security_queue_count > 200 ? "font-bold text-red-600 animate-pulse" :
                              f.security_queue_count > 150 ? "font-bold text-orange-600" :
                              f.security_queue_count > 100 ? "font-bold text-amber-600" : ""
                            }`}>
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
