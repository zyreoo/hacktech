import { StatusBadge } from "@/components/shared/status-badge";
import { Wind } from "lucide-react";
import { formatGripScore, runwayStatusVariant } from "@/lib/utils";
import type { Runway } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/modern-ui/card";

export function RunwaySummary({ runways }: { runways: Runway[] }) {
  return (
    <Card variant="default" className="overflow-hidden">
      <CardHeader className="border-b border-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Wind className="h-4 w-4 text-slate-500" />
          <CardTitle className="text-base font-medium">Runway Conditions</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="p-0">
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
                  <p className={`font-mono text-sm font-bold ${
                    (r.grip_score ?? 1) < 0.4 ? "text-red-600" :
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
      </CardContent>
    </Card>
  );
}
