import { SectionHeader } from "@/components/shared/section-header";
import { Users, Activity } from "lucide-react";
import type { PassengerFlow } from "@/types/api";
import { useState, useEffect } from "react";

export function PassengerQueueSummary({ flows }: { flows: PassengerFlow[] }) {
  // Debug: Log the flows data
  console.log('Passenger flows received:', flows.length, flows.slice(0, 3).map(f => ({ id: f.id, security: f.security_queue_count, timestamp: f.timestamp })));
  
  // Take only the 10 most recent flows for more visible changes
  const recentFlows = flows
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10);

  const totalCheckIn = recentFlows.reduce((s, f) => s + f.check_in_count, 0);
  const totalSecurity = recentFlows.reduce((s, f) => s + f.security_queue_count, 0);
  const totalBoarding = recentFlows.reduce((s, f) => s + f.boarding_count, 0);

  // Get latest timestamp for live indicator
  const latestTimestamp = recentFlows.length > 0 
    ? new Date(recentFlows[0].timestamp).toLocaleTimeString()
    : null;

  // Force re-render key based on latest timestamp
  const renderKey = latestTimestamp || 'no-data';

  // Debug counter
  const [renderCount, setRenderCount] = useState(0);
  useEffect(() => {
    setRenderCount(c => c + 1);
  }, [flows]);

  // Dynamic color based on queue levels
  const getSecurityColor = (count: number) => {
    if (count >= 150) return "bg-red-500";  // Critical
    if (count >= 100) return "bg-orange-500";  // Warning
    if (count >= 50) return "bg-amber-500";  // Caution
    return "bg-emerald-500";  // Normal
  };

  const getCheckInColor = (count: number) => {
    if (count >= 200) return "bg-red-500";
    if (count >= 150) return "bg-orange-500";
    return "bg-sky-500";
  };

  const getBoardingColor = (count: number) => {
    if (count >= 150) return "bg-red-500";
    if (count >= 100) return "bg-orange-500";
    return "bg-emerald-500";
  };

  const bars: { label: string; value: number; color: string }[] = [
    { label: "Check-in",      value: totalCheckIn,  color: getCheckInColor(totalCheckIn) },
    { label: "Security",      value: totalSecurity, color: getSecurityColor(totalSecurity) },
    { label: "Boarding",      value: totalBoarding, color: getBoardingColor(totalBoarding) },
  ];
  const max = Math.max(...bars.map((b) => b.value), 1);

  return (
    <div key={renderKey} className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <SectionHeader title="Passenger Flow" icon={Users} />
          {latestTimestamp && (
            <div className="flex items-center gap-1 text-xs text-emerald-600">
              <Activity className="h-3 w-3 animate-pulse" />
              <span>{latestTimestamp}</span>
              <span className="text-slate-400">#{renderCount}</span>
            </div>
          )}
        </div>
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
                className={`h-2 rounded-full transition-all duration-500 ease-out ${color} ${
                  value >= 200 ? 'animate-pulse' : ''
                }`}
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
        <div className="mt-4 space-y-2">
          <p className="text-xs text-slate-500 font-medium">Latest flights:</p>
          {recentFlows.slice(0, 3).map((flow, idx) => (
            <div key={flow.id || idx} className="flex items-center justify-between text-xs p-2 bg-slate-50 dark:bg-slate-800 rounded">
              <span className="text-slate-600">Flight {flow.flight_id} · {flow.terminal_zone}</span>
              <div className="flex gap-3">
                <span className="text-slate-500">Sec: <span className={`font-semibold ${
                  flow.security_queue_count >= 150 ? 'text-red-600' : 
                  flow.security_queue_count >= 100 ? 'text-orange-600' : 'text-slate-700'
                }`}>{flow.security_queue_count}</span></span>
                <span className="text-slate-500">Check: <span className="font-semibold text-slate-700">{flow.check_in_count}</span></span>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400">Latest {recentFlows.length} flow records</p>
      </div>
    </div>
  );
}
