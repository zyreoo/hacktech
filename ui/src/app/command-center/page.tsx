"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { SummaryMetricsBar } from "@/components/command-center/summary-metrics-bar";
import { LayerControls, DEFAULT_LAYERS, type LayerVisibility } from "@/components/command-center/layer-controls";
import { AirportDigitalTwinMap } from "@/components/command-center/airport-digital-twin-map";
import { AlertsPanel } from "@/components/command-center/alerts-panel";
import { IntelligenceDrawer, type DrawerSubject } from "@/components/command-center/intelligence-drawer";
import { EventTimeline } from "@/components/command-center/event-timeline";
import { AIInsightsPanel } from "@/components/command-center/ai-insights-panel";
import { CardLoadingState, SpinnerLoader } from "@/components/shared/loading-state";
import { ErrorState } from "@/components/shared/error-state";
import {
  useOverview,
  useAlerts,
  usePassengerFlow,
  useInfrastructure,
  usePredictions,
} from "@/lib/hooks/queries";
import {
  useOverviewWithSimulation,
  useFlightsWithSimulation,
  useRunwaysWithSimulation,
  usePassengerFlowWithSimulation,
} from "@/lib/hooks/simulation-data";
import {
  buildTimelineEntries,
  entityKey,
  getSelfHealingIssues,
  getRecommendedActions,
  getSelfHealingIssueForSubject,
  getRecommendedActionsForSubject,
  getNeedsAttentionSummary,
  getQueueHotspots,
  type ResolutionStatus,
} from "@/lib/command-center/selectors";
import {
  getImpactForSubject,
  getImpactConnectionLines,
} from "@/lib/command-center/impact-selectors";
import { SelfHealingCenter } from "@/components/command-center/self-healing-center";
import { RecommendedActionsPanel } from "@/components/command-center/recommended-actions-panel";
import { OperationalImpactPanel } from "@/components/command-center/operational-impact-panel";
import { SimulationControls } from "@/components/command-center/simulation-controls";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/modern-ui/tabs";
import type { Flight, Alert, Runway, InfrastructureAsset } from "@/types/api";

export default function CommandCenterPage() {
  const [layerVisibility, setLayerVisibility] = useState<LayerVisibility>(DEFAULT_LAYERS);
  const [selectedEntity, setSelectedEntity] = useState<{ type: string; id: string } | null>(null);
  const [drawerSubject, setDrawerSubject] = useState<DrawerSubject>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [resolutionState, setResolutionState] = useState<Record<string, ResolutionStatus>>({});
  const [dismissedActionIds, setDismissedActionIds] = useState<Set<string>>(new Set());

  const overview = useOverviewWithSimulation();
  const alertsQuery = useAlerts({ resolved: false, limit: 100 });
  const flightsQuery = useFlightsWithSimulation({ limit: 200 });
  const runwaysQuery = useRunwaysWithSimulation();
  const passengerFlowQuery = usePassengerFlowWithSimulation({ limit: 100 });
  const infrastructureQuery = useInfrastructure();
  const predictionsQuery = usePredictions({ limit: 50 });

  const isLoading =
    overview.isLoading ||
    alertsQuery.isLoading ||
    flightsQuery.isLoading ||
    runwaysQuery.isLoading;
  const isError = overview.isError;
  const dataUpdatedAt = overview.dataUpdatedAt;

  useEffect(() => {
    if (dataUpdatedAt) setLastRefresh(new Date(dataUpdatedAt));
  }, [dataUpdatedAt]);

  const handleVisibilityChange = useCallback((key: keyof LayerVisibility, value: boolean) => {
    setLayerVisibility((prev) => ({ ...prev, [key]: value }));
  }, []);

  const flights = flightsQuery.data ?? overview.data?.current_flights ?? [];
  const alerts = alertsQuery.data ?? overview.data?.active_alerts ?? [];
  const runways = runwaysQuery.data ?? overview.data?.runway_conditions ?? [];
  const passengerFlows = passengerFlowQuery.data ?? overview.data?.passenger_queues ?? [];
  const infrastructure = infrastructureQuery.data ?? overview.data?.infrastructure_status ?? [];

  const operationalImpact = useMemo(
    () =>
      getImpactForSubject(drawerSubject, {
        flights,
        runways,
        passengerFlows,
        infrastructure,
        queueHotspots: getQueueHotspots(passengerFlows),
      }),
    [drawerSubject, flights, runways, passengerFlows, infrastructure]
  );
  const impactConnectionLines = useMemo(
    () => getImpactConnectionLines(operationalImpact, flights, runways, infrastructure),
    [operationalImpact, flights, runways, infrastructure]
  );
  const impactHighlight = useMemo(() => {
    if (!operationalImpact) return undefined;
    return {
      affectedFlightIds: operationalImpact.affectedFlightIds,
      affectedRunwayIds: operationalImpact.affectedRunwayIds,
    };
  }, [operationalImpact]);

  const timelineEntries = useMemo(
    () =>
      buildTimelineEntries(
        alerts,
        predictionsQuery.data ?? undefined,
        flights
      ),
    [alerts, predictionsQuery.data, flights]
  );

  const selfHealingIssues = useMemo(
    () => getSelfHealingIssues(flights, infrastructure),
    [flights, infrastructure]
  );

  const recommendedActionsAll = useMemo(
    () => getRecommendedActions(overview.data),
    [overview.data]
  );
  const recommendedActions = useMemo(
    () => recommendedActionsAll.filter((a) => !dismissedActionIds.has(a.id)),
    [recommendedActionsAll, dismissedActionIds]
  );

  const resolutionStatusForSubject = useCallback(
    (subject: DrawerSubject): ResolutionStatus | undefined => {
      if (!subject || !("data" in subject) || !subject.data) return undefined;
      const id = "id" in subject.data ? String(subject.data.id) : "";
      return resolutionState[entityKey(subject.type, id)] ?? "new";
    },
    [resolutionState]
  );
  const setResolutionStatusForSubject = useCallback(
    (subject: DrawerSubject, status: ResolutionStatus) => {
      if (!subject || !("data" in subject) || !subject.data) return;
      const id = "id" in subject.data ? String(subject.data.id) : "";
      setResolutionState((s) => ({ ...s, [entityKey(subject.type, id)]: status }));
    },
    []
  );

  const handleSelectFlight = useCallback(
    (flight: Flight) => {
      setSelectedEntity({ type: "flight", id: String(flight.id) });
      setDrawerSubject({ type: "flight", data: flight });
      setSelectedAlertId(null);
    },
    []
  );

  const handleSelectAlert = useCallback((alert: Alert) => {
    setSelectedAlertId(alert.id);
    setSelectedEntity({ type: "alert", id: String(alert.id) });
    setDrawerSubject({ type: "alert", data: alert });
  }, []);

  const handleSelectRunway = useCallback((runway: Runway) => {
    setSelectedEntity({ type: "runway", id: String(runway.id) });
    setDrawerSubject({ type: "runway", data: runway });
  }, []);

  const handleSelectInfrastructure = useCallback((asset: InfrastructureAsset) => {
    setSelectedEntity({ type: "infrastructure", id: String(asset.id) });
    setDrawerSubject({ type: "infrastructure", data: asset });
  }, []);

  const handleFocusEntity = useCallback(
    (type: string, id: string) => {
      setSelectedEntity({ type, id });
      if (type === "flight") {
        const flight = flights.find((f) => String(f.id) === id);
        if (flight) setDrawerSubject({ type: "flight", data: flight });
      } else if (type === "alert") {
        const alert = alerts.find((a) => String(a.id) === id);
        if (alert) setDrawerSubject({ type: "alert", data: alert });
      } else if (type === "runway") {
        const runway = runways.find((r) => String(r.id) === id);
        if (runway) setDrawerSubject({ type: "runway", data: runway });
      } else if (type === "infrastructure") {
        const asset = infrastructure.find((a) => String(a.id) === id);
        if (asset) setDrawerSubject({ type: "infrastructure", data: asset });
      } else if (type === "zone") {
        setDrawerSubject(null);
      }
    },
    [flights, alerts, runways, infrastructure]
  );

  const handleMapClick = useCallback(() => {
    setSelectedEntity(null);
    setDrawerSubject(null);
    setSelectedAlertId(null);
  }, []);

  if (isError) {
    return (
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title="Command Center" subtitle="Digital twin operations" />
        <main className="flex-1 p-6">
          <ErrorState
            message="Could not load command center data. Is the backend running?"
            onRetry={() => overview.refetch()}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col min-h-0 bg-background">
      <Header
        title="Command Center"
        subtitle="Airport digital twin · Live operations"
      />
      <SummaryMetricsBar
        overview={overview.data}
        lastRefresh={lastRefresh}
        isLoading={overview.isLoading}
        needsAttention={
          overview.data
            ? getNeedsAttentionSummary(overview.data, selfHealingIssues.length)
            : null
        }
      />
      <main className="flex min-h-0 flex-1 flex-col overflow-auto p-2">
        {isLoading && !overview.data ? (
          <div className="flex flex-1 items-center justify-center">
            <CardLoadingState rows={4} />
            <SpinnerLoader />
          </div>
        ) : (
          <div className="flex gap-2 min-h-[calc(100vh-11rem)]">
            {/* Left: Alerts (slim, scrollable) */}
            <div className="w-56 shrink-0 min-h-0 flex flex-col overflow-hidden self-stretch max-h-[calc(100vh-11rem)]">
              <AlertsPanel
              alerts={alerts}
              selectedAlertId={selectedAlertId}
              onSelectAlert={handleSelectAlert}
              onFocusEntity={handleFocusEntity}
              className="flex-1 min-h-0 w-full"
            />
            </div>

            {/* Center: Map hero + tabbed lower section (scrollable column) */}
            <div className="flex min-w-0 flex-1 flex-col gap-2 min-h-0 overflow-auto">
              <div className="flex flex-wrap items-center justify-end gap-2">
                <SimulationControls flights={flights} runways={runways} className="w-72 max-w-full" />
                <LayerControls
                  visibility={layerVisibility}
                  onVisibilityChange={handleVisibilityChange}
                />
              </div>
              <div
                className="min-h-[68vh] flex-1 rounded-xl shadow-xl"
                style={{ minHeight: "520px" }}
              >
                <AirportDigitalTwinMap
                  flights={flights}
                  alerts={alerts}
                  runways={runways}
                  passengerFlows={passengerFlows}
                  infrastructure={infrastructure}
                  layerVisibility={layerVisibility}
                  selectedEntity={selectedEntity}
                  onSelectFlight={handleSelectFlight}
                  onSelectAlert={handleSelectAlert}
                  onSelectRunway={handleSelectRunway}
                  onSelectInfrastructure={handleSelectInfrastructure}
                  onMapClick={handleMapClick}
                  impactHighlight={impactHighlight}
                  connectionLines={impactConnectionLines}
                  className="h-full min-h-[520px]"
                />
              </div>
              {/* Bottom: Tabbed section */}
              <Tabs defaultValue="timeline" className="shrink-0">
                <TabsList className="h-9 w-full justify-start rounded-lg bg-muted/60 p-1">
                  <TabsTrigger value="timeline" className="text-xs">
                    Timeline
                  </TabsTrigger>
                  <TabsTrigger value="impact" className="text-xs">
                    Impact
                  </TabsTrigger>
                  <TabsTrigger value="insights" className="text-xs">
                    Insights
                  </TabsTrigger>
                  <TabsTrigger value="self-healing" className="text-xs">
                    Self-healing
                  </TabsTrigger>
                  <TabsTrigger value="actions" className="text-xs">
                    Actions
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="timeline" className="mt-2 max-h-[200px] overflow-auto">
                  <EventTimeline
                    entries={timelineEntries}
                    onSelectEntity={handleFocusEntity}
                  />
                </TabsContent>
                <TabsContent value="impact" className="mt-2 max-h-[200px] overflow-auto">
                  <OperationalImpactPanel impact={operationalImpact ?? null} />
                </TabsContent>
                <TabsContent value="insights" className="mt-2 max-h-[200px] overflow-auto">
                  <AIInsightsPanel overview={overview.data} onSelectAlert={() => {}} />
                </TabsContent>
                <TabsContent value="self-healing" className="mt-2 max-h-[200px] overflow-auto">
                  <SelfHealingCenter
                    issues={selfHealingIssues}
                    onFocusEntity={handleFocusEntity}
                  />
                </TabsContent>
                <TabsContent value="actions" className="mt-2 max-h-[200px] overflow-auto">
                  <RecommendedActionsPanel
                    actions={recommendedActions}
                    onFocusEntity={handleFocusEntity}
                    onDismiss={(id) =>
                      setDismissedActionIds((s) => new Set(s).add(id))
                    }
                  />
                </TabsContent>
              </Tabs>
            </div>

            {/* Right: Intelligence drawer (scrollable) */}
            <div className="w-80 shrink-0 min-h-0 self-stretch max-h-[calc(100vh-11rem)] overflow-hidden flex flex-col">
              <IntelligenceDrawer
                subject={drawerSubject}
                onClose={() => {
                  setDrawerSubject(null);
                  setSelectedEntity(null);
                  setSelectedAlertId(null);
                }}
                resolutionStatus={
                  drawerSubject ? resolutionStatusForSubject(drawerSubject) : undefined
                }
                onResolutionChange={(status) =>
                  drawerSubject && setResolutionStatusForSubject(drawerSubject, status)
                }
                selfHealingIssue={
                  drawerSubject
                    ? getSelfHealingIssueForSubject(drawerSubject, selfHealingIssues)
                    : null
                }
                recommendedActions={
                  drawerSubject
                    ? getRecommendedActionsForSubject(drawerSubject, recommendedActions)
                    : []
                }
                operationalImpact={operationalImpact ?? null}
                className="flex-1 min-h-0"
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
