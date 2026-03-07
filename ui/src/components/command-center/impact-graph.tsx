"use client";

import type { ImpactChainNode } from "@/lib/command-center/impact-selectors";
import { ArrowDown, AlertCircle, GitBranch, Flag } from "lucide-react";
import { cn } from "@/lib/utils";

interface ImpactGraphProps {
  chain: ImpactChainNode[];
  severity: "low" | "moderate" | "high" | "critical";
  className?: string;
}

const SEVERITY_CLASS = {
  low: "text-slate-500 border-slate-500/40",
  moderate: "text-sky-500 border-sky-500/40",
  high: "text-amber-500 border-amber-500/40",
  critical: "text-red-500 border-red-500/40",
};

export function ImpactGraph({ chain, severity, className }: ImpactGraphProps) {
  if (chain.length === 0) return null;

  return (
    <div className={cn("space-y-1", className)}>
      {chain.map((node, i) => (
        <div key={node.id} className="flex items-center gap-2">
          {i > 0 && (
            <div className="flex w-6 shrink-0 justify-center">
              <ArrowDown className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
          )}
          <div
            className={cn(
              "flex flex-1 items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs",
              node.type === "source" && "border-l-4 bg-muted/50 font-medium",
              node.type === "propagation" && "border-l-4 border-l-amber-500/50 bg-amber-500/5",
              node.type === "outcome" && "bg-muted/30",
              node.type === "source" && SEVERITY_CLASS[severity]
            )}
          >
            {node.type === "source" && <AlertCircle className="h-3.5 w-3.5 shrink-0" />}
            {node.type === "propagation" && <GitBranch className="h-3.5 w-3.5 shrink-0 text-amber-500" />}
            {node.type === "outcome" && <Flag className="h-3 w-3 shrink-0 text-muted-foreground" />}
            <span className="truncate">{node.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
