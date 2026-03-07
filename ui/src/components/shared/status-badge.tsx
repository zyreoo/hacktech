import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import type { StatusVariant } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold tracking-wide uppercase",
  {
    variants: {
      variant: {
        default: "bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-100",
        success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
        warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
        danger:  "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
        info:    "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
        muted:   "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
        purple:  "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

interface StatusBadgeProps extends VariantProps<typeof badgeVariants> {
  label: string;
  dot?: boolean;
  className?: string;
}

export function StatusBadge({ label, variant, dot = false, className }: StatusBadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)}>
      {dot && (
        <span
          className={cn("h-1.5 w-1.5 rounded-full", {
            "bg-slate-500":   variant === "default" || variant === "muted",
            "bg-emerald-500": variant === "success",
            "bg-amber-500":   variant === "warning",
            "bg-red-500":     variant === "danger",
            "bg-sky-500":     variant === "info",
            "bg-violet-500":  variant === "purple",
          })}
        />
      )}
      {label}
    </span>
  );
}

// ─── Source-type labels (raw / predicted / reconciled) ───────────────────────

export function RawBadge() {
  return <StatusBadge label="Raw" variant="muted" />;
}

export function PredictedBadge() {
  return <StatusBadge label="Predicted" variant="purple" />;
}

export function ReconciledBadge() {
  return <StatusBadge label="Reconciled" variant="info" />;
}

// ─── Outcome type badge ───────────────────────────────────────────────────────

const OUTCOME_LABELS: Record<string, string> = {
  ml_model:          "ML Model",
  rules_fallback:    "Rules Fallback",
  insufficient_data: "Insufficient Data",
};

export function PredictionOutcomeBadge({ outcome }: { outcome: string | null | undefined }) {
  if (!outcome) return <StatusBadge label="Unknown" variant="muted" />;
  const variant =
    outcome === "ml_model"
      ? "success"
      : outcome === "rules_fallback"
      ? "warning"
      : "danger";
  return <StatusBadge label={OUTCOME_LABELS[outcome] ?? outcome} variant={variant} />;
}
