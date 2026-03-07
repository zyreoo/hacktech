"use client";

import { ScrollArea } from "@/components/modern-ui/scroll-area";
import { SeverityBadge } from "./severity-badge";
import { formatRelativeTime } from "@/lib/utils";
import type { Alert } from "@/types/api";
import { cn } from "@/lib/utils";

interface AlertsPanelProps {
  alerts: Alert[];
  selectedAlertId: number | null;
  onSelectAlert: (alert: Alert) => void;
  onFocusEntity?: (type: string, id: string) => void;
  className?: string;
}

export function AlertsPanel({
  alerts,
  selectedAlertId,
  onSelectAlert,
  onFocusEntity,
  className,
}: AlertsPanelProps) {
  const active = alerts.filter((a) => !a.resolved);
  const sorted = [...active].sort((a, b) => {
    const order = { critical: 0, warning: 1, info: 2 };
    return (order[a.severity as keyof typeof order] ?? 3) - (order[b.severity as keyof typeof order] ?? 3);
  });

  return (
    <div
      className={cn(
        "flex w-72 shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      <div className="border-b border-border px-3 py-2.5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Active Alerts
        </h3>
        <p className="mt-1 text-sm font-semibold tabular-nums">{sorted.length}</p>
      </div>
      <ScrollArea className="flex-1">
        <div className="space-y-1 p-2">
          {sorted.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-muted-foreground">
              No active alerts
            </p>
          ) : (
            sorted.map((alert) => (
              <button
                key={alert.id}
                type="button"
                onClick={() => {
                  onSelectAlert(alert);
                  if (alert.related_entity_type && alert.related_entity_id) {
                    onFocusEntity?.(alert.related_entity_type, alert.related_entity_id);
                  }
                }}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-left transition-colors",
                  selectedAlertId === alert.id
                    ? "border-primary bg-primary/10"
                    : "border-transparent hover:bg-muted/60"
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <SeverityBadge severity={alert.severity} dot />
                  <span className="text-[10px] text-muted-foreground">
                    {formatRelativeTime(alert.created_at)}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs font-medium text-foreground">
                  {alert.alert_type}
                </p>
                <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">
                  {alert.message}
                </p>
                {alert.uniqueness_key && (
                  <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                    {alert.uniqueness_key}
                  </p>
                )}
                {alert.related_entity_type && alert.related_entity_id && (
                  <p className="mt-0.5 text-[10px] text-muted-foreground">
                    {alert.related_entity_type}: {alert.related_entity_id}
                  </p>
                )}
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
