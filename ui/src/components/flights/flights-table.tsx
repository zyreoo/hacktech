"use client";

import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge, PredictedBadge, ReconciledBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import {
  formatTime,
  formatDelay,
  formatConfidence,
  flightStatusVariant,
} from "@/lib/utils";
import type { Flight } from "@/types/api";
import { Plane } from "lucide-react";

interface FlightsTableProps {
  flights: Flight[];
}

export function FlightsTable({ flights }: FlightsTableProps) {
  if (flights.length === 0) {
    return <EmptyState title="No flights found" description="Try adjusting your filters." />;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-100 dark:border-slate-800">
            <TableHead className="text-xs font-semibold uppercase text-slate-500">Flight</TableHead>
            <TableHead className="text-xs font-semibold uppercase text-slate-500">Airline</TableHead>
            <TableHead className="text-xs font-semibold uppercase text-slate-500">Route</TableHead>
            <TableHead className="text-xs font-semibold uppercase text-slate-500">Sched.</TableHead>
            {/* Raw */}
            <TableHead className="text-xs font-semibold uppercase text-slate-500">
              <span className="text-slate-400">Status (Raw)</span>
            </TableHead>
            <TableHead className="text-xs font-semibold uppercase text-slate-500">
              <span className="text-slate-400">Gate (Raw)</span>
            </TableHead>
            {/* Reconciled */}
            <TableHead className="text-xs font-semibold uppercase text-slate-500">
              <span className="text-sky-600 dark:text-sky-400">Status ⟳</span>
            </TableHead>
            <TableHead className="text-xs font-semibold uppercase text-slate-500">
              <span className="text-sky-600 dark:text-sky-400">Gate ⟳</span>
            </TableHead>
            {/* Predicted */}
            <TableHead className="text-xs font-semibold uppercase text-slate-500">
              <span className="text-violet-600 dark:text-violet-400">Delay (AI)</span>
            </TableHead>
            <TableHead className="text-xs font-semibold uppercase text-slate-500">
              <span className="text-violet-600 dark:text-violet-400">Conf.</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {flights.map((f) => (
            <TableRow
              key={f.id}
              className="border-slate-50 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40"
            >
              <TableCell className="font-mono font-semibold">
                <Link
                  href={`/flights/${f.id}`}
                  className="text-sky-600 hover:underline dark:text-sky-400"
                >
                  {f.flight_code}
                </Link>
              </TableCell>
              <TableCell className="text-sm text-slate-600 dark:text-slate-300">{f.airline}</TableCell>
              <TableCell className="text-sm text-slate-600 dark:text-slate-300">
                {f.origin} → {f.destination}
              </TableCell>
              <TableCell className="font-mono text-sm text-slate-600 dark:text-slate-300">
                {formatTime(f.scheduled_time)}
              </TableCell>
              {/* Raw */}
              <TableCell>
                <StatusBadge label={f.status} variant={flightStatusVariant(f.status)} />
              </TableCell>
              <TableCell className="font-mono text-sm text-slate-500">{f.gate ?? "—"}</TableCell>
              {/* Reconciled */}
              <TableCell>
                {f.reconciled_status ? (
                  <div className="flex items-center gap-1">
                    <StatusBadge
                      label={f.reconciled_status}
                      variant={flightStatusVariant(f.reconciled_status)}
                    />
                    <ReconciledBadge />
                  </div>
                ) : (
                  <span className="text-xs text-slate-400">—</span>
                )}
              </TableCell>
              <TableCell>
                {f.reconciled_gate ? (
                  <div className="flex items-center gap-1">
                    <span className="font-mono text-sm">{f.reconciled_gate}</span>
                    <ReconciledBadge />
                  </div>
                ) : (
                  <span className="text-xs text-slate-400">—</span>
                )}
              </TableCell>
              {/* Predicted */}
              <TableCell>
                {f.predicted_arrival_delay_min != null ? (
                  <div className="flex items-center gap-1">
                    <span
                      className={`font-mono text-sm font-medium ${
                        f.predicted_arrival_delay_min > 30
                          ? "text-red-600"
                          : f.predicted_arrival_delay_min > 15
                          ? "text-amber-600"
                          : "text-emerald-600"
                      }`}
                    >
                      {formatDelay(f.predicted_arrival_delay_min)}
                    </span>
                    <PredictedBadge />
                  </div>
                ) : (
                  <span className="text-xs text-slate-400">—</span>
                )}
              </TableCell>
              <TableCell className="font-mono text-xs text-slate-500">
                {formatConfidence(f.prediction_confidence)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
