import { StatusBadge, RawBadge, ReconciledBadge } from "@/components/shared/status-badge";
import { formatDateTime, formatConfidence, flightStatusVariant } from "@/lib/utils";
import type { Flight } from "@/types/api";

interface FieldRowProps {
  label: string;
  value: React.ReactNode;
}

function FieldRow({ label, value }: FieldRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="min-w-[160px] text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-right text-sm text-slate-800 dark:text-slate-100">{value ?? "—"}</span>
    </div>
  );
}

export function FlightInfoPanel({ flight }: { flight: Flight }) {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Raw data */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-3 flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Source Data</h3>
          <RawBadge />
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          <FieldRow label="Flight Code" value={<span className="font-mono font-bold">{flight.flight_code}</span>} />
          <FieldRow label="Airline" value={flight.airline} />
          <FieldRow label="Origin" value={flight.origin} />
          <FieldRow label="Destination" value={flight.destination} />
          <FieldRow label="Scheduled" value={formatDateTime(flight.scheduled_time)} />
          <FieldRow label="Estimated" value={formatDateTime(flight.estimated_time)} />
          <FieldRow
            label="Status"
            value={
              <StatusBadge label={flight.status} variant={flightStatusVariant(flight.status)} />
            }
          />
          <FieldRow label="Gate" value={flight.gate} />
          <FieldRow label="Stand" value={flight.stand} />
        </div>
      </div>

      {/* Reconciled data */}
      <div className="rounded-xl border border-sky-200 bg-white p-5 dark:border-sky-800/60 dark:bg-slate-900">
        <div className="mb-3 flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Reconciled Data</h3>
          <ReconciledBadge />
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          <FieldRow
            label="Reconciled Status"
            value={
              flight.reconciled_status ? (
                <StatusBadge
                  label={flight.reconciled_status}
                  variant={flightStatusVariant(flight.reconciled_status)}
                />
              ) : null
            }
          />
          <FieldRow label="Reconciled ETA" value={formatDateTime(flight.reconciled_eta)} />
          <FieldRow label="Reconciled Gate" value={<span className="font-mono">{flight.reconciled_gate ?? "—"}</span>} />
          <FieldRow
            label="Confidence"
            value={
              <span className={`font-semibold ${
                (flight.reconciliation_confidence ?? 0) > 0.7 ? "text-emerald-600" : "text-amber-600"
              }`}>
                {formatConfidence(flight.reconciliation_confidence)}
              </span>
            }
          />
          <FieldRow label="Reason" value={
            flight.reconciliation_reason ? (
              <span className="max-w-[200px] text-xs leading-relaxed">{flight.reconciliation_reason}</span>
            ) : null
          } />
          <FieldRow label="Last Reconciled" value={formatDateTime(flight.last_reconciled_at)} />
        </div>
      </div>

      {/* Prediction data */}
      <div className="rounded-xl border border-violet-200 bg-white p-5 dark:border-violet-800/60 dark:bg-slate-900">
        <div className="mb-3 flex items-center gap-2">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">AI Prediction</h3>
          <StatusBadge label="Predicted" variant="purple" />
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          <FieldRow label="Predicted ETA" value={formatDateTime(flight.predicted_eta)} />
          <FieldRow
            label="Delay Prediction"
            value={
              flight.predicted_arrival_delay_min != null ? (
                <span className={`font-mono font-bold ${
                  flight.predicted_arrival_delay_min > 30 ? "text-red-600" :
                  flight.predicted_arrival_delay_min > 15 ? "text-amber-600" : "text-emerald-600"
                }`}>
                  {flight.predicted_arrival_delay_min >= 0 ? "+" : ""}
                  {Math.round(flight.predicted_arrival_delay_min)} min
                </span>
              ) : null
            }
          />
          <FieldRow
            label="Confidence"
            value={
              <span className={`font-semibold ${
                (flight.prediction_confidence ?? 0) > 0.6 ? "text-emerald-600" : "text-amber-600"
              }`}>
                {formatConfidence(flight.prediction_confidence)}
              </span>
            }
          />
          <FieldRow label="Model Version" value={<span className="font-mono text-xs">{flight.prediction_model_version ?? "—"}</span>} />
          <FieldRow label="Last Predicted" value={formatDateTime(flight.last_prediction_at)} />
        </div>
      </div>
    </div>
  );
}
