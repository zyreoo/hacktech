import { get, post } from "./client";
import type {
  OverviewResponse,
  Flight,
  FlightUpdate,
  Alert,
  Runway,
  Resource,
  PassengerFlow,
  InfrastructureAsset,
  PassengerService,
  DigitalIdentityStatus,
  RetailEvent,
  PredictionAudit,
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

// ─── Alerts ───────────────────────────────────────────────────────────────────

export const fetchAlerts = (params?: { resolved?: boolean; limit?: number }) =>
  get<Alert[]>("/alerts", params);

// ─── Runways ──────────────────────────────────────────────────────────────────

export const fetchRunways = () => get<Runway[]>("/runways");

// ─── Resources ────────────────────────────────────────────────────────────────

export const fetchResources = (params?: { limit?: number }) =>
  get<Resource[]>("/resources", params);

// ─── Passenger Flow ───────────────────────────────────────────────────────────

export const fetchPassengerFlow = (params?: { limit?: number }) =>
  get<PassengerFlow[]>("/passenger-flow", params);

// ─── Infrastructure ───────────────────────────────────────────────────────────

export const fetchInfrastructure = () =>
  get<InfrastructureAsset[]>("/infrastructure");

// ─── Services ─────────────────────────────────────────────────────────────────

export const fetchServices = (params?: { limit?: number }) =>
  get<PassengerService[]>("/services", params);

// ─── Identity ─────────────────────────────────────────────────────────────────

export const fetchIdentity = (params?: { limit?: number }) =>
  get<DigitalIdentityStatus[]>("/identity", params);

// ─── Retail ───────────────────────────────────────────────────────────────────

export const fetchRetail = (params?: { limit?: number }) =>
  get<RetailEvent[]>("/retail", params);

// ─── Predictions ──────────────────────────────────────────────────────────────

export const fetchPredictions = (params?: { skip?: number; limit?: number }) =>
  get<PredictionAudit[]>("/predictions", params);

export const fetchPredictionsForFlight = (flightId: number) =>
  get<PredictionAudit[]>(`/predictions/flights/${flightId}`);

export const runPrediction = (body: PredictRequest) =>
  post<PredictResponse, PredictRequest>("/predict", body);
