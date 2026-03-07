import { StatusBadge } from "@/components/shared/status-badge";
import { Cpu } from "lucide-react";
import { infraStatusVariant } from "@/lib/utils";
import type { InfrastructureAsset } from "@/types/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/modern-ui/card";

export function InfrastructureSummary({ assets }: { assets: InfrastructureAsset[] }) {
  const issues = assets.filter(
    (a) => a.tamper_detected || a.status === "offline" || a.status === "degraded"
  );

  return (
    <Card variant="default" className="overflow-hidden">
      <CardHeader className="border-b border-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-slate-500" />
          <div>
            <CardTitle className="text-base font-medium">Infrastructure</CardTitle>
            <CardDescription>{assets.length} assets monitored</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {issues.length === 0 ? (
          <p className="px-4 py-6 text-center text-xs text-emerald-600 dark:text-emerald-400">
            ✓ All infrastructure assets operational
          </p>
        ) : (
          issues.slice(0, 5).map((a) => (
            <div key={a.id} className="flex items-center justify-between px-4 py-2.5">
              <div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{a.asset_name}</p>
                <p className="text-xs text-slate-500">{a.asset_type} · {a.location ?? "Unknown"}</p>
              </div>
              <div className="flex items-center gap-2">
                {a.tamper_detected && <StatusBadge label="Tamper" variant="danger" />}
                <StatusBadge label={a.status} variant={infraStatusVariant(a.status)} />
              </div>
            </div>
          ))
        )}
        {issues.length > 5 && (
          <p className="px-4 py-2 text-xs text-slate-400">+{issues.length - 5} more issues</p>
        )}
        </div>
      </CardContent>
    </Card>
  );
}
