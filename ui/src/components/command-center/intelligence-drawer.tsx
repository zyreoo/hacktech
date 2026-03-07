"use client";

import { ScrollArea } from "@/components/modern-ui/scroll-area";
import {
  StatusBadge,
  RawBadge,
  ReconciledBadge,
  PredictedBadge,
} from "@/components/shared/status-badge";
import {
  formatDateTime,
  formatConfidence,
  formatDelay,
  flightStatusVariant,
  runwayStatusVariant,
  infraStatusVariant,
} from "@/lib/utils";
import { SeverityBadge } from "./severity-badge";
import type {
  Flight,
  Alert,
  Runway,
  InfrastructureAsset,
  Resource,
} from "@/types/api";
import {
  hasReconciliationMismatch,
  type ResolutionStatus,
  type SelfHealingIssue,
  type RecommendedAction,
} from "@/lib/command-center/selectors";
import type { OperationalImpact } from "@/lib/command-center/impact-selectors";
import { OperationalImpactPanel } from "./operational-impact-panel";
import { cn } from "@/lib/utils";

export type DrawerSubject =
  | { type: "flight"; data: Flight }
  | { type: "alert"; data: Alert }
  | { type: "runway"; data: Runway }
  | { type: "infrastructure"; data: InfrastructureAsset }
  | { type: "resource"; data: Resource }
  | null;

interface IntelligenceDrawerProps {
  subject: DrawerSubject;
  onClose?: () => void;
  resolutionStatus?: ResolutionStatus;
  onResolutionChange?: (status: ResolutionStatus) => void;
  selfHealingIssue?: SelfHealingIssue | null;
  recommendedActions?: RecommendedAction[];
  operationalImpact?: OperationalImpact | null;
  className?: string;
}

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/50 py-2 text-sm">
      <span className="min-w-[120px] text-xs font-medium text-muted-foreground">{label}</span>
      <span className="text-right text-xs text-foreground">{value ?? "—"}</span>
    </div>
  );
}

export function IntelligenceDrawer({
  subject,
  onClose,
  resolutionStatus,
  onResolutionChange,
  selfHealingIssue,
  recommendedActions = [],
  operationalImpact = null,
  className,
}: IntelligenceDrawerProps) {
  if (!subject || !("data" in subject) || subject.data == null) {
    return (
      <div
        className={cn(
          "flex w-80 shrink-0 flex-col items-center justify-center rounded-xl border border-border bg-card p-8 text-center",
          className
        )}
      >
        <p className="text-sm text-muted-foreground">Select a flight, alert, runway, or asset</p>
        <p className="mt-1 text-xs text-muted-foreground">Click on the map or list</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex w-80 shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Detail
          </h3>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Close"
            >
              ×
            </button>
          )}
        </div>
        <p className="mt-1 text-sm font-semibold text-foreground">
          {subject.type === "flight" && subject.data.flight_code}
          {subject.type === "alert" && subject.data.alert_type}
          {subject.type === "runway" && subject.data.runway_code}
          {subject.type === "infrastructure" && subject.data.asset_name}
          {subject.type === "resource" && subject.data.resource_name}
        </p>
      </div>
      {/* Issue summary, impact, suggested action, self-healing, resolution */}
      {(selfHealingIssue ||
        recommendedActions.length > 0 ||
        (resolutionStatus != null && onResolutionChange)) && (
        <div className="space-y-2 border-b border-border p-3">
          {selfHealingIssue && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-2 text-xs">
              <p className="font-semibold text-foreground">Self-healing</p>
              <p className="text-muted-foreground">{selfHealingIssue.reason}</p>
              <p className="mt-1 text-[11px]">
                Raw: {selfHealingIssue.rawValue} → Recommended:{" "}
                {selfHealingIssue.recommendedValue}
              </p>
            </div>
          )}
          {recommendedActions.length > 0 && (
            <div className="text-xs">
              <p className="font-semibold text-foreground">Suggested action</p>
              <p className="text-muted-foreground">
                {recommendedActions[0].suggestedStep}
              </p>
            </div>
          )}
          {resolutionStatus != null && onResolutionChange && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">
                Status
              </span>
              <select
                value={resolutionStatus}
                onChange={(e) =>
                  onResolutionChange(e.target.value as ResolutionStatus)
                }
                className="rounded border border-border bg-background px-2 py-1 text-xs"
              >
                <option value="new">New</option>
                <option value="investigating">Investigating</option>
                <option value="suggested_fix">Suggested fix available</option>
                <option value="resolved">Resolved</option>
                <option value="escalated">Escalated</option>
              </select>
              <span className="text-[10px] text-muted-foreground">
                (UI only, TODO: persist)
              </span>
            </div>
          )}
        </div>
      )}
      <div className="border-b border-border p-3">
        <OperationalImpactPanel impact={operationalImpact ?? null} className="max-h-[220px]" />
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4">
          {subject.type === "flight" && <FlightDetail flight={subject.data} />}
          {subject.type === "alert" && <AlertDetail alert={subject.data} />}
          {subject.type === "runway" && <RunwayDetail runway={subject.data} />}
          {subject.type === "infrastructure" && <InfrastructureDetail asset={subject.data} />}
          {subject.type === "resource" && <ResourceDetail resource={subject.data} />}
        </div>
      </ScrollArea>
    </div>
  );
}

function FlightDetail({ flight }: { flight: Flight }) {
  const mismatch = hasReconciliationMismatch(flight);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1">
        <StatusBadge label={flight.status} variant={flightStatusVariant(flight.status)} />
        {flight.predicted_eta != null && <PredictedBadge />}
        {flight.reconciled_eta != null && <ReconciledBadge />}
        {mismatch && (
          <StatusBadge label="Mismatch" variant="warning" />
        )}
      </div>
      <FieldRow label="Airline" value={flight.airline} />
      <FieldRow label="Origin" value={flight.origin} />
      <FieldRow label="Destination" value={flight.destination} />
      <FieldRow label="Scheduled" value={formatDateTime(flight.scheduled_time)} />
      <FieldRow label="Estimated (raw)" value={formatDateTime(flight.estimated_time)} />
      <FieldRow label="Gate (raw)" value={flight.gate} />
      <FieldRow label="Stand (raw)" value={flight.stand} />
      {flight.predicted_eta != null && (
        <>
          <FieldRow label="Predicted ETA" value={formatDateTime(flight.predicted_eta)} />
          <FieldRow label="Pred. delay" value={formatDelay(flight.predicted_arrival_delay_min)} />
          <FieldRow label="Confidence" value={formatConfidence(flight.prediction_confidence)} />
        </>
      )}
      {flight.reconciled_eta != null && (
        <>
          <FieldRow label="Reconciled ETA" value={formatDateTime(flight.reconciled_eta)} />
          <FieldRow label="Reconciled gate" value={flight.reconciled_gate} />
          <FieldRow label="Reason" value={flight.reconciliation_reason} />
          <FieldRow label="Confidence" value={formatConfidence(flight.reconciliation_confidence)} />
        </>
      )}
    </div>
  );
}

function AlertDetail({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-3">
      <SeverityBadge severity={alert.severity} />
      <FieldRow label="Type" value={alert.alert_type} />
      <FieldRow label="Message" value={alert.message} />
      <FieldRow label="Uniqueness key" value={alert.uniqueness_key} />
      <FieldRow label="Created" value={formatDateTime(alert.created_at)} />
      <FieldRow label="Resolved" value={alert.resolved ? "Yes" : "No"} />
      {alert.related_entity_type && (
        <FieldRow label="Related" value={`${alert.related_entity_type} ${alert.related_entity_id}`} />
      )}
      {alert.suggested_action && (
        <FieldRow label="Suggested action" value={alert.suggested_action} />
      )}
    </div>
  );
}

function RunwayDetail({ runway }: { runway: Runway }) {
  return (
    <div className="space-y-3">
      <StatusBadge label={runway.status} variant={runwayStatusVariant(runway.status)} />
      <FieldRow label="Code" value={runway.runway_code} />
      <FieldRow label="Surface" value={runway.surface_condition} />
      <FieldRow label="Grip score" value={runway.grip_score != null ? `${(runway.grip_score * 100).toFixed(0)}%` : "—"} />
      <FieldRow label="Hazard" value={runway.hazard_detected ? "Yes" : "No"} />
      <FieldRow label="Last inspection" value={formatDateTime(runway.last_inspection_time)} />
    </div>
  );
}

function InfrastructureDetail({ asset }: { asset: InfrastructureAsset }) {
  return (
    <div className="space-y-3">
      <StatusBadge label={asset.status} variant={infraStatusVariant(asset.status)} />
      <FieldRow label="Type" value={asset.asset_type} />
      <FieldRow label="Location" value={asset.location} />
      <FieldRow label="Network health" value={asset.network_health != null ? `${(asset.network_health * 100).toFixed(0)}%` : "—"} />
      <FieldRow label="Tamper detected" value={asset.tamper_detected ? "Yes" : "No"} />
      <FieldRow label="Last updated" value={formatDateTime(asset.last_updated)} />
    </div>
  );
}

function ResourceDetail({ resource }: { resource: Resource }) {
  return (
    <div className="space-y-3">
      <FieldRow label="Type" value={resource.resource_type} />
      <FieldRow label="Status" value={resource.status} />
      <FieldRow label="Assigned to" value={resource.assigned_to} />
      <FieldRow label="Location" value={resource.location} />
    </div>
  );
}
