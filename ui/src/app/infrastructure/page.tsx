"use client";

import { useMemo } from "react";
import { Header } from "@/components/layout/header";
import { StatusBadge } from "@/components/shared/status-badge";
import { MetricCard } from "@/components/shared/metric-card";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useInfrastructure } from "@/lib/hooks/queries";
import { formatDateTime, infraStatusVariant } from "@/lib/utils";
import { Cpu, ShieldAlert, Wifi, AlertTriangle } from "lucide-react";

export default function InfrastructurePage() {
  const { data: assets = [], isLoading, isError, refetch } = useInfrastructure();

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
