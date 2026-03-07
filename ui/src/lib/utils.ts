import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ─── Date/Time Formatters ─────────────────────────────────────────────────────

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const minutes = Math.floor(diff / 60_000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return iso;
  }
}

// ─── Number Formatters ────────────────────────────────────────────────────────

export function formatConfidence(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

export function formatDelay(minutes: number | null | undefined): string {
  if (minutes == null) return "—";
  const sign = minutes >= 0 ? "+" : "";
  return `${sign}${Math.round(minutes)} min`;
}

export function formatGripScore(score: number | null | undefined): string {
  if (score == null) return "—";
  return `${(score * 100).toFixed(0)}%`;
}

// ─── Status Color Maps ────────────────────────────────────────────────────────

export type StatusVariant = "default" | "success" | "warning" | "danger" | "info" | "muted" | "purple";

export function flightStatusVariant(status: string): StatusVariant {
  switch (status?.toLowerCase()) {
    case "scheduled": return "default";
    case "boarding":  return "success";
    case "departed":  return "info";
    case "arrived":   return "success";
    case "delayed":   return "warning";
    case "cancelled": return "danger";
    default:          return "muted";
  }
}

export function alertSeverityVariant(severity: string): StatusVariant {
  switch (severity?.toLowerCase()) {
    case "critical": return "danger";
    case "warning":  return "warning";
    case "info":     return "info";
    default:         return "muted";
  }
}

export function runwayStatusVariant(status: string): StatusVariant {
  switch (status?.toLowerCase()) {
    case "active":      return "success";
    case "closed":      return "danger";
    case "maintenance": return "warning";
    default:            return "muted";
  }
}

export function resourceStatusVariant(status: string): StatusVariant {
  switch (status?.toLowerCase()) {
    case "available":   return "success";
    case "assigned":    return "info";
    case "maintenance": return "warning";
    default:            return "muted";
  }
}

export function infraStatusVariant(status: string): StatusVariant {
  switch (status?.toLowerCase()) {
    case "operational": return "success";
    case "degraded":    return "warning";
    case "offline":     return "danger";
    default:            return "muted";
  }
}

export function predictionOutcomeVariant(outcome: string | null | undefined): StatusVariant {
  switch (outcome) {
    case "ml_model":          return "success";
    case "rules_fallback":    return "warning";
    case "insufficient_data": return "danger";
    default:                  return "muted";
  }
}

export function verificationStatusVariant(status: string): StatusVariant {
  switch (status?.toLowerCase()) {
    case "verified": return "success";
    case "pending":  return "warning";
    case "failed":   return "danger";
    default:         return "muted";
  }
}
