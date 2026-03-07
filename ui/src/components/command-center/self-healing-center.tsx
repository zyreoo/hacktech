"use client";

import { ScrollArea } from "@/components/modern-ui/scroll-area";
import { Button } from "@/components/modern-ui/button";
import { formatConfidence } from "@/lib/utils";
import type { SelfHealingIssue } from "@/lib/command-center/selectors";
import { Wrench, ChevronRight, CheckCircle2, Search } from "lucide-react";
import { cn } from "@/lib/utils";

const IMPACT_CLASS: Record<SelfHealingIssue["impact"], string> = {
  critical: "border-red-500/60 bg-red-500/10 dark:bg-red-950/40",
  high: "border-amber-500/50 bg-amber-500/10 dark:bg-amber-950/30",
  medium: "border-amber-500/30 bg-amber-500/5 dark:bg-amber-950/20",
  low: "border-slate-500/40 bg-slate-500/5",
};

const IMPACT_LABEL: Record<SelfHealingIssue["impact"], string> = {
  critical: "Critical — immediate action",
  high: "High — affects operations",
  medium: "Medium — review recommended",
  low: "Low — monitor",
};

const ISSUE_LABEL: Record<SelfHealingIssue["issueType"], string> = {
  gate_mismatch: "Gate mismatch",
  eta_mismatch: "ETA mismatch",
  prediction_vs_raw_eta: "Prediction vs raw ETA",
  infrastructure_degraded: "Asset degraded",
  infrastructure_tamper: "Tamper",
};

interface SelfHealingCenterProps {
  issues: SelfHealingIssue[];
  onFocusEntity?: (type: string, id: string) => void;
  className?: string;
}

export function SelfHealingCenter({
  issues,
  onFocusEntity,
  className,
}: SelfHealingCenterProps) {
  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      <div className="border-b border-border px-4 py-3">
        <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Wrench className="h-3.5 w-3.5" /> Self-healing
        </h3>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Operational inconsistencies and recommended corrections
        </p>
      </div>
      <ScrollArea className="max-h-[220px] flex-1">
        <div className="space-y-3 p-3">
          {issues.length === 0 ? (
            <p className="px-3 py-6 text-center text-xs text-muted-foreground">
              No issues — data consistent
            </p>
          ) : (
            issues.map((issue) => (
              <div
                key={issue.id}
                className={cn(
                  "rounded-xl border p-3.5 text-left shadow-sm transition-shadow",
                  IMPACT_CLASS[issue.impact]
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-xs font-semibold text-foreground">
                      {issue.displayLabel}
                    </span>
                    <span className="ml-2 rounded bg-muted/80 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {ISSUE_LABEL[issue.issueType]}
                    </span>
                  </div>
                  {issue.confidence != null && (
                    <span className="text-[10px] font-medium text-muted-foreground">
                      {formatConfidence(issue.confidence)}
                    </span>
                  )}
                </div>
                <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                  <span className="text-muted-foreground">Raw</span>
                  <span className="font-mono text-foreground">{issue.rawValue ?? "—"}</span>
                  <span className="text-muted-foreground">Suggested</span>
                  <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">
                    {issue.recommendedValue ?? "—"}
                  </span>
                </div>
                {issue.reason && (
                  <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
                    {issue.reason}
                  </p>
                )}
                <p className="mt-1.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">
                  Impact: {IMPACT_LABEL[issue.impact]}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 gap-1.5 text-xs"
                    onClick={() =>
                      onFocusEntity?.(issue.entityType, issue.entityId)
                    }
                  >
                    <Search className="h-3 w-3" /> Review
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="h-8 gap-1.5 text-xs"
                    onClick={() => onFocusEntity?.(issue.entityType, issue.entityId)}
                  >
                    <CheckCircle2 className="h-3 w-3" /> Accept fix
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
