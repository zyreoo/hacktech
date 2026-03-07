import Link from "next/link";
import { SectionHeader } from "@/components/shared/section-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Plane } from "lucide-react";
import { formatTime, formatDelay, flightStatusVariant } from "@/lib/utils";
import type { Flight } from "@/types/api";

interface FlightsSummaryProps {
  flights: Flight[];
  maxItems?: number;
}

export function FlightsSummary({ flights, maxItems = 8 }: FlightsSummaryProps) {
  const visible = flights.slice(0, maxItems);

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <SectionHeader
          title="Current Flights"
          icon={Plane}
          action={
            <Link href="/flights" className="text-xs text-sky-600 hover:underline dark:text-sky-400">
              View all →
            </Link>
          }
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800">
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Flight</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Route</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Sched.</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Delay</th>
              <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Gate</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((f) => (
              <tr
                key={f.id}
                className="border-b border-slate-50 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50"
              >
                <td className="px-4 py-2.5">
                  <Link href={`/flights/${f.id}`} className="font-mono font-semibold text-sky-600 hover:underline dark:text-sky-400">
                    {f.flight_code}
                  </Link>
                </td>
                <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">
                  {f.origin} → {f.destination}
                </td>
                <td className="px-4 py-2.5 font-mono text-slate-600 dark:text-slate-300">
                  {formatTime(f.scheduled_time)}
                </td>
                <td className="px-4 py-2.5">
                  <StatusBadge
                    label={f.reconciled_status ?? f.status}
                    variant={flightStatusVariant(f.reconciled_status ?? f.status)}
                    dot
                  />
                </td>
                <td className="px-4 py-2.5 font-mono text-xs">
                  {f.predicted_arrival_delay_min != null ? (
                    <span className={f.predicted_arrival_delay_min > 15 ? "text-amber-600" : "text-slate-500"}>
                      {formatDelay(f.predicted_arrival_delay_min)}
                    </span>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">
                  {f.reconciled_gate ?? f.gate ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {flights.length > maxItems && (
          <div className="px-4 py-2 text-xs text-slate-400">
            +{flights.length - maxItems} more flights
          </div>
        )}
      </div>
    </div>
  );
}
