"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { StatusBadge } from "@/components/shared/status-badge";
import { TableLoadingState } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAlerts, useAlertIssues, useResolveAlert } from "@/lib/hooks/queries";
import { Button } from "@/components/ui/button";
import { formatRelativeTime, alertSeverityVariant } from "@/lib/utils";
import { Bell, ShieldCheck, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

const issueSeverityStyles: Record<string, string> = {
  critical: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 text-red-800 dark:text-red-200",
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
  low: "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300",
};

const SEVERITY_ROWS: Record<string, string> = {
  critical: "bg-red-50/50 dark:bg-red-950/20",
  warning:  "bg-amber-50/30 dark:bg-amber-950/10",
  info:     "",
};

/** Fallback suggested actions when API does not return suggested_action (e.g. cache). */
const SUGGESTED_ACTION_BY_TYPE: Record<string, string> = {
  queue: "Deploy extra security lanes or redirect passengers to reduce queue depth; monitor wait times.",
  runway_hazard: "Inspect runway and clear hazard; consider temporary closure until cleared.",
  grip: "Schedule runway surface treatment or restrict operations until grip improves.",
  security: "Verify asset integrity and secure area; escalate to security if tamper confirmed.",
  gate_conflict: "Reassign gate for one of the flights or adjust schedule to resolve overlap.",
};

function getSuggestedAction(alert: { alert_type: string; suggested_action?: string | null }): string | null {
  return alert.suggested_action ?? SUGGESTED_ACTION_BY_TYPE[alert.alert_type] ?? null;
}

export default function AlertsPage() {
  const [showResolved, setShowResolved] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [filterType, setFilterType] = useState("all");

  const { data: alerts = [], isLoading, isError, refetch } = useAlerts({
    resolved: showResolved ? undefined : false,
    limit: 200,
  });
  const { data: issues = [], isLoading: issuesLoading } = useAlertIssues({ limit: 300 });
  const resolveAlertMutation = useResolveAlert();
  const [fixError, setFixError] = useState<string | null>(null);

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
          {!issuesLoading && issues.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-emerald-50/50 dark:border-slate-700 dark:bg-emerald-950/20 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              No alert data quality issues. No stale critical, orphan references, or duplicate unresolved alerts.
            </div>
          )}
          {!issuesLoading && issues.length > 0 && (
            <ul className="mb-6 space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.alert_id}-${i}`}
                  className={cn(
                    "rounded-xl border px-4 py-3 text-sm",
                    issueSeverityStyles[issue.severity] ?? issueSeverityStyles.low
                  )}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Link
                          href={`/alerts?highlight=${issue.alert_id}`}
                          className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs underline dark:bg-black/20 hover:opacity-80"
                        >
                          Alert #{issue.alert_id}
                        </Link>
                        {issue.related_entity_type && issue.related_entity_id && (
                          <span className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">
                            {issue.related_entity_type} {issue.related_entity_id}
                          </span>
                        )}
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="mt-2 shrink-0 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
                        disabled={resolveAlertMutation.isPending}
                        onClick={(e) => {
                          e.preventDefault();
                          setFixError(null);
                          resolveAlertMutation.mutate(
                            { id: issue.alert_id, resolved: true },
                            { onError: (err) => setFixError(err instanceof Error ? err.message : "Failed to resolve alert") }
                          );
                        }}
                      >
                        {resolveAlertMutation.isPending ? "Applying…" : "Resolve alert"}
                      </Button>
                      {fixError && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{fixError}</p>}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

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
                  <TableHead className="min-w-[200px]">Message</TableHead>
                  <TableHead className="min-w-[220px]">Suggested action</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Source</TableHead>
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
                    <TableCell className="min-w-[200px] text-sm text-slate-700 dark:text-slate-300">
                      {alert.message}
                    </TableCell>
                    <TableCell className="min-w-[220px]">
                      {(() => {
                        const action = getSuggestedAction(alert);
                        return action ? (
                          <span className="block rounded-md bg-slate-100 px-2 py-1.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                            {action}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        );
                      })()}
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
