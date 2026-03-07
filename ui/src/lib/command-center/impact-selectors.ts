/**
 * Operational impact estimation (frontend-derived).
 * No backend APIs; uses existing flight, alert, runway, infrastructure, and queue data.
 */

import type { Flight, Runway, PassengerFlow, InfrastructureAsset } from "@/types/api";
import { GATE_MAP, getTerminalZone, getPointForGateOrStand, RUNWAY_POSITIONS } from "./map-config";
import type { MapPoint } from "./map-config";

export type ImpactSeverity = "low" | "moderate" | "high" | "critical";

export interface ImpactChainNode {
  id: string;
  label: string;
  type: "source" | "propagation" | "outcome";
  entityType?: string;
  entityId?: string;
}

export interface OperationalImpact {
  /** Root cause label */
  rootLabel: string;
  /** Root entity type and id */
  rootType: string;
  rootId: string;
  /** Visual chain for Impact Graph */
  chain: ImpactChainNode[];
  /** Affected flight ids (for map highlighting) */
  affectedFlightIds: Set<number>;
  /** Affected runway ids */
  affectedRunwayIds: Set<number>;
  /** Severity */
  severity: ImpactSeverity;
  /** Short summary for panel */
  summary: string;
}

const DELAY_THRESHOLD_MIN = 15;
const GATE_CONFLICT_DELAY_MIN = 20;

/** Terminal from gate: use first char (A->T1, B->T2, C->T3) or GATE_MAP */
function getTerminalForGate(gate: string | null): string | null {
  if (!gate) return null;
  const pos = GATE_MAP.get(gate);
  if (pos) return pos.terminal;
  const c = gate.charAt(0).toUpperCase();
  if (c === "A") return "T1";
  if (c === "B") return "T2";
  if (c === "C") return "T3";
  if (gate.startsWith("S")) return "T1"; // default stand to T1
  return null;
}

/** Flights at same gate (potential gate conflict) */
function getFlightsAtGate(gate: string | null, flights: Flight[], excludeFlightId?: number): Flight[] {
  if (!gate) return [];
  return flights.filter(
    (f) => (f.gate === gate || f.stand === gate) && f.id !== excludeFlightId
  );
}

/** Flights in terminal (by gate prefix / GATE_MAP) */
function getFlightsInTerminal(terminalId: string, flights: Flight[]): Flight[] {
  return flights.filter((f) => getTerminalForGate(f.gate ?? f.stand) === terminalId);
}

function deriveSeverity(
  affectedCount: number,
  alertSeverity?: string,
  confidence?: number | null
): ImpactSeverity {
  if (alertSeverity === "critical" || (confidence != null && confidence < 0.5 && affectedCount > 0))
    return "critical";
  if (affectedCount >= 5 || alertSeverity === "warning") return "high";
  if (affectedCount >= 2) return "moderate";
  return "low";
}

/** Build impact for a delayed flight: gate conflict, next flight, connection risk */
export function getImpactForFlight(
  flight: Flight,
  allFlights: Flight[]
): OperationalImpact | null {
  const delayMin = flight.predicted_arrival_delay_min ?? (flight.status === "delayed" ? 30 : 0);
  if (delayMin < DELAY_THRESHOLD_MIN) return null;

  const gate = flight.gate ?? flight.stand ?? null;
  const sameGateFlights = getFlightsAtGate(gate, allFlights, flight.id);
  const chain: ImpactChainNode[] = [
    { id: "root", label: `${flight.flight_code} delayed ${Math.round(delayMin)} min`, type: "source", entityType: "flight", entityId: String(flight.id) },
  ];
  const affectedFlightIds = new Set<number>();

  if (gate) {
    chain.push({ id: "gate", label: `Gate ${gate} occupied longer`, type: "propagation" });
    sameGateFlights.forEach((f) => {
      affectedFlightIds.add(f.id);
      chain.push({ id: `f-${f.id}`, label: `${f.flight_code} cannot dock`, type: "outcome", entityType: "flight", entityId: String(f.id) });
    });
  }
  if (affectedFlightIds.size > 0 || delayMin >= 30) {
    chain.push({ id: "conn", label: "Passenger connection risk", type: "outcome" });
  }

  const severity = deriveSeverity(
    affectedFlightIds.size + 1,
    undefined,
    flight.prediction_confidence
  );
  const summary =
    affectedFlightIds.size > 0
      ? `Gate ${gate ?? "—"} conflict: ${affectedFlightIds.size} flight(s) affected.`
      : `Delay may cause gate hold and connection risk.`;

  return {
    rootLabel: `${flight.flight_code} delay`,
    rootType: "flight",
    rootId: String(flight.id),
    chain,
    affectedFlightIds: new Set([flight.id, ...affectedFlightIds]),
    affectedRunwayIds: new Set(),
    severity,
    summary,
  };
}

/** Build impact for runway issue: arrival spacing, inbound delays */
export function getImpactForRunway(
  runway: Runway,
  allRunways: Runway[],
  allFlights: Flight[]
): OperationalImpact | null {
  const isIssue = runway.status !== "active" || runway.hazard_detected;
  if (!isIssue) return null;

  const chain: ImpactChainNode[] = [
    { id: "root", label: `${runway.runway_code} ${runway.hazard_detected ? "hazard" : runway.status}`, type: "source", entityType: "runway", entityId: String(runway.id) },
    { id: "p1", label: "Arrival spacing increased", type: "propagation" },
    { id: "p2", label: "Multiple inbound flights delayed", type: "outcome" },
  ];
  const affectedFlightIds = new Set(
    allFlights.filter((f) => f.runway_id === runway.id).map((f) => f.id)
  );
  affectedFlightIds.forEach((id) => {
    const f = allFlights.find((x) => x.id === id);
    if (f) chain.push({ id: `f-${id}`, label: f.flight_code, type: "outcome", entityType: "flight", entityId: String(id) });
  });

  const severity = deriveSeverity(affectedFlightIds.size, "warning");
  const summary =
    affectedFlightIds.size > 0
      ? `${affectedFlightIds.size} flight(s) may be delayed.`
      : "Runway capacity reduced; expect delays.";

  return {
    rootLabel: `Runway ${runway.runway_code}`,
    rootType: "runway",
    rootId: String(runway.id),
    chain,
    affectedFlightIds,
    affectedRunwayIds: new Set([runway.id]),
    severity,
    summary,
  };
}

/** Build impact for queue hotspot: boarding delays, late pax */
export function getImpactForQueueHotspot(
  zoneId: string,
  flows: PassengerFlow[],
  allFlights: Flight[]
): OperationalImpact | null {
  const zoneFlows = flows.filter(
    (f) => f.terminal_zone === zoneId || f.terminal_zone?.includes(zoneId)
  );
  const totalQueue = zoneFlows.reduce(
    (s, f) => s + f.check_in_count + f.security_queue_count + f.boarding_count,
    0
  );
  if (totalQueue < 80) return null;

  const terminalId = zoneId.startsWith("T") ? zoneId : `T${zoneId}`;
  const flightsInTerminal = getFlightsInTerminal(terminalId, allFlights);
  const chain: ImpactChainNode[] = [
    { id: "root", label: `${zoneId} queue overload (${totalQueue} pax)`, type: "source" },
    { id: "p1", label: "Security / check-in congestion", type: "propagation" },
    { id: "p2", label: "Boarding delays, late passenger arrivals", type: "outcome" },
  ];
  flightsInTerminal.slice(0, 5).forEach((f) => {
    chain.push({ id: `f-${f.id}`, label: f.flight_code, type: "outcome", entityType: "flight", entityId: String(f.id) });
  });

  const severity = totalQueue >= 200 ? "high" : totalQueue >= 120 ? "moderate" : "low";
  return {
    rootLabel: `Queue ${zoneId}`,
    rootType: "zone",
    rootId: zoneId,
    chain,
    affectedFlightIds: new Set(flightsInTerminal.map((f) => f.id)),
    affectedRunwayIds: new Set(),
    severity: severity as ImpactSeverity,
    summary: `${flightsInTerminal.length} flight(s) in terminal may experience boarding delays.`,
  };
}

/** Build impact for degraded infrastructure */
export function getImpactForInfrastructure(
  asset: InfrastructureAsset,
  allFlights: Flight[]
): OperationalImpact | null {
  const isIssue = asset.status !== "operational" || asset.tamper_detected;
  if (!isIssue) return null;

  const zone = getTerminalZone(asset.location);
  const terminalId = zone?.id ?? null;
  const affectedFlights = terminalId
    ? getFlightsInTerminal(terminalId, allFlights)
    : [];
  const chain: ImpactChainNode[] = [
    { id: "root", label: `${asset.asset_name} ${asset.status}`, type: "source", entityType: "infrastructure", entityId: String(asset.id) },
    { id: "p1", label: "Related equipment / area affected", type: "propagation" },
  ];
  affectedFlights.slice(0, 4).forEach((f) => {
    chain.push({ id: `f-${f.id}`, label: f.flight_code, type: "outcome", entityType: "flight", entityId: String(f.id) });
  });

  const severity = asset.tamper_detected ? "critical" : asset.status === "offline" ? "high" : "moderate";
  return {
    rootLabel: asset.asset_name,
    rootType: "infrastructure",
    rootId: String(asset.id),
    chain,
    affectedFlightIds: new Set(affectedFlights.map((f) => f.id)),
    affectedRunwayIds: new Set(),
    severity: severity as ImpactSeverity,
    summary: affectedFlights.length > 0 ? `${affectedFlights.length} flight(s) in area may be impacted.` : "Asset out; verify coverage.",
  };
}

/** Get impact for current drawer subject (flight, runway, zone, infrastructure) */
export function getImpactForSubject(
  subject: { type: string; data: unknown } | null,
  context: {
    flights: Flight[];
    runways: Runway[];
    passengerFlows: PassengerFlow[];
    infrastructure: InfrastructureAsset[];
    queueHotspots?: { zone: string; level: string }[];
  }
): OperationalImpact | null {
  if (!subject) return null;
  if (subject.type === "flight") {
    return getImpactForFlight(subject.data as Flight, context.flights);
  }
  if (subject.type === "runway") {
    return getImpactForRunway(subject.data as Runway, context.runways, context.flights);
  }
  if (subject.type === "infrastructure") {
    return getImpactForInfrastructure(subject.data as InfrastructureAsset, context.flights);
  }
  if (subject.type === "zone" && context.queueHotspots) {
    const zoneId = (subject.data as { zone?: string }).zone ?? (subject.data as { id?: string }).id ?? "";
    return getImpactForQueueHotspot(zoneId, context.passengerFlows, context.flights);
  }
  return null;
}

/** Connection lines for map: from root entity to affected flights */
export function getImpactConnectionLines(
  impact: OperationalImpact | null,
  flights: Flight[],
  runways: Runway[],
  infrastructure?: InfrastructureAsset[]
): { from: MapPoint; to: MapPoint }[] {
  if (!impact || impact.affectedFlightIds.size === 0) return [];
  const lines: { from: MapPoint; to: MapPoint }[] = [];
  let fromPoint: MapPoint = { x: 500, y: 400 };

  if (impact.rootType === "flight") {
    const rootFlight = flights.find((f) => String(f.id) === impact.rootId);
    if (rootFlight) fromPoint = getPointForGateOrStand(rootFlight.gate ?? rootFlight.stand ?? null);
  } else if (impact.rootType === "runway") {
    const rw = runways.find((r) => String(r.id) === impact.rootId);
    const pos = rw ? RUNWAY_POSITIONS.find((p) => p.runwayCode === rw.runway_code) : null;
    if (pos) fromPoint = { x: (pos.start.x + pos.end.x) / 2, y: (pos.start.y + pos.end.y) / 2 };
  } else if (impact.rootType === "infrastructure" && infrastructure) {
    const asset = infrastructure.find((a) => String(a.id) === impact.rootId);
    const zone = asset ? getTerminalZone(asset.location) : null;
    if (zone) fromPoint = zone.center;
  }

  impact.affectedFlightIds.forEach((flightId) => {
    const f = flights.find((x) => x.id === flightId);
    if (f && String(f.id) !== impact.rootId) {
      const toPoint = getPointForGateOrStand(f.gate ?? f.stand ?? null);
      lines.push({ from: fromPoint, to: toPoint });
    }
  });
  return lines;
}
