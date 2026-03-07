"use client";

import { cn } from "@/lib/utils";
import { alertSeverityVariant } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/status-badge";
import type { StatusVariant } from "@/lib/utils";

const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critical",
  warning: "Warning",
  info: "Info",
};

interface SeverityBadgeProps {
  severity: string;
  dot?: boolean;
  className?: string;
}

export function SeverityBadge({ severity, dot = true, className }: SeverityBadgeProps) {
  const variant = alertSeverityVariant(severity) as StatusVariant;
  const label = SEVERITY_LABELS[severity?.toLowerCase()] ?? severity ?? "—";
  return <StatusBadge label={label} variant={variant} dot={dot} className={className} />;
}
