"use client";

import { Header } from "@/components/layout/header";
import { PredictionOutcomeBadge, StatusBadge } from "@/components/shared/status-badge";
import { TableLoadingState } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { usePredictions } from "@/lib/hooks/queries";
import { formatDateTime, formatConfidence, formatDelay } from "@/lib/utils";
import { BrainCircuit } from "lucide-react";
import Link from "next/link";

export default function PredictionsPage() {
  const { data: predictions = [], isLoading, isError, refetch } = usePredictions({ limit: 200 });

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header
        title="Prediction Audit"
        subtitle="Full audit trail of all AI arrival delay predictions"
      />
      <main className="flex-1 overflow-y-auto p-6">
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
