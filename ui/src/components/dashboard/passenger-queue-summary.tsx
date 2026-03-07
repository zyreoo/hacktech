import { SectionHeader } from "@/components/shared/section-header";
import { Users } from "lucide-react";
import type { PassengerFlow } from "@/types/api";

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
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <SectionHeader title="Passenger Flow" icon={Users} />
      </div>
      <div className="space-y-3 p-4">
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
      </div>
    </div>
  );
}
