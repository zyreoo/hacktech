import { SectionHeader } from "@/components/shared/section-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Wind } from "lucide-react";
import { formatGripScore, runwayStatusVariant } from "@/lib/utils";
import type { Runway } from "@/types/api";

export function RunwaySummary({ runways }: { runways: Runway[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <SectionHeader title="Runway Conditions" icon={Wind} />
      </div>
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {runways.length === 0 ? (
          <p className="px-4 py-8 text-center text-xs text-slate-400">No runway data</p>
        ) : (
          runways.map((r) => (
            <div key={r.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="font-mono text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {r.runway_code}
                </p>
                <p className="text-xs text-slate-500">
                  {r.surface_condition ?? "Unknown surface"}{" "}
                  {r.contamination_level != null && `· ${(r.contamination_level * 100).toFixed(0)}% contamination`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {r.hazard_detected && (
                  <StatusBadge label={r.hazard_type ?? "Hazard"} variant="danger" dot />
                )}
                <div className="text-right">
                  <p className="text-xs text-slate-500">Grip</p>
                  <p className={`font-mono text-sm font-bold transition-colors duration-500 ${
                    (r.grip_score ?? 1) < 0.3 ? "text-red-600 animate-pulse" :
                    (r.grip_score ?? 1) < 0.5 ? "text-orange-600" :
                    (r.grip_score ?? 1) < 0.7 ? "text-amber-600" : "text-emerald-600"
                  }`}>
                    {formatGripScore(r.grip_score)}
                  </p>
                </div>
                <StatusBadge label={r.status} variant={runwayStatusVariant(r.status)} />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
