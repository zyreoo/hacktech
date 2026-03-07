"use client";

import { ScrollArea } from "@/components/modern-ui/scroll-area";
import { Button } from "@/components/modern-ui/button";
import type {
  RecommendedAction,
  RecommendedActionPriority,
} from "@/lib/command-center/selectors";
import { ChevronRight, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const PRIORITY_CLASS: Record<RecommendedActionPriority, string> = {
  critical: "border-l-4 border-l-red-500 bg-red-500/5 dark:bg-red-950/30",
  high: "border-l-4 border-l-amber-500 bg-amber-500/5 dark:bg-amber-950/30",
  medium: "border-l-4 border-l-sky-500 bg-sky-500/5 dark:bg-sky-950/30",
  low: "border-l-4 border-l-slate-500 bg-slate-500/5",
};

const BENEFIT_BY_PRIORITY: Record<RecommendedActionPriority, string> = {
  critical: "Reduces operational risk immediately",
  high: "Improves situational awareness and response",
  medium: "Aligns data and reduces passenger impact",
  low: "Keeps operations running smoothly",
};

interface RecommendedActionsPanelProps {
  actions: RecommendedAction[];
  onFocusEntity?: (type: string, id: string) => void;
  onDismiss?: (id: string) => void;
  className?: string;
}

export function RecommendedActionsPanel({
  actions,
  onFocusEntity,
  onDismiss,
  className,
}: RecommendedActionsPanelProps) {
  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      <div className="border-b border-border px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Recommended actions
        </h3>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Next steps for critical items — priority order
        </p>
      </div>
      <ScrollArea className="max-h-[220px] flex-1">
        <div className="space-y-2 p-3">
          {actions.length === 0 ? (
            <p className="px-3 py-6 text-center text-xs text-muted-foreground">
              No actions — all clear
            </p>
          ) : (
            actions.map((action) => (
              <div
                key={action.id}
                className={cn(
                  "rounded-xl border border-border/60 p-3 text-left shadow-sm",
                  PRIORITY_CLASS[action.priority]
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-foreground">
                    {action.title}
                  </span>
                  <span
                    className={cn(
                      "rounded px-2 py-0.5 text-[10px] font-semibold uppercase",
                      action.priority === "critical" && "bg-red-500/20 text-red-700 dark:text-red-300",
                      action.priority === "high" && "bg-amber-500/20 text-amber-700 dark:text-amber-300",
                      action.priority === "medium" && "bg-sky-500/20 text-sky-700 dark:text-sky-300",
                      action.priority === "low" && "bg-slate-500/20 text-slate-600 dark:text-slate-400"
                    )}
                  >
                    {action.priority}
                  </span>
                </div>
                {action.entityLabel && (
                  <p className="mt-1 text-[10px] font-medium text-muted-foreground">
                    Entity: {action.entityLabel}
                  </p>
                )}
                <p className="mt-1.5 line-clamp-2 text-[11px] text-muted-foreground">
                  {action.description}
                </p>
                {action.suggestedStep && (
                  <p className="mt-1.5 text-[11px] font-medium text-primary">
                    {action.suggestedStep}
                  </p>
                )}
                <p className="mt-1 flex items-center gap-1 text-[10px] text-emerald-700 dark:text-emerald-400">
                  <Zap className="h-3 w-3" />
                  {BENEFIT_BY_PRIORITY[action.priority]}
                </p>
                <div className="mt-3 flex gap-2">
                  {action.entityType && action.entityId && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1 text-xs"
                      onClick={() =>
                        onFocusEntity?.(action.entityType, action.entityId)
                      }
                    >
                      View <ChevronRight className="h-3 w-3" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => onDismiss?.(action.id)}
                  >
                    Dismiss
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
