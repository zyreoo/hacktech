"use client";

import { Plane, AlertTriangle, Clock, Activity, AlertCircle } from "lucide-react";
import { HealthScoreCard } from "./health-score-card";
import { cn } from "@/lib/utils";
import {
  deriveHealthScore,
  getCriticalAlertCount,
  getPredictedDelayCount,
  type NeedsAttentionSummary,
} from "@/lib/command-center/selectors";
import type { OverviewResponse } from "@/types/api";

interface SummaryMetricsBarProps {
  overview: OverviewResponse | undefined;
  lastRefresh: Date | null;
  isLoading?: boolean;
  needsAttention?: NeedsAttentionSummary | null;
  className?: string;
}

export function SummaryMetricsBar({
  overview,
  lastRefresh,
  isLoading,
  needsAttention,
  className,
}: SummaryMetricsBarProps) {
  const healthScore = deriveHealthScore(overview);
  const activeFlights = overview?.current_flights?.length ?? 0;
  const activeAlerts = overview?.active_alerts?.filter((a) => !a.resolved).length ?? 0;
  const criticalAlerts = getCriticalAlertCount(overview?.active_alerts);
  const predictedDelays = getPredictedDelayCount(overview?.current_flights);

  return (
    <div className={cn("flex flex-col border-b border-border bg-card/90", className)}>
      <header className="flex flex-wrap items-center gap-3 px-4 py-2.5">
        <HealthScoreCard score={healthScore} size="sm" showLabel />
        <MetricPill
          icon={Plane}
          value={activeFlights}
          label="Flights"
          highlight={activeFlights === 0}
        />
        <MetricPill
          icon={AlertTriangle}
          value={activeAlerts}
          label="Alerts"
          sub={`${criticalAlerts} critical`}
          highlight={criticalAlerts > 0}
          variant={criticalAlerts > 0 ? "danger" : "default"}
        />
        <MetricPill
          icon={Clock}
          value={predictedDelays}
          label="Pred. Delays"
          highlight={predictedDelays > 0}
          variant={predictedDelays > 0 ? "warning" : "default"}
        />
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          {isLoading && <Activity className="h-3.5 w-3.5 animate-pulse" />}
          <span>
            {lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : "—"}
          </span>
          <span className="rounded bg-muted px-1.5 py-0.5 font-medium">Live</span>
        </div>
      </header>
      {needsAttention && needsAttention.total > 0 && (
        <div className="flex flex-wrap items-center gap-4 border-t border-border/60 bg-amber-500/5 px-4 py-2 dark:bg-amber-950/30">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 dark:text-amber-300">
            <AlertCircle className="h-3.5 w-3.5" />
            Needs attention now
          </span>
          {needsAttention.criticalAlerts > 0 && (
            <span className="text-[11px] text-muted-foreground">
              <strong className="text-red-600 dark:text-red-400">{needsAttention.criticalAlerts}</strong> critical alerts
            </span>
          )}
          {needsAttention.selfHealingCount > 0 && (
            <span className="text-[11px] text-muted-foreground">
              <strong className="text-amber-600 dark:text-amber-400">{needsAttention.selfHealingCount}</strong> self-healing
            </span>
          )}
          {needsAttention.degradedInfraCount > 0 && (
            <span className="text-[11px] text-muted-foreground">
              <strong className="text-amber-600 dark:text-amber-400">{needsAttention.degradedInfraCount}</strong> degraded infra
            </span>
          )}
          {needsAttention.predictedDelays > 0 && (
            <span className="text-[11px] text-muted-foreground">
              <strong className="text-amber-600 dark:text-amber-400">{needsAttention.predictedDelays}</strong> predicted delays
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function MetricPill({
  icon: Icon,
  value,
  label,
  sub,
  highlight,
  variant = "default",
}: {
  icon: React.ComponentType<{ className?: string }>;
  value: number;
  label: string;
  sub?: string;
  highlight?: boolean;
  variant?: "default" | "warning" | "danger";
}) {
  const variantClass =
    variant === "danger"
      ? "text-red-600 dark:text-red-400"
      : variant === "warning"
      ? "text-amber-600 dark:text-amber-400"
      : "text-foreground";
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-1.5",
        highlight && "border-amber-500/40 bg-amber-500/5 dark:border-amber-400/30 dark:bg-amber-500/10"
      )}
    >
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="flex flex-col">
        <span className={cn("text-sm font-semibold tabular-nums", variantClass)}>
          {value}
        </span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {label}
          {sub ? ` · ${sub}` : ""}
        </span>
      </div>
    </div>
  );
}
