import { AlertTriangle, Info, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Alert } from "@/types/api";
import { formatRelativeTime } from "@/lib/utils";

const severityConfig = {
  critical: {
    bg: "bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800",
    text: "text-red-800 dark:text-red-200",
    icon: XCircle,
    iconColor: "text-red-500",
  },
  warning: {
    bg: "bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800",
    text: "text-amber-800 dark:text-amber-200",
    icon: AlertTriangle,
    iconColor: "text-amber-500",
  },
  info: {
    bg: "bg-sky-50 dark:bg-sky-950/40 border-sky-200 dark:border-sky-800",
    text: "text-sky-800 dark:text-sky-200",
    icon: Info,
    iconColor: "text-sky-500",
  },
};

function getConfig(severity: string) {
  return severityConfig[severity as keyof typeof severityConfig] ?? severityConfig.info;
}

interface AlertBannerProps {
  alert: Alert;
  compact?: boolean;
}

export function AlertBanner({ alert, compact = false }: AlertBannerProps) {
  const cfg = getConfig(alert.severity);
  const Icon = cfg.icon;

  return (
    <div className={cn("flex items-start gap-3 rounded-lg border p-3", cfg.bg)}>
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", cfg.iconColor)} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className={cn("text-xs font-semibold uppercase tracking-wide", cfg.text)}>
            {alert.alert_type}
          </span>
          <span className="shrink-0 text-xs text-slate-500">
            {formatRelativeTime(alert.created_at)}
          </span>
        </div>
        {!compact && (
          <p className={cn("mt-0.5 text-sm", cfg.text)}>{alert.message}</p>
        )}
        {compact && (
          <p className={cn("mt-0.5 truncate text-sm", cfg.text)}>{alert.message}</p>
        )}
        {!compact && alert.related_entity_type && (
          <p className="mt-1 text-xs text-slate-500">
            {alert.related_entity_type}: {alert.related_entity_id}
          </p>
        )}
      </div>
    </div>
  );
}
