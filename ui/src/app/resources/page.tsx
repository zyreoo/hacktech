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
import { useResources } from "@/lib/hooks/queries";
import { resourceStatusVariant } from "@/lib/utils";
import { Layers } from "lucide-react";

export default function ResourcesPage() {
  const { data: resources = [], isLoading, isError, refetch } = useResources({ limit: 200 });
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

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
                      <StatusBadge label={r.status} variant={resourceStatusVariant(r.status)} dot />
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
