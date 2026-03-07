import { Users } from "lucide-react";
import type { PassengerFlow } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/modern-ui/card";

export function PassengerQueueSummary({ flows }: { flows: PassengerFlow[] }) {
  const totalCheckIn = flows.reduce((s, f) => s + f.check_in_count, 0);
  const totalSecurity = flows.reduce((s, f) => s + f.security_queue_count, 0);
  const totalBoarding = flows.reduce((s, f) => s + f.boarding_count, 0);

  const bars: { label: string; value: number; color: string }[] = [
    { label: "Check-in",      value: totalCheckIn,  color: "bg-sky-500" },
    { label: "Security",      value: totalSecurity, color: "bg-amber-500" },
    { label: "Boarding",      value: totalBoarding, color: "bg-emerald-500" },
  ];
  const max = Math.max(...bars.map((b) => b.value), 1);

  return (
    <Card variant="default" className="overflow-hidden">
      <CardHeader className="border-b border-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-slate-500" />
          <CardTitle className="text-base font-medium">Passenger Flow</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 p-4">
        {bars.map(({ label, value, color }) => (
          <div key={label}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-slate-600 dark:text-slate-300">{label}</span>
              <span className="font-mono font-semibold text-slate-800 dark:text-slate-100">
                {value.toLocaleString()}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div
                className={`h-2 rounded-full transition-all ${color}`}
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
        <p className="text-xs text-slate-400">Aggregated across {flows.length} flow records</p>
      </CardContent>
    </Card>
  );
}
