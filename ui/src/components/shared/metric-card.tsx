import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  highlight?: "default" | "warning" | "danger" | "success";
  className?: string;
}

const highlightStyles = {
  default: "border-slate-200 dark:border-slate-700",
  warning: "border-l-4 border-l-amber-500 dark:border-l-amber-400",
  danger:  "border-l-4 border-l-red-500 dark:border-l-red-400",
  success: "border-l-4 border-l-emerald-500 dark:border-l-emerald-400",
};

const valueStyles = {
  default: "text-slate-900 dark:text-slate-100",
  warning: "text-amber-700 dark:text-amber-300",
  danger:  "text-red-700 dark:text-red-300",
  success: "text-emerald-700 dark:text-emerald-300",
};

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  highlight = "default",
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-white dark:bg-slate-900 p-4 shadow-sm",
        highlightStyles[highlight],
        className
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {title}
        </p>
        {Icon && (
          <Icon className="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500" />
        )}
      </div>
      <p className={cn("mt-2 text-2xl font-bold tabular-nums", valueStyles[highlight])}>
        {value}
      </p>
      {subtitle && (
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
      )}
    </div>
  );
}
