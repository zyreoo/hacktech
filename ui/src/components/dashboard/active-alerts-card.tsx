import Link from "next/link";
import { AlertBanner } from "@/components/shared/alert-banner";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeader } from "@/components/shared/section-header";
import { Bell } from "lucide-react";
import type { Alert } from "@/types/api";

interface ActiveAlertsCardProps {
  alerts: Alert[];
  maxItems?: number;
}

export function ActiveAlertsCard({ alerts, maxItems = 5 }: ActiveAlertsCardProps) {
  const sorted = [...alerts]
    .sort((a, b) => {
      const order = { critical: 0, warning: 1, info: 2 };
      return (order[a.severity as keyof typeof order] ?? 3) - (order[b.severity as keyof typeof order] ?? 3);
    })
    .slice(0, maxItems);

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <SectionHeader
          title="Active Alerts"
          icon={Bell}
          action={
            <Link href="/alerts" className="text-xs text-sky-600 hover:underline dark:text-sky-400">
              View all →
            </Link>
          }
        />
      </div>
      <div className="space-y-2 p-4">
        {sorted.length === 0 ? (
          <EmptyState
            title="No active alerts"
            description="All systems operating normally."
          />
        ) : (
          sorted.map((alert) => <AlertBanner key={alert.id} alert={alert} compact />)
        )}
      </div>
    </div>
  );
}
