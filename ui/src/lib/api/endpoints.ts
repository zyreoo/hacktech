import { get, post, patch } from "./client";
import type {
  OverviewResponse,
  Flight,
  FlightUpdate,
  Alert,
  AlertIssue,
  Runway,
  RunwayIssue,
  Resource,
  ResourceIssue,
  PassengerFlow,
  PassengerFlowIssue,
  InfrastructureAsset,
  InfrastructureIssue,
  PassengerService,
  ServiceIssue,
  DigitalIdentityStatus,
  RetailEvent,
  PredictionAudit,
  PredictionIssue,
  FlightIssue,
  PredictRequest,
  PredictResponse,
} from "@/types/api";

// ─── Overview ─────────────────────────────────────────────────────────────────

export const fetchOverview = () => get<OverviewResponse>("/overview");
export const fetchAodbOverview = () => get<OverviewResponse>("/aodb/overview");

// ─── Flights ──────────────────────────────────────────────────────────────────

export const fetchFlights = (params?: { skip?: number; limit?: number }) =>
  get<Flight[]>("/aodb/flights", params);

export const fetchFlight = (id: number) =>
  get<Flight>(`/aodb/flights/${id}`);

export const fetchFlightUpdates = (flightId: number) =>
  get<FlightUpdate[]>(`/flights/${flightId}/updates`);

export const fetchFlightIssues = (params?: { limit?: number }) =>
  get<FlightIssue[]>("/flights/issues", params);

export const reassignFlight = (id: number, body: { runway_id?: number; gate?: string; reconciled_gate?: string }) =>
  patch<Flight>(`/flights/${id}/reassign`, body);

// ─── Alerts ───────────────────────────────────────────────────────────────────

export const fetchAlerts = (params?: { resolved?: boolean; limit?: number }) =>
  get<Alert[]>("/alerts", params);

export const fetchAlertIssues = (params?: { limit?: number }) =>
  get<AlertIssue[]>("/alerts/issues", params);

export const resolveAlert = (id: number, resolved = true) =>
  patch<Alert>(`/alerts/${id}/resolve`, { resolved });

// ─── Runways ──────────────────────────────────────────────────────────────────

export const fetchRunways = () => get<Runway[]>("/runways");
export const fetchRunwayIssues = () => get<RunwayIssue[]>("/runways/issues");

export const updateRunwayStatus = (id: number, status: string) =>
  patch<Runway>(`/runways/${id}/status`, { status });

export const updateRunwayHazard = (id: number, hazard_detected: boolean, hazard_type?: string | null) =>
  patch<Runway>(`/runways/${id}/hazard`, { hazard_detected, hazard_type });

// ─── Resources ────────────────────────────────────────────────────────────────

export const fetchResources = (params?: { limit?: number }) =>
  get<Resource[]>("/resources", params);

export const fetchResourceIssues = () =>
  get<ResourceIssue[]>("/resources/issues");

export const updateResourceStatus = (id: number, status: string, assigned_to?: string | null) =>
  patch<Resource>(`/resources/${id}/status`, assigned_to === undefined ? { status } : { status, assigned_to });

// ─── Passenger Flow ───────────────────────────────────────────────────────────

export const fetchPassengerFlow = (params?: { limit?: number }) =>
  get<PassengerFlow[]>("/passenger-flow", params);

export const fetchPassengerFlowIssues = (params?: { limit?: number }) =>
  get<PassengerFlowIssue[]>("/passenger-flow/issues", params);

// ─── Infrastructure ───────────────────────────────────────────────────────────

export const fetchInfrastructure = () =>
  get<InfrastructureAsset[]>("/infrastructure");

export const fetchInfrastructureIssues = () =>
  get<InfrastructureIssue[]>("/infrastructure/issues");

export const updateInfrastructureStatus = (
  id: number,
  body: { status?: string; tamper_detected?: boolean; network_health?: number }
) => patch<InfrastructureAsset>(`/infrastructure/${id}/status`, body);

// ─── Services ─────────────────────────────────────────────────────────────────

export const fetchServices = (params?: { limit?: number }) =>
  get<PassengerService[]>("/services", params);

export const fetchServiceIssues = (params?: { limit?: number }) =>
  get<ServiceIssue[]>("/services/issues", params);

// ─── Identity ─────────────────────────────────────────────────────────────────

export const fetchIdentity = (params?: { limit?: number }) =>
  get<DigitalIdentityStatus[]>("/identity", params);

// ─── Retail ───────────────────────────────────────────────────────────────────

export const fetchRetail = (params?: { limit?: number }) =>
  get<RetailEvent[]>("/retail", params);

// ─── Predictions ──────────────────────────────────────────────────────────────

export const fetchPredictions = (params?: { skip?: number; limit?: number }) =>
  get<PredictionAudit[]>("/predictions", params);

export const fetchPredictionIssues = (params?: { limit?: number }) =>
  get<PredictionIssue[]>("/predictions/issues", params);

export const fetchPredictionsForFlight = (flightId: number) =>
  get<PredictionAudit[]>(`/predictions/flights/${flightId}`);

export const runPrediction = (body: PredictRequest) =>
  post<PredictResponse, PredictRequest>("/predict", body);
