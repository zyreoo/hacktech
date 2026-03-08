"use client";

import { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { PredictionOutcomeBadge, StatusBadge } from "@/components/shared/status-badge";
import { TableLoadingState } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usePredictions, usePredictionIssues, useFlights, useRunPrediction } from "@/lib/hooks/queries";
import { formatDateTime, formatConfidence, formatDelay } from "@/lib/utils";
import { BrainCircuit, ShieldCheck, AlertTriangle, Play } from "lucide-react";
import { Button } from "@/components/ui/button";

const issueSeverityStyles: Record<string, string> = {
  critical: "border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 text-red-800 dark:text-red-200",
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
  low: "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300",
};

export default function PredictionsPage() {
  const { data: predictions = [], isLoading, isError, refetch } = usePredictions({ limit: 200 });
  const { data: issues = [], isLoading: issuesLoading } = usePredictionIssues({ limit: 200 });
  const { data: flights = [] } = useFlights({ limit: 50 });
  const runPredictionMutation = useRunPrediction();
  const [selectedFlightId, setSelectedFlightId] = useState<string>("");
  const activeFlights = Array.isArray(flights) ? flights.filter((f) => f.status && !["cancelled", "departed", "arrived"].includes(f.status)) : [];

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header
        title="Prediction Audit"
        subtitle="Full audit trail of all AI arrival delay predictions"
      />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Run prediction – see it work */}
        <section className="mb-6 rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-900/50">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-slate-100">
            <Play className="h-4 w-4 text-sky-500" />
            Run prediction
          </h2>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
            Run arrival delay prediction for a flight. The new prediction will appear in the audit table below.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Select value={selectedFlightId} onValueChange={setSelectedFlightId}>
              <SelectTrigger className="w-56">
                <SelectValue placeholder="Select flight" />
              </SelectTrigger>
              <SelectContent>
                {activeFlights.slice(0, 15).map((f) => (
                  <SelectItem key={f.id} value={String(f.id)}>
                    {f.flight_code} ({f.origin} → {f.destination})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="button"
              size="sm"
              disabled={!selectedFlightId || runPredictionMutation.isPending}
              onClick={() => {
                const id = parseInt(selectedFlightId, 10);
                if (!Number.isNaN(id)) runPredictionMutation.mutate({ flight_id: id });
              }}
            >
              {runPredictionMutation.isPending ? "Running…" : "Run prediction"}
            </Button>
            {runPredictionMutation.isSuccess && (
              <span className="text-sm text-emerald-600 dark:text-emerald-400">Prediction saved. Check the table below.</span>
            )}
            {runPredictionMutation.isError && (
              <span className="text-sm text-red-600 dark:text-red-400">
                {runPredictionMutation.error instanceof Error ? runPredictionMutation.error.message : "Run failed"}
              </span>
            )}
          </div>
        </section>

        {/* Self-healing & quality */}
        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-slate-100">
            <ShieldCheck className="h-4 w-4 text-slate-500" />
            Self-healing & quality
          </h2>
          {issuesLoading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/50 px-4 py-3 text-sm text-slate-500">
              Checking for issues…
            </div>
          )}
          {!issuesLoading && issues.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-emerald-50/50 dark:border-slate-700 dark:bg-emerald-950/20 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              No prediction quality issues. Stale, low-confidence, and fallback predictions are within expected range.
            </div>
          )}
          {!issuesLoading && issues.length > 0 && (
            <ul className="mb-6 space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.prediction_id}-${i}`}
                  className={`rounded-xl border px-4 py-3 text-sm ${issueSeverityStyles[issue.severity] ?? issueSeverityStyles.low}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Link
                          href={`/flights/${issue.flight_id}`}
                          className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs underline dark:bg-black/20 hover:opacity-80"
                        >
                          Flight #{issue.flight_id}
                        </Link>
                        <span className="rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">
                          Prediction #{issue.prediction_id}
                        </span>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {isLoading && <TableLoadingState rows={10} />}
        {isError && (
          <ErrorState message="Could not load predictions." onRetry={() => refetch()} />
        )}

        {!isLoading && !isError && predictions.length === 0 && (
          <EmptyState
            icon={BrainCircuit}
            title="No predictions yet"
            description="Run a prediction from a flight detail page to populate the audit trail."
          />
        )}

        {!isLoading && !isError && predictions.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Flight</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Delay</TableHead>
                  <TableHead>Predicted ETA</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>Input Quality</TableHead>
                  <TableHead>Missing Features</TableHead>
                  <TableHead>Stale Warnings</TableHead>
                  <TableHead>Model</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {predictions.map((p) => (
                  <TableRow key={p.id} className="border-slate-100 dark:border-slate-800">
                    <TableCell>
                      <Link
                        href={`/flights/${p.flight_id}`}
                        className="font-mono font-semibold text-sky-600 hover:underline dark:text-sky-400"
                      >
                        #{p.flight_id}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatDateTime(p.prediction_timestamp)}
                    </TableCell>
                    <TableCell>
                      <span className={`font-mono text-sm font-semibold ${
                        p.predicted_arrival_delay_min > 30 ? "text-red-600" :
                        p.predicted_arrival_delay_min > 15 ? "text-amber-600" : "text-emerald-600"
                      }`}>
                        {formatDelay(p.predicted_arrival_delay_min)}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatDateTime(p.predicted_arrival_time)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {formatConfidence(p.confidence_score)}
                    </TableCell>
                    <TableCell>
                      <PredictionOutcomeBadge outcome={p.prediction_outcome} />
                    </TableCell>
                    <TableCell>
                      {p.input_quality_score != null ? (
                        <div className="flex items-center gap-1.5">
                          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                            <div
                              className={`h-1.5 rounded-full ${
                                p.input_quality_score > 0.7 ? "bg-emerald-500" :
                                p.input_quality_score > 0.4 ? "bg-amber-500" : "bg-red-500"
                              }`}
                              style={{ width: `${p.input_quality_score * 100}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs">
                            {(p.input_quality_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {p.missing_features && p.missing_features.length > 0 ? (
                        <div className="flex flex-wrap gap-0.5">
                          {p.missing_features.map((f) => (
                            <StatusBadge key={f} label={f} variant="warning" />
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-emerald-600">None</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {p.stale_data_warnings && p.stale_data_warnings.length > 0 ? (
                        <StatusBadge label={`${p.stale_data_warnings.length} warning${p.stale_data_warnings.length > 1 ? "s" : ""}`} variant="warning" />
                      ) : (
                        <span className="text-xs text-emerald-600">None</span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-400">{p.model_version}</TableCell>
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
