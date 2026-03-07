import { Users, Activity } from "lucide-react";
import type { PassengerFlow } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/modern-ui/card";

export function PassengerQueueSummary({ flows }: { flows: PassengerFlow[] }) {
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
    <Card key={renderKey} variant="default" className="overflow-hidden">
      <CardHeader className="border-b border-border/50 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base font-medium">Passenger Flow</CardTitle>
          </div>
          {latestTimestamp && (
            <div className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
              <Activity className="h-3 w-3 animate-pulse" />
              <span>{latestTimestamp}</span>
            </div>
          )}
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
                className={`h-2 rounded-full transition-all duration-500 ease-out ${color} ${
                  value >= 200 ? 'animate-pulse' : ''
                }`}
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
        <p className="text-xs text-muted-foreground">Aggregated across {flows.length} flow records</p>
      </CardContent>
    </Card>
  );
}
