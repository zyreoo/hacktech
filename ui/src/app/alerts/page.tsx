"use client";

import { useState, useMemo } from "react";
import { Header } from "@/components/layout/header";
import { StatusBadge } from "@/components/shared/status-badge";
import { TableLoadingState } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAlerts } from "@/lib/hooks/queries";
import { formatRelativeTime, alertSeverityVariant } from "@/lib/utils";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";

const SEVERITY_ROWS: Record<string, string> = {
  critical: "bg-red-50/50 dark:bg-red-950/20",
  warning:  "bg-amber-50/30 dark:bg-amber-950/10",
  info:     "",
};

export default function AlertsPage() {
  const [showResolved, setShowResolved] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [filterType, setFilterType] = useState("all");

  const { data: alerts = [], isLoading, isError, refetch } = useAlerts({
    resolved: showResolved ? undefined : false,
    limit: 200,
  });

  const alertTypes = useMemo(() => [...new Set(alerts.map((a) => a.alert_type))].sort(), [alerts]);

  const filtered = useMemo(() =>
    alerts.filter((a) => {
      const matchSev = filterSeverity === "all" || a.severity === filterSeverity;
      const matchType = filterType === "all" || a.alert_type === filterType;
      return matchSev && matchType;
    }),
  [alerts, filterSeverity, filterType]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header title="Alerts" subtitle="Active operational alerts and notifications" />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Filters */}
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <Select value={filterSeverity} onValueChange={(v) => setFilterSeverity(v ?? "all")}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
              <SelectItem value="info">Info</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterType} onValueChange={(v) => setFilterType(v ?? "all")}>
            <SelectTrigger className="w-52">
              <SelectValue placeholder="Alert Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {alertTypes.map((t) => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={showResolved}
              onChange={(e) => setShowResolved(e.target.checked)}
              className="rounded"
            />
            Show resolved
          </label>

          <span className="ml-auto text-xs text-slate-500">
            {filtered.length} alert{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>

        {isLoading && <TableLoadingState rows={8} />}
        {isError && <ErrorState message="Could not load alerts." onRetry={() => refetch()} />}

        {!isLoading && !isError && filtered.length === 0 && (
          <EmptyState icon={Bell} title="No alerts" description="No alerts match the current filters." />
        )}

        {!isLoading && !isError && filtered.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="max-w-sm">Message</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>State</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((alert) => (
                  <TableRow
                    key={alert.id}
                    className={cn(
                      SEVERITY_ROWS[alert.severity],
                      "border-slate-100 dark:border-slate-800"
                    )}
                  >
                    <TableCell>
                      <StatusBadge
                        label={alert.severity}
                        variant={alertSeverityVariant(alert.severity)}
                        dot
                      />
                    </TableCell>
                    <TableCell className="font-mono text-xs">{alert.alert_type}</TableCell>
                    <TableCell className="max-w-sm text-sm text-slate-700 dark:text-slate-300">
                      {alert.message}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {alert.related_entity_type && (
                        <>
                          <span className="font-medium">{alert.related_entity_type}</span>{" "}
                          {alert.related_entity_id}
                        </>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">{alert.source_module ?? "—"}</TableCell>
                    <TableCell className="max-w-[140px] truncate font-mono text-xs text-slate-400">
                      {alert.uniqueness_key ?? "—"}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {formatRelativeTime(alert.created_at)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge
                        label={alert.resolved ? "Resolved" : "Active"}
                        variant={alert.resolved ? "success" : "warning"}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </main>
    </div>
  );
}
