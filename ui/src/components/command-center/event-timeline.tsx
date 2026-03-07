"use client";

import { ScrollArea } from "@/components/modern-ui/scroll-area";
import { formatRelativeTime } from "@/lib/utils";
import type { TimelineEntry } from "@/lib/command-center/selectors";
import { AlertTriangle, BrainCircuit, GitMerge, Plane } from "lucide-react";
import { cn } from "@/lib/utils";

interface EventTimelineProps {
  entries: TimelineEntry[];
  onSelectEntity?: (type: string, id: string) => void;
  className?: string;
}

const sourceIcon: Record<TimelineEntry["source"], React.ComponentType<{ className?: string }>> = {
  alert: AlertTriangle,
  prediction: BrainCircuit,
  reconciliation: GitMerge,
  flight: Plane,
};

const sourceColor: Record<TimelineEntry["source"], string> = {
  alert: "text-red-500",
  prediction: "text-violet-500",
  reconciliation: "text-sky-500",
  flight: "text-slate-500",
};

export function EventTimeline({
  entries,
  onSelectEntity,
  className,
}: EventTimelineProps) {
  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      <div className="border-b border-border px-3 py-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Event timeline
        </h3>
        <p className="mt-0.5 text-[10px] text-muted-foreground">
          Derived from alerts, predictions & reconciliation
        </p>
      </div>
      <ScrollArea className="max-h-[220px] flex-1">
        <div className="space-y-0 p-2">
          {entries.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-muted-foreground">
              No recent events
            </p>
          ) : (
            entries.slice(0, 30).map((entry) => {
              const Icon = sourceIcon[entry.source];
              const colorClass = sourceColor[entry.source];
              return (
                <button
                  key={entry.id}
                  type="button"
                  className="flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted/60"
                  onClick={() => {
                    if (entry.entityType && entry.entityId) {
                      onSelectEntity?.(entry.entityType, entry.entityId);
                    }
                  }}
                >
                  <Icon className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", colorClass)} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-foreground">{entry.label}</p>
                    {entry.sublabel && (
                      <p className="truncate text-[10px] text-muted-foreground">{entry.sublabel}</p>
                    )}
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground">
                        {formatRelativeTime(entry.timestamp)}
                      </span>
                      {entry.derived && (
                        <span className="rounded bg-muted px-1 text-[9px] text-muted-foreground">
                          derived
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
