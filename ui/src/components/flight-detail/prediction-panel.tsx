"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PredictionOutcomeBadge, StatusBadge } from "@/components/shared/status-badge";
import { useRunPrediction } from "@/lib/hooks/queries";
import { formatDateTime, formatConfidence } from "@/lib/utils";
import type { PredictResponse } from "@/types/api";
import { BrainCircuit, Loader2, AlertTriangle } from "lucide-react";

interface PredictionPanelProps {
  flightId: number;
}

export function PredictionPanel({ flightId }: PredictionPanelProps) {
  const mutation = useRunPrediction();
  const [result, setResult] = useState<PredictResponse | null>(null);

  const handleRun = async () => {
    const res = await mutation.mutateAsync({ flight_id: flightId });
    setResult(res);
  };

  return (
    <div className="rounded-xl border border-violet-200 bg-white p-5 dark:border-violet-800/60 dark:bg-slate-900">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-5 w-5 text-violet-500" />
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Run Prediction</h3>
        </div>
        <Button
          onClick={handleRun}
          disabled={mutation.isPending}
          className="bg-violet-600 text-white hover:bg-violet-700"
          size="sm"
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Running…
            </>
          ) : (
            <>
              <BrainCircuit className="mr-2 h-4 w-4" />
              Run Prediction
            </>
          )}
        </Button>
      </div>

      {mutation.isError && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Prediction failed. Check the backend.
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Summary row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-violet-50 p-3 text-center dark:bg-violet-950/30">
              <p className="text-xs text-slate-500">Delay Prediction</p>
              <p className={`mt-1 text-xl font-bold ${
                result.predicted_arrival_delay_min > 30 ? "text-red-600" :
                result.predicted_arrival_delay_min > 15 ? "text-amber-600" : "text-emerald-600"
              }`}>
                {result.predicted_arrival_delay_min >= 0 ? "+" : ""}
                {Math.round(result.predicted_arrival_delay_min)} min
              </p>
            </div>
            <div className="rounded-lg bg-violet-50 p-3 text-center dark:bg-violet-950/30">
              <p className="text-xs text-slate-500">Confidence</p>
              <p className="mt-1 text-xl font-bold text-violet-700 dark:text-violet-300">
                {formatConfidence(result.confidence_score)}
              </p>
            </div>
            <div className="rounded-lg bg-violet-50 p-3 text-center dark:bg-violet-950/30">
              <p className="text-xs text-slate-500">Outcome</p>
              <div className="mt-1 flex justify-center">
                <PredictionOutcomeBadge outcome={result.prediction_outcome} />
              </div>
            </div>
          </div>

          {/* Predicted arrival */}
          {result.predicted_arrival_time && (
            <p className="text-xs text-slate-500">
              Predicted arrival: <span className="font-semibold text-slate-800 dark:text-slate-100">{formatDateTime(result.predicted_arrival_time)}</span>
            </p>
          )}

          {/* Quality warnings */}
          {result.missing_features.length > 0 && (
            <div className="rounded-lg bg-amber-50 p-3 dark:bg-amber-950/30">
              <p className="text-xs font-semibold text-amber-700 dark:text-amber-300">Missing Features</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {result.missing_features.map((f) => (
                  <StatusBadge key={f} label={f} variant="warning" />
                ))}
              </div>
            </div>
          )}

          {result.stale_data_warnings.length > 0 && (
            <div className="rounded-lg bg-amber-50 p-3 dark:bg-amber-950/30">
              <p className="text-xs font-semibold text-amber-700 dark:text-amber-300">Stale Data Warnings</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-amber-700 dark:text-amber-300">
                {result.stale_data_warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}

          {/* Operational reason codes */}
          {result.operational_reason_codes && result.operational_reason_codes.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Operational Drivers
              </p>
              <div className="space-y-1.5">
                {result.operational_reason_codes.map((rc, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50">
                    <div>
                      <span className="font-mono text-xs font-semibold text-slate-700 dark:text-slate-200">
                        {rc.operational_code}
                      </span>
                      <p className="text-xs text-slate-500">{rc.operational_phrase}</p>
                    </div>
                    <span className="font-mono text-xs text-slate-400">
                      {(rc.contribution * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-slate-400">
            Ran at {formatDateTime(result.prediction_timestamp)} · {result.model_version}
          </p>
        </div>
      )}
    </div>
  );
}
