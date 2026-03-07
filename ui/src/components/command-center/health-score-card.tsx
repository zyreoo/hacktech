"use client";

import { cn } from "@/lib/utils";
import { Activity, TrendingUp, TrendingDown } from "lucide-react";

interface HealthScoreCardProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export function HealthScoreCard({
  score,
  size = "md",
  showLabel = true,
  className,
}: HealthScoreCardProps) {
  const variant =
    score >= 80 ? "success" : score >= 60 ? "warning" : "danger";
  const colorClasses = {
    success: "text-emerald-600 dark:text-emerald-400",
    warning: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
  };
  const bgClasses = {
    success: "bg-emerald-500/15 border-emerald-500/30",
    warning: "bg-amber-500/15 border-amber-500/30",
    danger: "bg-red-500/15 border-red-500/30",
  };
  const Icon = score >= 80 ? TrendingUp : score >= 60 ? Activity : TrendingDown;

  const sizeClasses = {
    sm: "text-lg font-bold",
    md: "text-2xl font-bold",
    lg: "text-3xl font-bold",
  };

  return (
    <div
      className={cn(
        "inline-flex flex-col items-center rounded-xl border px-4 py-2 transition-colors",
        bgClasses[variant],
        className
      )}
    >
      <div className={cn("flex items-center gap-2 tabular-nums", colorClasses[variant], sizeClasses[size])}>
        <Icon className="h-5 w-5 shrink-0" />
        {score}
        {showLabel && (
          <span className="text-xs font-medium uppercase tracking-wide opacity-80">/ 100</span>
        )}
      </div>
      {showLabel && (
        <span className="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Health
        </span>
      )}
    </div>
  );
}
