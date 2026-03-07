import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { formatDateTime, formatConfidence, flightStatusVariant } from "@/lib/utils";
import type { FlightUpdate } from "@/types/api";

const SOURCE_COLORS: Record<string, string> = {
  airline:     "info",
  radar:       "success",
  airport_ops: "warning",
  manual:      "muted",
};

export function FlightUpdatesPanel({ updates }: { updates: FlightUpdate[] }) {
  if (updates.length === 0) {
    return <EmptyState title="No raw updates" description="No source data received yet." />;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Source</TableHead>
            <TableHead>Reported At</TableHead>
            <TableHead>Reported ETA</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Gate</TableHead>
            <TableHead>Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {updates.map((u) => (
            <TableRow key={u.id}>
              <TableCell>
                <StatusBadge
                  label={u.source_name}
                  variant={(SOURCE_COLORS[u.source_name] ?? "muted") as never}
                />
              </TableCell>
              <TableCell className="font-mono text-xs">{formatDateTime(u.reported_at)}</TableCell>
              <TableCell className="font-mono text-xs">{formatDateTime(u.reported_eta)}</TableCell>
              <TableCell>
                {u.reported_status ? (
                  <StatusBadge label={u.reported_status} variant={flightStatusVariant(u.reported_status)} />
                ) : (
                  <span className="text-xs text-slate-400">—</span>
                )}
              </TableCell>
              <TableCell className="font-mono text-sm">{u.reported_gate ?? "—"}</TableCell>
              <TableCell className="font-mono text-xs">{formatConfidence(u.confidence_score)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
