/**
 * Command Center derived data selectors.
 * All derivations are frontend-only from existing API responses.
 */

import type {
  OverviewResponse,
  Flight,
  Alert,
  Runway,
  PassengerFlow,
  InfrastructureAsset,
  PredictionAudit,
} from "@/types/api";

// ─── Health Score (0–100) ───────────────────────────────────────────────────
// Derived from: critical/warning alerts, runway hazards, infra status, delayed flights.
// Formula: start at 100, subtract penalties for each issue.

const CRITICAL_ALERT_PENALTY = 15;
const WARNING_ALERT_PENALTY = 5;
const RUNWAY_HAZARD_PENALTY = 10;
const INFRA_OFFLINE_PENALTY = 10;
const INFRA_DEGRADED_PENALTY = 5;
const TAMPER_PENALTY = 8;
const DELAYED_FLIGHT_PENALTY = 1; // cap per flight so many delays don't zero out

export function deriveHealthScore(overview: OverviewResponse | undefined): number {
  if (!overview) return 0;
  let score = 100;
  const alerts = overview.active_alerts.filter((a) => !a.resolved);
  alerts.filter((a) => a.severity === "critical").forEach(() => (score -= CRITICAL_ALERT_PENALTY));
  alerts.filter((a) => a.severity === "warning").forEach(() => (score -= WARNING_ALERT_PENALTY));
  overview.runway_conditions.filter((r) => r.hazard_detected).forEach(() => (score -= RUNWAY_HAZARD_PENALTY));
  overview.infrastructure_status.forEach((a) => {
    if (a.status === "offline") score -= INFRA_OFFLINE_PENALTY;
    else if (a.status === "degraded") score -= INFRA_DEGRADED_PENALTY;
    if (a.tamper_detected) score -= TAMPER_PENALTY;
  });
  const delayedCount = overview.current_flights.filter(
    (f) => f.status === "delayed" || (f.predicted_arrival_delay_min ?? 0) > 15
  ).length;
  score -= Math.min(delayedCount * DELAYED_FLIGHT_PENALTY, 20);
  return Math.max(0, Math.min(100, Math.round(score)));
}

// ─── Critical alert count ────────────────────────────────────────────────────

export function getCriticalAlertCount(alerts: Alert[] | undefined): number {
  if (!alerts) return 0;
  return alerts.filter((a) => !a.resolved && a.severity === "critical").length;
}

// ─── Predicted delay count (flights with predicted delay > 15 min) ─────────────

export function getPredictedDelayCount(flights: Flight[] | undefined): number {
  if (!flights) return 0;
  return flights.filter((f) => (f.predicted_arrival_delay_min ?? 0) > 15).length;
}

// ─── Needs Attention Now (for operational summary strip) ─────────────────────
export interface NeedsAttentionSummary {
  criticalAlerts: number;
  selfHealingCount: number;
  degradedInfraCount: number;
  predictedDelays: number;
  total: number;
}

export function getNeedsAttentionSummary(
  overview: OverviewResponse | undefined,
  selfHealingCount: number
): NeedsAttentionSummary {
  if (!overview) {
    return { criticalAlerts: 0, selfHealingCount: 0, degradedInfraCount: 0, predictedDelays: 0, total: 0 };
  }
  const criticalAlerts = getCriticalAlertCount(overview.active_alerts);
  const degradedInfraCount = overview.infrastructure_status.filter(
    (a) => a.status === "degraded" || a.status === "offline" || a.tamper_detected
  ).length;
  const predictedDelays = getPredictedDelayCount(overview.current_flights);
  const total = criticalAlerts + selfHealingCount + degradedInfraCount + predictedDelays;
  return {
    criticalAlerts,
    selfHealingCount,
    degradedInfraCount,
    predictedDelays,
    total,
  };
}

// ─── Queue hotspot summary (zones with high total queue count) ─────────────────

export interface QueueHotspot {
  zone: string;
  totalCount: number;
  checkIn: number;
  security: number;
  boarding: number;
  level: "high" | "medium" | "low";
}

const HIGH_QUEUE_THRESHOLD = 80;
const MEDIUM_QUEUE_THRESHOLD = 40;

export function getQueueHotspots(flows: PassengerFlow[] | undefined): QueueHotspot[] {
  if (!flows || flows.length === 0) return [];
  const byZone = new Map<string, { checkIn: number; security: number; boarding: number }>();
  for (const f of flows) {
    const zone = f.terminal_zone ?? "Unknown";
    const cur = byZone.get(zone) ?? { checkIn: 0, security: 0, boarding: 0 };
    cur.checkIn += f.check_in_count;
    cur.security += f.security_queue_count;
    cur.boarding += f.boarding_count;
    byZone.set(zone, cur);
  }
  return Array.from(byZone.entries()).map(([zone, counts]) => {
    const total = counts.checkIn + counts.security + counts.boarding;
    let level: "high" | "medium" | "low" = "low";
    if (total >= HIGH_QUEUE_THRESHOLD) level = "high";
    else if (total >= MEDIUM_QUEUE_THRESHOLD) level = "medium";
    return { zone, totalCount: total, ...counts, level };
  });
}

// ─── Event timeline entry (derived from alerts, predictions, reconciliation) ─

export type TimelineSource = "alert" | "prediction" | "reconciliation" | "flight";

export interface TimelineEntry {
  id: string;
  timestamp: string;
  source: TimelineSource;
  label: string;
  sublabel?: string;
  entityType?: string;
  entityId?: string;
  derived?: boolean;
}

export function buildTimelineEntries(
  alerts: Alert[] | undefined,
  predictions: PredictionAudit[] | undefined,
  flights: Flight[] | undefined
): TimelineEntry[] {
  const entries: TimelineEntry[] = [];
  const added = new Set<string>();

  if (alerts) {
    for (const a of alerts.filter((a) => !a.resolved)) {
      const key = `alert-${a.id}`;
      if (added.has(key)) continue;
      added.add(key);
      entries.push({
        id: key,
        timestamp: a.created_at,
        source: "alert",
        label: a.alert_type,
        sublabel: a.message,
        entityType: a.related_entity_type ?? "alert",
        entityId: a.related_entity_id ?? String(a.id),
        derived: false,
      });
    }
  }

  if (predictions) {
    const sorted = [...predictions].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
    for (const p of sorted.slice(0, 30)) {
      const key = `pred-${p.id}`;
      if (added.has(key)) continue;
      added.add(key);
      entries.push({
        id: key,
        timestamp: p.created_at,
        source: "prediction",
        label: `Prediction: Flight #${p.flight_id}`,
        sublabel: `Delay ${p.predicted_arrival_delay_min} min`,
        entityType: "flight",
        entityId: String(p.flight_id),
        derived: false,
      });
    }
  }

  if (flights) {
    for (const f of flights) {
      if (f.last_reconciled_at) {
        const key = `recon-${f.id}-${f.last_reconciled_at}`;
        if (added.has(key)) continue;
        added.add(key);
        entries.push({
          id: key,
          timestamp: f.last_reconciled_at,
          source: "reconciliation",
          label: `Reconciled: ${f.flight_code}`,
          sublabel: f.reconciled_gate ?? f.reconciled_eta ?? undefined,
          entityType: "flight",
          entityId: String(f.id),
          derived: false,
        });
      }
      if (f.last_prediction_at) {
        const key = `flight-pred-${f.id}-${f.last_prediction_at}`;
        if (added.has(key)) continue;
        added.add(key);
        entries.push({
          id: key,
          timestamp: f.last_prediction_at,
          source: "prediction",
          label: `Prediction: ${f.flight_code}`,
          sublabel: f.predicted_arrival_delay_min != null ? `${f.predicted_arrival_delay_min} min delay` : undefined,
          entityType: "flight",
          entityId: String(f.id),
          derived: true,
        });
      }
    }
  }

  entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  return entries.slice(0, 50);
}

// ─── Reconciliation mismatch (raw vs reconciled differs) ───────────────────────

export function hasReconciliationMismatch(flight: Flight): boolean {
  const gateMismatch = flight.reconciled_gate != null && flight.gate !== flight.reconciled_gate;
  const etaMismatch =
    flight.reconciled_eta != null &&
    flight.estimated_time != null &&
    flight.estimated_time !== flight.reconciled_eta;
  return gateMismatch || etaMismatch;
}

export function getFlightsWithMismatch(flights: Flight[] | undefined): Flight[] {
  if (!flights) return [];
  return flights.filter(hasReconciliationMismatch);
}

// ─── Resolution workflow (UI state; backend persistence TODO) ─────────────────
export type ResolutionStatus =
  | "new"
  | "investigating"
  | "suggested_fix"
  | "resolved"
  | "escalated";

export function entityKey(type: string, id: string): string {
  return `${type}-${id}`;
}

// ─── Self-healing issues ──────────────────────────────────────────────────────
export type SelfHealingIssueType =
  | "gate_mismatch"
  | "eta_mismatch"
  | "prediction_vs_raw_eta"
  | "infrastructure_degraded"
  | "infrastructure_tamper";

export type SelfHealingImpact = "low" | "medium" | "high" | "critical";

export interface SelfHealingIssue {
  id: string;
  entityType: "flight" | "infrastructure";
  entityId: string;
  displayLabel: string;
  issueType: SelfHealingIssueType;
  rawValue: string | null;
  recommendedValue: string | null;
  confidence: number | null;
  reason: string | null;
  impact: SelfHealingImpact;
  flight?: Flight;
  asset?: InfrastructureAsset;
}

const IMPACT_ORDER: Record<SelfHealingImpact, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export function getSelfHealingIssues(
  flights: Flight[] | undefined,
  infrastructure: InfrastructureAsset[] | undefined
): SelfHealingIssue[] {
  const issues: SelfHealingIssue[] = [];
  if (flights) {
    for (const f of flights) {
      if (f.reconciled_gate != null && f.gate !== f.reconciled_gate) {
        issues.push({
          id: `gate-${f.id}`,
          entityType: "flight",
          entityId: String(f.id),
          displayLabel: f.flight_code ?? `Flight ${f.id}`,
          issueType: "gate_mismatch",
          rawValue: f.gate ?? "—",
          recommendedValue: f.reconciled_gate,
          confidence: f.reconciliation_confidence ?? null,
          reason: f.reconciliation_reason ?? "Reconciled gate differs from raw AODB.",
          impact: "high",
          flight: f,
        });
      }
      if (
        f.reconciled_eta != null &&
        f.estimated_time != null &&
        f.estimated_time !== f.reconciled_eta
      ) {
        issues.push({
          id: `eta-${f.id}`,
          entityType: "flight",
          entityId: String(f.id),
          displayLabel: f.flight_code ?? `Flight ${f.id}`,
          issueType: "eta_mismatch",
          rawValue: f.estimated_time,
          recommendedValue: f.reconciled_eta,
          confidence: f.reconciliation_confidence ?? null,
          reason: f.reconciliation_reason ?? "Reconciled ETA differs from raw.",
          impact: "medium",
          flight: f,
        });
      }
      if (
        f.predicted_eta != null &&
        f.estimated_time != null &&
        Math.abs(
          new Date(f.predicted_eta).getTime() - new Date(f.estimated_time).getTime()
        ) >
          15 * 60_000
      ) {
        issues.push({
          id: `pred-eta-${f.id}`,
          entityType: "flight",
          entityId: String(f.id),
          displayLabel: f.flight_code ?? `Flight ${f.id}`,
          issueType: "prediction_vs_raw_eta",
          rawValue: f.estimated_time,
          recommendedValue: f.predicted_eta,
          confidence: f.prediction_confidence ?? null,
          reason: "Predicted ETA differs materially from raw.",
          impact: (f.predicted_arrival_delay_min ?? 0) > 30 ? "high" : "medium",
          flight: f,
        });
      }
    }
  }
  if (infrastructure) {
    for (const a of infrastructure) {
      if (a.status === "degraded" || a.status === "offline") {
        issues.push({
          id: `infra-${a.id}`,
          entityType: "infrastructure",
          entityId: String(a.id),
          displayLabel: a.asset_name ?? `Asset ${a.id}`,
          issueType: "infrastructure_degraded",
          rawValue: a.status,
          recommendedValue: "operational",
          confidence: a.network_health ?? null,
          reason: `Asset reported ${a.status}. Verify and restore if possible.`,
          impact: a.status === "offline" ? "high" : "medium",
          asset: a,
        });
      }
      if (a.tamper_detected) {
        issues.push({
          id: `tamper-${a.id}`,
          entityType: "infrastructure",
          entityId: String(a.id),
          displayLabel: a.asset_name ?? `Asset ${a.id}`,
          issueType: "infrastructure_tamper",
          rawValue: "tamper_detected",
          recommendedValue: "verified_secure",
          confidence: null,
          reason: "Tamper detected. Verify asset integrity and secure area.",
          impact: "critical",
          asset: a,
        });
      }
    }
  }
  issues.sort((a, b) => IMPACT_ORDER[a.impact] - IMPACT_ORDER[b.impact]);
  return issues;
}

// ─── Recommended actions ─────────────────────────────────────────────────────
export type RecommendedActionPriority = "critical" | "high" | "medium" | "low";

export interface RecommendedAction {
  id: string;
  title: string;
  description: string;
  priority: RecommendedActionPriority;
  entityType: string;
  entityId: string;
  entityLabel?: string;
  suggestedStep?: string;
}

export function getRecommendedActions(
  overview: OverviewResponse | undefined
): RecommendedAction[] {
  if (!overview) return [];
  const actions: RecommendedAction[] = [];
  const flights = overview.current_flights;
  const alerts = overview.active_alerts.filter((a) => !a.resolved);
  const hotspots = getQueueHotspots(overview.passenger_queues);
  const infra = overview.infrastructure_status;
  const mismatches = getFlightsWithMismatch(flights);

  for (const a of alerts.filter((a) => a.severity === "critical")) {
    actions.push({
      id: `alert-${a.id}`,
      title: "Address critical alert",
      description: a.message,
      priority: "critical",
      entityType: "alert",
      entityId: String(a.id),
      entityLabel: a.alert_type,
      suggestedStep: a.suggested_action ?? "Review alert and verify related entity.",
    });
  }
  for (const h of hotspots.filter((h) => h.level === "high")) {
    actions.push({
      id: `queue-${h.zone}`,
      title: "Reduce queue congestion",
      description: `${h.zone}: ${h.totalCount} passengers in flow.`,
      priority: "high",
      entityType: "zone",
      entityId: h.zone,
      entityLabel: h.zone,
      suggestedStep: "Consider opening additional security lane or check-in desks.",
    });
  }
  for (const asset of infra.filter(
    (a) => a.status === "degraded" || a.status === "offline"
  )) {
    actions.push({
      id: `infra-${asset.id}`,
      title: "Verify asset integrity",
      description: `${asset.asset_name} is ${asset.status}.`,
      priority: asset.status === "offline" ? "critical" : "high",
      entityType: "infrastructure",
      entityId: String(asset.id),
      entityLabel: asset.asset_name,
      suggestedStep: "Verify asset integrity and secure area. Restore service if safe.",
    });
  }
  for (const asset of infra.filter((a) => a.tamper_detected)) {
    actions.push({
      id: `tamper-${asset.id}`,
      title: "Secure tampered asset",
      description: `Tamper detected on ${asset.asset_name}.`,
      priority: "critical",
      entityType: "infrastructure",
      entityId: String(asset.id),
      entityLabel: asset.asset_name,
      suggestedStep: "Verify asset integrity and secure area immediately.",
    });
  }
  for (const f of mismatches) {
    actions.push({
      id: `mismatch-${f.id}`,
      title: "Review gate/ETA mismatch",
      description: `${f.flight_code}: raw and reconciled data differ.`,
      priority: "medium",
      entityType: "flight",
      entityId: String(f.id),
      entityLabel: f.flight_code,
      suggestedStep: "Review gate mismatch and confirm latest reported update with AODB.",
    });
  }
  const delayedCount = flights.filter(
    (f) => (f.predicted_arrival_delay_min ?? 0) > 15
  ).length;
  if (delayedCount > 0) {
    actions.push({
      id: "delays-summary",
      title: "Monitor predicted delays",
      description: `${delayedCount} flight(s) with predicted delay > 15 min.`,
      priority: "medium",
      entityType: "flights",
      entityId: "",
      suggestedStep: "Review delay predictions and adjust ground handling or pax comms.",
    });
  }
  const po: Record<RecommendedActionPriority, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
  };
  actions.sort((a, b) => po[a.priority] - po[b.priority]);
  return actions.slice(0, 20);
}

export function getSelfHealingIssueForSubject(
  subject: { type: string; data?: { id: number } } | null,
  issues: SelfHealingIssue[]
): SelfHealingIssue | undefined {
  if (!subject || !subject.data) return undefined;
  const id = String(subject.data.id);
  return issues.find(
    (i) => i.entityType === subject.type && i.entityId === id
  );
}

export function getRecommendedActionsForSubject(
  subject: { type: string; data?: { id: number } } | null,
  actions: RecommendedAction[]
): RecommendedAction[] {
  if (!subject || !subject.data) return [];
  const id = String((subject.data as { id?: number }).id ?? "");
  return actions.filter(
    (a) =>
      (a.entityType === subject.type && a.entityId === id) ||
      (subject.type === "flight" && a.entityType === "flight" && a.entityId === id)
  );
}
