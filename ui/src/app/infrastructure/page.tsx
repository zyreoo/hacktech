"use client";

import { useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { StatusBadge } from "@/components/shared/status-badge";
import { MetricCard } from "@/components/shared/metric-card";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useInfrastructure, useInfrastructureIssues, useUpdateInfrastructureStatus } from "@/lib/hooks/queries";
import { formatDateTime, infraStatusVariant } from "@/lib/utils";
import { Cpu, ShieldAlert, Wifi, AlertTriangle, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

const issueSeverityStyles: Record<string, string> = {
  critical: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 text-red-800 dark:text-red-200",
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
};

export default function InfrastructurePage() {
  const { data: assets = [], isLoading, isError, refetch } = useInfrastructure();
  const { data: issues = [], isLoading: issuesLoading } = useInfrastructureIssues();
  const updateInfra = useUpdateInfrastructureStatus();
  const [fixError, setFixError] = useState<string | null>(null);

  const stats = useMemo(() => ({
    total:       assets.length,
    operational: assets.filter((a) => a.status === "operational").length,
    degraded:    assets.filter((a) => a.status === "degraded").length,
    offline:     assets.filter((a) => a.status === "offline").length,
    tamper:      assets.filter((a) => a.tamper_detected).length,
  }), [assets]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header title="Infrastructure" subtitle="Asset health, network status, and security monitoring" />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Self-healing */}
        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-slate-100">
            <ShieldCheck className="h-4 w-4 text-slate-500" />
            Self-healing
          </h2>
          {issuesLoading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/50 px-4 py-3 text-sm text-slate-500">
              Checking for issues…
            </div>
          )}
          {!issuesLoading && issues.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-emerald-50/50 dark:border-slate-700 dark:bg-emerald-950/20 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              No infrastructure issues. All assets operational, no tamper flags.
            </div>
          )}
          {!issuesLoading && issues.length > 0 && (
            <ul className="mb-6 space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.asset_id}-${i}`}
                  className={`rounded-xl border px-4 py-3 text-sm ${issueSeverityStyles[issue.severity] ?? "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50"}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 min-w-0 flex-1">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                      <div>
                        <p className="font-medium">{issue.message}</p>
                        <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                        <span className="mt-2 inline-block rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">{issue.asset_name}</span>
                      </div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      {issue.type === "tamper_detected" && (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300"
                          disabled={updateInfra.isPending}
                          onClick={() => {
                            setFixError(null);
                            updateInfra.mutate(
                              { id: issue.asset_id, status: "operational", tamper_detected: false },
                              { onError: (err) => setFixError(err instanceof Error ? err.message : "Failed") }
                            );
                          }}
                        >
                          {updateInfra.isPending ? "Applying…" : "Clear tamper"}
                        </Button>
                      )}
                      {issue.type === "asset_unhealthy" && (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="border-sky-600 text-sky-700 hover:bg-sky-50 dark:border-sky-500 dark:text-sky-300"
                          disabled={updateInfra.isPending}
                          onClick={() => {
                            setFixError(null);
                            updateInfra.mutate(
                              { id: issue.asset_id, status: "operational" },
                              { onError: (err) => setFixError(err instanceof Error ? err.message : "Failed") }
                            );
                          }}
                        >
                          {updateInfra.isPending ? "Applying…" : "Set operational"}
                        </Button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {fixError && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{fixError}</p>}
        </section>

        {isLoading && <SpinnerLoader />}
        {isError && <ErrorState message="Could not load infrastructure data." onRetry={() => refetch()} />}
        {!isLoading && !isError && assets.length === 0 && (
          <EmptyState icon={Cpu} title="No assets" description="No infrastructure assets found." />
        )}

        {assets.length > 0 && (
          <div className="space-y-6">
            {/* KPIs */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <MetricCard title="Total Assets" value={stats.total} icon={Cpu} />
              <MetricCard title="Operational" value={stats.operational} icon={Cpu} highlight="success" />
              <MetricCard
                title="Degraded / Offline"
                value={stats.degraded + stats.offline}
                icon={AlertTriangle}
                highlight={stats.degraded + stats.offline > 0 ? "warning" : "default"}
              />
              <MetricCard
                title="Tamper Flags"
                value={stats.tamper}
                icon={ShieldAlert}
                highlight={stats.tamper > 0 ? "danger" : "default"}
              />
            </div>

            <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Asset</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Network Health</TableHead>
                    <TableHead>Tamper</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Last Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assets.map((a) => (
                    <TableRow
                      key={a.id}
                      className={`border-slate-100 dark:border-slate-800 ${
                        a.tamper_detected ? "bg-red-50/50 dark:bg-red-950/20" : ""
                      }`}
                    >
                      <TableCell className="font-semibold text-slate-800 dark:text-slate-100">{a.asset_name}</TableCell>
                      <TableCell className="text-sm capitalize text-slate-600 dark:text-slate-300">{a.asset_type}</TableCell>
                      <TableCell>
                        <StatusBadge label={a.status} variant={infraStatusVariant(a.status)} dot />
                      </TableCell>
                      <TableCell>
                        {a.network_health != null ? (
                          <div className="flex items-center gap-2">
                            <Wifi className={`h-3.5 w-3.5 ${
                              a.network_health > 0.7 ? "text-emerald-500" :
                              a.network_health > 0.4 ? "text-amber-500" : "text-red-500"
                            }`} />
                            <span className="font-mono text-xs">
                              {(a.network_health * 100).toFixed(0)}%
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {a.tamper_detected ? (
                          <div className="flex items-center gap-1 text-red-600 dark:text-red-400">
                            <ShieldAlert className="h-4 w-4" />
                            <span className="text-xs font-semibold">TAMPER</span>
                          </div>
                        ) : (
                          <span className="text-xs text-emerald-600">Clear</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-slate-500">{a.location ?? "—"}</TableCell>
                      <TableCell className="text-xs text-slate-400">{formatDateTime(a.last_updated)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
