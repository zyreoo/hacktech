"use client";

import { cn } from "@/lib/utils";
import { Plane, AlertTriangle, Users, Wind, Cpu, BrainCircuit, GitMerge } from "lucide-react";

export interface LayerVisibility {
  flights: boolean;
  alerts: boolean;
  queues: boolean;
  runways: boolean;
  infrastructure: boolean;
  prediction: boolean;
  reconciliation: boolean;
}

const DEFAULT_LAYERS: LayerVisibility = {
  flights: true,
  alerts: true,
  queues: true,
  runways: true,
  infrastructure: true,
  prediction: true,
  reconciliation: true,
};

const LAYER_ITEMS: { key: keyof LayerVisibility; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: "flights", label: "Flights", icon: Plane },
  { key: "alerts", label: "Alerts", icon: AlertTriangle },
  { key: "queues", label: "Queues", icon: Users },
  { key: "runways", label: "Runways", icon: Wind },
  { key: "infrastructure", label: "Infrastructure", icon: Cpu },
  { key: "prediction", label: "Prediction", icon: BrainCircuit },
  { key: "reconciliation", label: "Reconciliation", icon: GitMerge },
];

interface LayerControlsProps {
  visibility: LayerVisibility;
  onVisibilityChange: (key: keyof LayerVisibility, value: boolean) => void;
  className?: string;
}

export function LayerControls({ visibility, onVisibilityChange, className }: LayerControlsProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card/90 p-2 shadow-sm",
        className
      )}
    >
      <span className="w-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        Layers
      </span>
      {LAYER_ITEMS.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          onClick={() => onVisibilityChange(key, !visibility[key])}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
            visibility[key]
              ? "bg-primary/15 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <Icon className="h-3.5 w-3.5" />
          {label}
        </button>
      ))}
    </div>
  );
}

export { DEFAULT_LAYERS };
