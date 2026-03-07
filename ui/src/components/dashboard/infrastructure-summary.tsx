import { SectionHeader } from "@/components/shared/section-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Cpu } from "lucide-react";
import { infraStatusVariant } from "@/lib/utils";
import type { InfrastructureAsset } from "@/types/api";

export function InfrastructureSummary({ assets }: { assets: InfrastructureAsset[] }) {
  const issues = assets.filter(
    (a) => a.tamper_detected || a.status === "offline" || a.status === "degraded" || a.status === "maintenance"
  );

  // Show network health as a percentage for more visibility
  const getHealthColor = (health: number | null) => {
    if (!health) return "text-slate-400";
    if (health < 0.3) return "text-red-600 animate-pulse";
    if (health < 0.6) return "text-orange-600";
    if (health < 0.8) return "text-amber-600";
    return "text-emerald-600";
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <SectionHeader title="Infrastructure" icon={Cpu} subtitle={`${assets.length} assets monitored`} />
      </div>
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
                {a.network_health !== null && (
                  <span className={`text-xs font-mono transition-colors duration-500 ${getHealthColor(a.network_health)}`}>
                    {Math.round(a.network_health * 100)}%
                  </span>
                )}
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
    </div>
  );
}
