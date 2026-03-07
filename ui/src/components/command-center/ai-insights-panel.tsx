"use client";

import { ScrollArea } from "@/components/modern-ui/scroll-area";
import {
  getPredictedDelayCount,
  getCriticalAlertCount,
  getQueueHotspots,
  getFlightsWithMismatch,
} from "@/lib/command-center/selectors";
import type { OverviewResponse } from "@/types/api";
import { Clock, AlertTriangle, Users, GitMerge, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIInsightsPanelProps {
  overview: OverviewResponse | undefined;
  onSelectFlight?: (flightId: number) => void;
  onSelectAlert?: () => void;
  className?: string;
}

export function AIInsightsPanel({
  overview,
  onSelectFlight,
  onSelectAlert,
  className,
}: AIInsightsPanelProps) {
  const flights = overview?.current_flights ?? [];
  const alerts = overview?.active_alerts ?? [];
  const flows = overview?.passenger_queues ?? [];
  const predictedDelays = getPredictedDelayCount(flights);
  const criticalAlerts = getCriticalAlertCount(alerts);
  const hotspots = getQueueHotspots(flows);
  const highHotspots = hotspots.filter((h) => h.level === "high");
  const degradedInfra = overview?.infrastructure_status?.filter(
    (a) => a.status === "degraded" || a.status === "offline" || a.tamper_detected
  ) ?? [];
  const mismatches = getFlightsWithMismatch(flights);

  const insights: { id: string; icon: React.ComponentType<{ className?: string }>; label: string; count: number; onClick?: () => void }[] = [];
  if (predictedDelays > 0) {
    insights.push({
      id: "delays",
      icon: Clock,
      label: "Flights with predicted delays",
      count: predictedDelays,
    });
  }
  if (criticalAlerts > 0) {
    insights.push({
      id: "critical",
      icon: AlertTriangle,
      label: "Critical alerts",
      count: criticalAlerts,
      onClick: onSelectAlert,
    });
  }
  if (highHotspots.length > 0) {
    insights.push({
      id: "queues",
      icon: Users,
      label: "Queue hotspots",
      count: highHotspots.length,
    });
  }
  if (degradedInfra.length > 0) {
    insights.push({
      id: "infra",
      icon: Cpu,
      label: "Degraded infrastructure",
      count: degradedInfra.length,
    });
  }
  if (mismatches.length > 0) {
    insights.push({
      id: "mismatch",
      icon: GitMerge,
      label: "Reconciliation mismatches",
      count: mismatches.length,
    });
  }

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      <div className="border-b border-border px-3 py-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          AI & operational insights
        </h3>
        <p className="mt-0.5 text-[10px] text-muted-foreground">
          Derived from current data
        </p>
      </div>
      <ScrollArea className="max-h-[180px] flex-1">
        <div className="space-y-1 p-2">
          {insights.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-muted-foreground">
              No notable insights
            </p>
          ) : (
            insights.map((insight) => {
              const Icon = insight.icon;
              return (
                <button
                  key={insight.id}
                  type="button"
                  onClick={insight.onClick}
                  className="flex w-full items-center gap-2 rounded-lg border border-border/50 px-3 py-2 text-left transition-colors hover:bg-muted/60"
                >
                  <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1 text-xs font-medium text-foreground">
                    {insight.label}
                  </span>
                  <span className="rounded bg-primary/15 px-2 py-0.5 text-xs font-semibold tabular-nums text-primary">
                    {insight.count}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
