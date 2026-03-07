"use client";

import { ScrollArea } from "@/components/modern-ui/scroll-area";
import type { OperationalImpact, ImpactSeverity } from "@/lib/command-center/impact-selectors";
import { ImpactGraph } from "./impact-graph";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";

const SEVERITY_STYLE: Record<ImpactSeverity, string> = {
  low: "border-slate-500/50 bg-slate-500/10 text-slate-700 dark:text-slate-300",
  moderate: "border-sky-500/50 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  high: "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  critical: "border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-300",
};

interface OperationalImpactPanelProps {
  impact: OperationalImpact | null;
  className?: string;
}

export function OperationalImpactPanel({ impact, className }: OperationalImpactPanelProps) {
  if (!impact) {
    return (
      <div
        className={cn(
          "rounded-xl border border-border bg-card p-4 text-center",
          className
        )}
      >
        <p className="text-xs text-muted-foreground">No operational impact estimated</p>
        <p className="mt-1 text-[11px] text-muted-foreground">Select a delayed flight, runway, queue, or asset</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      <div className="border-b border-border px-4 py-2.5">
        <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Activity className="h-3.5 w-3.5" /> Operational impact
        </h3>
        <div className="mt-1.5 flex items-center gap-2">
          <span
            className={cn(
              "rounded px-2 py-0.5 text-[10px] font-semibold uppercase",
              SEVERITY_STYLE[impact.severity]
            )}
          >
            {impact.severity}
          </span>
          {impact.affectedFlightIds.size > 0 && (
            <span className="text-[11px] text-muted-foreground">
              {impact.affectedFlightIds.size} flight(s) affected
            </span>
          )}
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="space-y-3 p-3">
          <p className="text-xs text-muted-foreground">{impact.summary}</p>
          <ImpactGraph chain={impact.chain} severity={impact.severity} />
        </div>
      </ScrollArea>
    </div>
  );
}
