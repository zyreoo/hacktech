import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/modern-ui/card";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  highlight?: "default" | "warning" | "danger" | "success";
  className?: string;
}

const cardVariantMap = {
  default: "default" as const,
  warning: "default" as const,
  danger: "default" as const,
  success: "default" as const,
};

const valueStyles = {
  default: "text-slate-900 dark:text-slate-100",
  warning: "text-amber-600 dark:text-amber-400",
  danger: "text-red-600 dark:text-red-400",
  success: "text-emerald-600 dark:text-emerald-400",
};

const borderStyles = {
  default: "",
  warning: "border-l-4 border-l-amber-500 dark:border-l-amber-400",
  danger: "border-l-4 border-l-red-500 dark:border-l-red-400",
  success: "border-l-4 border-l-emerald-500 dark:border-l-emerald-400",
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
    <Card
      variant={cardVariantMap[highlight]}
      size="sm"
      className={cn(
        "transition-all duration-300 hover:shadow-md",
        borderStyles[highlight],
        className
      )}
    >
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {title}
          </p>
          <CardTitle className={cn("mt-2 text-2xl font-bold tabular-nums", valueStyles[highlight])}>
            {value}
          </CardTitle>
          {subtitle && (
            <CardDescription className="mt-0.5 text-xs">{subtitle}</CardDescription>
          )}
        </div>
        {Icon && (
          <Icon className="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500" />
        )}
      </CardHeader>
    </Card>
  );
}
