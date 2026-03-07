"use client";

import { Header } from "@/components/layout/header";
import { StatusBadge } from "@/components/shared/status-badge";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import { useRunways } from "@/lib/hooks/queries";
import { formatDateTime, formatGripScore, runwayStatusVariant } from "@/lib/utils";
import { Wind, AlertTriangle, CheckCircle2 } from "lucide-react";

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

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header title="Runways" subtitle="Runway status, surface conditions, and hazard detection" />
      <main className="flex-1 overflow-y-auto p-6">
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
