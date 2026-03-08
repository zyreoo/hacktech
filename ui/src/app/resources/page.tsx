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
import { useResources, useResourceIssues, useUpdateResourceStatus, useReassignFlight } from "@/lib/hooks/queries";
import { getApiErrorMessage } from "@/lib/api/client";
import { resourceStatusVariant } from "@/lib/utils";
import { Layers, AlertTriangle, ShieldCheck, DoorOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

const issueSeverityStyles: Record<string, string> = {
  critical: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 text-red-800 dark:text-red-200",
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
};

export default function ResourcesPage() {
  const { data: resources = [], isLoading, isError, refetch } = useResources({ limit: 200 });
  const { data: issues = [], isLoading: issuesLoading } = useResourceIssues();
  const updateResource = useUpdateResourceStatus();
  const reassignFlightMutation = useReassignFlight();
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [fixError, setFixError] = useState<string | null>(null);

  const resourceTypes = useMemo(
    () => [...new Set(resources.map((r) => r.resource_type))].sort(),
    [resources]
  );

  const filtered = useMemo(
    () =>
      resources.filter((r) => {
        const matchType = filterType === "all" || r.resource_type === filterType;
        const matchStatus = filterStatus === "all" || r.status === filterStatus;
        return matchType && matchStatus;
      }),
    [resources, filterType, filterStatus]
  );

  const summary = useMemo(() => ({
    available:   resources.filter((r) => r.status === "available").length,
    assigned:    resources.filter((r) => r.status === "assigned").length,
    maintenance: resources.filter((r) => r.status === "maintenance").length,
  }), [resources]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header title="Resources" subtitle="Gates, stands, desks, and other operational resources" />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Summary pills */}
        <div className="mb-5 flex flex-wrap gap-3">
          {[
            { label: "Available",   count: summary.available,   color: "text-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 dark:text-emerald-300" },
            { label: "Assigned",    count: summary.assigned,    color: "text-sky-700 bg-sky-50 dark:bg-sky-950/30 dark:text-sky-300" },
            { label: "Maintenance", count: summary.maintenance, color: "text-amber-700 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-300" },
          ].map(({ label, count, color }) => (
            <div key={label} className={`rounded-full px-3 py-1 text-sm font-semibold ${color}`}>
              {count} {label}
            </div>
          ))}
        </div>

        {/* Self-healing & conflicts */}
        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-slate-100">
            <ShieldCheck className="h-4 w-4 text-slate-500" />
            Self-healing & conflicts
          </h2>
          {issuesLoading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/50 px-4 py-3 text-sm text-slate-500">
              Checking for issues…
            </div>
          )}
          {!issuesLoading && issues.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-emerald-50/50 dark:border-slate-700 dark:bg-emerald-950/20 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              No conflicts or self-healing issues detected. Resources are aligned with live flight data.
            </div>
          )}
          {!issuesLoading && issues.length > 0 && (
            <ul className="space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.resource_id ?? issue.resource_name}-${i}`}
                  className={`rounded-xl border px-4 py-3 text-sm ${issueSeverityStyles[issue.severity] ?? "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300"}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {issue.resource_id != null && (
                          <span className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">
                            Resource #{issue.resource_id}
                          </span>
                        )}
                        {issue.flight_id != null && (
                          <Link
                            href={`/command-center?flight=${issue.flight_id}`}
                            className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs underline dark:bg-black/20 hover:opacity-80"
                          >
                            Flight #{issue.flight_id}
                          </Link>
                        )}
                        {issue.flight_code && (
                          <span className="font-mono text-xs opacity-90">{issue.flight_code}</span>
                        )}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {issue.resource_id != null && (
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="shrink-0 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
                            disabled={updateResource.isPending || reassignFlightMutation.isPending}
                            onClick={(e) => {
                              e.preventDefault();
                              setFixError(null);
                              updateResource.mutate(
                                { id: issue.resource_id!, status: "available", assigned_to: null },
                                { onSuccess: () => setFixError(null), onError: (err) => setFixError(getApiErrorMessage(err) || "Failed to release gate") }
                              );
                            }}
                          >
                            {updateResource.isPending ? "Applying…" : "Release gate"}
                          </Button>
                        )}
                        {issue.type === "gate_mismatch" && issue.flight_id != null && issue.resource_name && (
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="shrink-0 border-sky-600 text-sky-700 hover:bg-sky-50 dark:border-sky-500 dark:text-sky-300 dark:hover:bg-sky-950/40"
                            disabled={updateResource.isPending || reassignFlightMutation.isPending}
                            onClick={(e) => {
                              e.preventDefault();
                              setFixError(null);
                              reassignFlightMutation.mutate(
                                { id: issue.flight_id!, gate: issue.resource_name, reconciled_gate: issue.resource_name },
                                { onSuccess: () => setFixError(null), onError: (err) => setFixError(getApiErrorMessage(err) || "Failed to align flight") }
                              );
                            }}
                          >
                            {reassignFlightMutation.isPending ? "Applying…" : "Align flight to this gate"}
                          </Button>
                        )}
                      </div>
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
          <Select value={filterType} onValueChange={(v) => setFilterType(v ?? "all")}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Resource type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {resourceTypes.map((t) => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filterStatus} onValueChange={(v) => setFilterStatus(v ?? "all")}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="available">Available</SelectItem>
              <SelectItem value="assigned">Assigned</SelectItem>
              <SelectItem value="maintenance">Maintenance</SelectItem>
            </SelectContent>
          </Select>

          <span className="ml-auto text-xs text-slate-500">{filtered.length} resources</span>
        </div>

        {isLoading && <TableLoadingState rows={8} />}
        {isError && <ErrorState message="Could not load resources." onRetry={() => refetch()} />}
        {!isLoading && !isError && filtered.length === 0 && (
          <EmptyState icon={Layers} title="No resources" description="No resources match the current filters." />
        )}

        {!isLoading && !isError && filtered.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Assigned To</TableHead>
                  <TableHead>Location</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((r) => (
                  <TableRow key={r.id} className="border-slate-100 dark:border-slate-800">
                    <TableCell className="font-semibold text-slate-800 dark:text-slate-100">{r.resource_name}</TableCell>
                    <TableCell className="text-sm capitalize text-slate-600 dark:text-slate-300">{r.resource_type}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <StatusBadge label={r.status} variant={resourceStatusVariant(r.status)} dot />
                        {r.resource_type === "gate" && r.status === "available" && (
                          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                            <DoorOpen className="h-3 w-3" aria-hidden />
                            Opened
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-sm text-slate-600 dark:text-slate-300">
                      {r.assigned_to ?? <span className="text-slate-400">—</span>}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">{r.location ?? "—"}</TableCell>
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
