"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import { StatusBadge } from "@/components/shared/status-badge";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import { useRunways, useRunwayIssues, useUpdateRunwayStatus, useUpdateRunwayHazard, useReassignFlight } from "@/lib/hooks/queries";
import { Button } from "@/components/ui/button";
import { formatDateTime, formatGripScore, runwayStatusVariant } from "@/lib/utils";
import { Wind, AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react";

const issueSeverityStyles: Record<string, string> = {
  critical: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 text-red-800 dark:text-red-200",
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
};

function GripBar({ score }: { score: number | null }) {
  if (score == null) return <span className="text-xs text-slate-400">—</span>;
  const pct = score * 100;
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`font-mono text-sm font-bold ${color.replace("bg-", "text-")}`}>
        {formatGripScore(score)}
      </span>
    </div>
  );
}

export default function RunwaysPage() {
  const { data: runways = [], isLoading, isError, refetch } = useRunways();
  const { data: issues = [], isLoading: issuesLoading } = useRunwayIssues();
  const updateRunwayStatus = useUpdateRunwayStatus();
  const updateRunwayHazard = useUpdateRunwayHazard();
  const reassignFlightMutation = useReassignFlight();
  const activeRunwayId = runways.find((r) => r.status === "active")?.id ?? null;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header title="Runways" subtitle="Runway status, surface conditions, and hazard detection" />
      <main className="flex-1 overflow-y-auto p-6">
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
              No conflicts or self-healing issues. Runways are aligned with flight assignments.
            </div>
          )}
          {!issuesLoading && issues.length > 0 && (
            <ul className="mb-6 space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.runway_id}-${i}`}
                  className={`rounded-xl border px-4 py-3 text-sm ${issueSeverityStyles[issue.severity] ?? "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300"}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <span className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">
                          {issue.runway_code}
                        </span>
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
                      {issue.type === "hazard_active_runway" && issue.runway_id != null && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="mt-2 shrink-0 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
                          disabled={updateRunwayHazard.isPending}
                          onClick={() => updateRunwayHazard.mutate({ id: issue.runway_id!, hazard_detected: false, hazard_type: null })}
                        >
                          {updateRunwayHazard.isPending ? "Applying…" : "Clear hazard"}
                        </Button>
                      )}
                      {issue.type === "runway_unavailable_assigned" && issue.flight_id != null && activeRunwayId != null && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="mt-2 shrink-0 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-950/40"
                          disabled={reassignFlightMutation.isPending}
                          onClick={() => reassignFlightMutation.mutate({ id: issue.flight_id!, runway_id: activeRunwayId })}
                        >
                          {reassignFlightMutation.isPending ? "Applying…" : "Reassign to active runway"}
                        </Button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {isLoading && <SpinnerLoader />}
        {isError && <ErrorState message="Could not load runways." onRetry={() => refetch()} />}
        {!isLoading && !isError && runways.length === 0 && (
          <EmptyState icon={Wind} title="No runways" description="No runway data available." />
        )}

        {runways.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {runways.map((r) => (
              <div
                key={r.id}
                className={`rounded-xl border bg-white p-5 shadow-sm dark:bg-slate-900 ${
                  r.hazard_detected
                    ? "border-l-4 border-l-red-500 border-red-200 dark:border-red-800"
                    : r.status === "closed"
                    ? "border-l-4 border-l-slate-500 border-slate-200 dark:border-slate-700"
                    : "border-slate-200 dark:border-slate-700"
                }`}
              >
                {/* Header */}
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wind className="h-5 w-5 text-slate-400" />
                    <span className="font-mono text-lg font-bold text-slate-900 dark:text-slate-100">
                      {r.runway_code}
                    </span>
                  </div>
                  <StatusBadge label={r.status} variant={runwayStatusVariant(r.status)} dot />
                </div>

                {/* Hazard alert */}
                {r.hazard_detected && (
                  <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    {r.hazard_type ?? "Hazard detected"}
                  </div>
                )}

                {!r.hazard_detected && r.status === "active" && (
                  <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
                    <CheckCircle2 className="h-4 w-4" />
                    Clear — no hazards
                  </div>
                )}

                {/* Stats grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-slate-500">Surface</p>
                    <p className="font-semibold capitalize text-slate-800 dark:text-slate-100">
                      {r.surface_condition ?? "Unknown"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Contamination</p>
                    <p className="font-semibold text-slate-800 dark:text-slate-100">
                      {r.contamination_level != null
                        ? `${(r.contamination_level * 100).toFixed(0)}%`
                        : "—"}
                    </p>
                  </div>
                </div>

                <div className="mt-3">
                  <p className="mb-1 text-xs text-slate-500">Grip Score</p>
                  <GripBar score={r.grip_score} />
                </div>

                {r.last_inspection_time && (
                  <p className="mt-3 text-xs text-slate-400">
                    Last inspected: {formatDateTime(r.last_inspection_time)}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
