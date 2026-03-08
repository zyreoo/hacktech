"use client";

import { Header } from "@/components/layout/header";
import { StatusBadge } from "@/components/shared/status-badge";
import { SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import { EmptyState } from "@/components/shared/empty-state";
import { MetricCard } from "@/components/shared/metric-card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useServices, useServiceIssues, useIdentity, useRetail } from "@/lib/hooks/queries";
import { formatDateTime, verificationStatusVariant } from "@/lib/utils";
import { ShoppingBag, ShieldCheck, UserCog, Users, AlertTriangle } from "lucide-react";

const issueSeverityStyles: Record<string, string> = {
  high: "border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200",
  medium: "border-sky-200 bg-sky-50 dark:border-sky-900/50 dark:bg-sky-950/30 text-sky-800 dark:text-sky-200",
};

function serviceStatusVariant(status: string) {
  switch (status) {
    case "completed":   return "success";
    case "in_progress": return "info";
    case "pending":     return "warning";
    default:            return "muted";
  }
}

function orderStatusVariant(status: string) {
  switch (status) {
    case "picked_up":  return "success";
    case "prepared":   return "info";
    case "placed":     return "warning";
    default:           return "muted";
  }
}

export default function ServicesPage() {
  const { data: services = [], isLoading: loadingServices, isError: errServices, refetch: refetchServices } = useServices({ limit: 100 });
  const { data: issues = [], isLoading: issuesLoading } = useServiceIssues({ limit: 200 });
  const { data: identities = [], isLoading: loadingId, isError: errId } = useIdentity({ limit: 100 });
  const { data: retail = [], isLoading: loadingRetail, isError: errRetail } = useRetail({ limit: 100 });

  const identityCounts = {
    verified: identities.filter((i) => i.verification_status === "verified").length,
    pending:  identities.filter((i) => i.verification_status === "pending").length,
    failed:   identities.filter((i) => i.verification_status === "failed").length,
  };

  const retailCounts = {
    placed:     retail.filter((r) => r.order_status === "placed").length,
    prepared:   retail.filter((r) => r.order_status === "prepared").length,
    picked_up:  retail.filter((r) => r.order_status === "picked_up").length,
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header title="Services / Identity / Retail" subtitle="Passenger services, digital identity, and retail activity" />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Self-healing */}
        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 dark:text-slate-100">
            <ShieldCheck className="h-4 w-4 text-slate-500" />
            Self-healing
          </h2>
          {issuesLoading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/50 px-4 py-3 text-sm text-slate-500">
              Checking for issues…
            </div>
          )}
          {!issuesLoading && issues.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-emerald-50/50 dark:border-slate-700 dark:bg-emerald-950/20 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-200">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              No service issues. No stale pending requests.
            </div>
          )}
          {!issuesLoading && issues.length > 0 && (
            <ul className="mb-6 space-y-2">
              {issues.map((issue, i) => (
                <li
                  key={`${issue.type}-${issue.service_id}-${i}`}
                  className={`rounded-xl border px-4 py-3 text-sm ${issueSeverityStyles[issue.severity] ?? "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50"}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-medium">{issue.message}</p>
                      <p className="mt-1 text-xs opacity-90">{issue.suggested_action}</p>
                      <span className="mt-2 inline-block rounded bg-white/60 px-2 py-0.5 font-mono text-xs dark:bg-black/20">{issue.passenger_reference}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Summary KPIs */}
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MetricCard title="Service Requests" value={services.length} icon={UserCog} />
          <MetricCard title="ID Verified" value={identityCounts.verified} icon={ShieldCheck} highlight="success" />
          <MetricCard
            title="ID Pending / Failed"
            value={identityCounts.pending + identityCounts.failed}
            highlight={identityCounts.failed > 0 ? "danger" : identityCounts.pending > 0 ? "warning" : "default"}
            icon={Users}
          />
          <MetricCard title="Retail Orders" value={retail.length} icon={ShoppingBag} />
        </div>

        <Tabs defaultValue="services">
          <TabsList>
            <TabsTrigger value="services">Passenger Services ({services.length})</TabsTrigger>
            <TabsTrigger value="identity">Digital Identity ({identities.length})</TabsTrigger>
            <TabsTrigger value="retail">Retail ({retail.length})</TabsTrigger>
          </TabsList>

          {/* ── Services ── */}
          <TabsContent value="services" className="mt-4">
            {loadingServices && <SpinnerLoader />}
            {errServices && <ErrorState message="Could not load services." onRetry={() => refetchServices()} />}
            {!loadingServices && services.length === 0 && (
              <EmptyState icon={UserCog} title="No service requests" description="No passenger service requests found." />
            )}
            {services.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Passenger Ref</TableHead>
                      <TableHead>Service Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>Requested</TableHead>
                      <TableHead>Completed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {services.map((s) => (
                      <TableRow key={s.id} className="border-slate-100 dark:border-slate-800">
                        <TableCell className="font-mono text-xs">{s.passenger_reference}</TableCell>
                        <TableCell className="capitalize text-sm text-slate-700 dark:text-slate-300">{s.service_type}</TableCell>
                        <TableCell>
                          <StatusBadge label={s.status} variant={serviceStatusVariant(s.status)} dot />
                        </TableCell>
                        <TableCell className="text-sm text-slate-500">{s.location ?? "—"}</TableCell>
                        <TableCell className="text-xs text-slate-500">{formatDateTime(s.request_time)}</TableCell>
                        <TableCell className="text-xs text-slate-500">{formatDateTime(s.completion_time)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>

          {/* ── Identity ── */}
          <TabsContent value="identity" className="mt-4">
            {loadingId && <SpinnerLoader />}
            {errId && <ErrorState message="Could not load identity data." />}
            {/* Summary row */}
            {!loadingId && (
              <div className="mb-4 flex flex-wrap gap-3">
                {[
                  { label: "Verified", count: identityCounts.verified, variant: "success" as const },
                  { label: "Pending",  count: identityCounts.pending,  variant: "warning" as const },
                  { label: "Failed",   count: identityCounts.failed,   variant: "danger"  as const },
                ].map(({ label, count, variant }) => (
                  <div key={label} className="flex items-center gap-2 rounded-full border px-3 py-1">
                    <StatusBadge label={label} variant={variant} dot />
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            )}
            {!loadingId && identities.length === 0 && (
              <EmptyState icon={ShieldCheck} title="No identity records" />
            )}
            {identities.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Passenger Ref</TableHead>
                      <TableHead>Verification Status</TableHead>
                      <TableHead>Method</TableHead>
                      <TableHead>Last Verified</TableHead>
                      <TableHead>Token</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {identities.map((i) => (
                      <TableRow key={i.id} className="border-slate-100 dark:border-slate-800">
                        <TableCell className="font-mono text-xs">{i.passenger_reference}</TableCell>
                        <TableCell>
                          <StatusBadge
                            label={i.verification_status}
                            variant={verificationStatusVariant(i.verification_status)}
                            dot
                          />
                        </TableCell>
                        <TableCell className="text-sm capitalize text-slate-600 dark:text-slate-300">
                          {i.verification_method ?? "—"}
                        </TableCell>
                        <TableCell className="text-xs text-slate-500">{formatDateTime(i.last_verified_at)}</TableCell>
                        <TableCell className="max-w-[140px] truncate font-mono text-xs text-slate-400">
                          {i.token_reference ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>

          {/* ── Retail ── */}
          <TabsContent value="retail" className="mt-4">
            {loadingRetail && <SpinnerLoader />}
            {errRetail && <ErrorState message="Could not load retail data." />}
            {/* Summary */}
            {!loadingRetail && (
              <div className="mb-4 flex flex-wrap gap-3">
                {[
                  { label: "Placed",    count: retailCounts.placed,    variant: "warning" as const },
                  { label: "Prepared",  count: retailCounts.prepared,  variant: "info"    as const },
                  { label: "Picked Up", count: retailCounts.picked_up, variant: "success" as const },
                ].map(({ label, count, variant }) => (
                  <div key={label} className="flex items-center gap-2 rounded-full border px-3 py-1">
                    <StatusBadge label={label} variant={variant} dot />
                    <span className="font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            )}
            {!loadingRetail && retail.length === 0 && (
              <EmptyState icon={ShoppingBag} title="No retail activity" />
            )}
            {retail.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Passenger Ref</TableHead>
                      <TableHead>Offer Type</TableHead>
                      <TableHead>Order Status</TableHead>
                      <TableHead>Pickup Gate</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {retail.map((r) => (
                      <TableRow key={r.id} className="border-slate-100 dark:border-slate-800">
                        <TableCell className="font-mono text-xs">{r.passenger_reference}</TableCell>
                        <TableCell className="text-sm capitalize text-slate-700 dark:text-slate-300">
                          {r.offer_type ?? "—"}
                        </TableCell>
                        <TableCell>
                          <StatusBadge
                            label={r.order_status}
                            variant={orderStatusVariant(r.order_status)}
                            dot
                          />
                        </TableCell>
                        <TableCell className="font-mono text-sm text-slate-600 dark:text-slate-300">
                          {r.pickup_gate ?? "—"}
                        </TableCell>
                        <TableCell className="text-xs text-slate-500">{formatDateTime(r.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
