import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PredictionOutcomeBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { formatDateTime, formatConfidence, formatDelay } from "@/lib/utils";
import type { PredictionAudit } from "@/types/api";
import { BrainCircuit } from "lucide-react";

export function PredictionHistory({ records }: { records: PredictionAudit[] }) {
  if (records.length === 0) {
    return (
      <EmptyState
        icon={BrainCircuit}
        title="No prediction history"
        description="Run a prediction to start the audit trail."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp</TableHead>
            <TableHead>Delay</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Outcome</TableHead>
            <TableHead>Quality</TableHead>
            <TableHead>Model</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {records.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="font-mono text-xs">{formatDateTime(r.prediction_timestamp)}</TableCell>
              <TableCell>
                <span className={`font-mono text-sm font-semibold ${
                  r.predicted_arrival_delay_min > 30 ? "text-red-600" :
                  r.predicted_arrival_delay_min > 15 ? "text-amber-600" : "text-emerald-600"
                }`}>
                  {formatDelay(r.predicted_arrival_delay_min)}
                </span>
              </TableCell>
              <TableCell className="font-mono text-sm">{formatConfidence(r.confidence_score)}</TableCell>
              <TableCell>
                <PredictionOutcomeBadge outcome={r.prediction_outcome} />
              </TableCell>
              <TableCell className="font-mono text-xs">
                {r.input_quality_score != null ? `${(r.input_quality_score * 100).toFixed(0)}%` : "—"}
              </TableCell>
              <TableCell className="font-mono text-xs text-slate-500">{r.model_version}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
