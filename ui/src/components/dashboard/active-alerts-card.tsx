import Link from "next/link";
import { AlertBanner } from "@/components/shared/alert-banner";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Bell } from "lucide-react";
import type { Alert } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/modern-ui/card";

interface ActiveAlertsCardProps {
  alerts: Alert[];
  maxItems?: number;
  onResolve?: (alertId: number) => void;
  resolvingId?: number | null;
}

export function ActiveAlertsCard({ alerts, maxItems = 6, onResolve, resolvingId }: ActiveAlertsCardProps) {
  const sorted = [...alerts]
    .sort((a, b) => {
      const order = { critical: 0, warning: 1, info: 2 };
      return (order[a.severity as keyof typeof order] ?? 3) - (order[b.severity as keyof typeof order] ?? 3);
    })
    .slice(0, maxItems);

  return (
    <Card variant="default" className="flex min-h-0 flex-col overflow-hidden">
      <CardHeader className="shrink-0 border-b border-border/50 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 shrink-0 text-slate-500" />
            <CardTitle className="text-base font-medium">Active Alerts</CardTitle>
          </div>
          <Link href="/alerts" className="shrink-0 text-xs text-primary hover:underline">
            View all →
          </Link>
        </div>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col overflow-hidden p-0">
        <div className="flex-1 space-y-2 overflow-y-auto p-4">
          {sorted.length === 0 ? (
            <EmptyState
              title="No active alerts"
              description="All systems operating normally."
            />
          ) : (
            sorted.map((alert) => (
              <div
                key={alert.id}
                className="flex items-start justify-between gap-2 rounded-lg border border-border/50 bg-background/50 p-2.5"
              >
                <div className="min-w-0 flex-1">
                  <AlertBanner alert={alert} compact />
                </div>
                {onResolve && !alert.resolved && Number.isFinite(Number(alert.id)) && (() => {
                  const aid = Number(alert.id);
                  return (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="shrink-0 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300"
                      disabled={resolvingId === aid}
                      onClick={() => onResolve(aid)}
                    >
                      {resolvingId === aid ? "Applying…" : "Resolve"}
                    </Button>
                  );
                })()}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
