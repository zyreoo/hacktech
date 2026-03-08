// ─── Shared primitives ────────────────────────────────────────────────────────

export type FlightStatus =
  | "scheduled"
  | "boarding"
  | "departed"
  | "delayed"
  | "cancelled"
  | "arrived"
  | string;

export type AlertSeverity = "info" | "warning" | "critical" | string;
export type PredictionOutcome =
  | "ml_model"
  | "rules_fallback"
  | "insufficient_data"
  | string;
export type ResourceStatus = "available" | "assigned" | "maintenance" | string;
export type RunwayStatus = "active" | "closed" | "maintenance" | string;
export type VerificationStatus = "verified" | "pending" | "failed" | string;
export type OrderStatus = "placed" | "prepared" | "picked_up" | string;
export type ServiceStatus = "pending" | "in_progress" | "completed" | string;
export type InfrastructureStatus = "operational" | "degraded" | "offline" | string;

// ─── Flight ───────────────────────────────────────────────────────────────────

export interface Flight {
  id: number;
  flight_code: string;
  airline: string;
  origin: string;
  destination: string;
  scheduled_time: string;
  estimated_time: string | null;
  status: FlightStatus;
  gate: string | null;
  stand: string | null;
  runway_id: number | null;
  // AI / Prediction fields
  predicted_eta: string | null;
  predicted_arrival_delay_min: number | null;
  prediction_confidence: number | null;
  prediction_model_version: string | null;
  last_prediction_at: string | null;
  // Reconciliation fields
  reconciled_eta: string | null;
  reconciled_status: string | null;
  reconciled_gate: string | null;
  reconciliation_reason: string | null;
  reconciliation_confidence: number | null;
  last_reconciled_at: string | null;
}

// ─── Flight Updates (AODB multi-source) ───────────────────────────────────────

export interface FlightUpdate {
  id: number;
  flight_id: number;
  source_name: string;
  reported_eta: string | null;
  reported_status: string | null;
  reported_gate: string | null;
  reported_at: string;
  confidence_score: number | null;
}

// ─── Prediction ───────────────────────────────────────────────────────────────

export interface ReasonCode {
  factor: string;
  contribution: number;
}

export interface OperationalReasonCode {
  factor: string;
  contribution: number;
  operational_code: string;
  operational_phrase: string;
}

export interface PredictRequest {
  flight_id: number;
}

export interface PredictResponse {
  flight_id: number;
  prediction_timestamp: string;
  model_version: string;
  predicted_arrival_delay_min: number;
  predicted_arrival_time: string | null;
  confidence_score: number | null;
  prediction_outcome: PredictionOutcome | null;
  fallback_used: boolean;
  input_quality_score: number | null;
  missing_features: string[];
  stale_data_warnings: string[];
  operational_reason_codes: OperationalReasonCode[] | null;
  reason_codes: ReasonCode[];
  features_used: Record<string, unknown> | null;
}

export interface PredictionAudit {
  id: number;
  flight_id: number;
  prediction_timestamp: string;
  model_version: string;
  predicted_arrival_delay_min: number;
  predicted_arrival_time: string | null;
  confidence_score: number | null;
  reason_codes: ReasonCode[] | null;
  created_at: string;
  prediction_outcome: PredictionOutcome | null;
  input_quality_score: number | null;
  missing_features: string[] | null;
  stale_data_warnings: string[] | null;
  operational_reason_codes: OperationalReasonCode[] | null;
}

export interface PredictionIssue {
  type: string;
  prediction_id: number;
  flight_id: number;
  message: string;
  severity: string;
  suggested_action: string;
}

// ─── Passenger Flow ───────────────────────────────────────────────────────────

export interface PassengerFlowIssue {
  type: string;
  flow_id: number;
  flight_id: number;
  message: string;
  severity: string;
  suggested_action: string;
}

export interface PassengerFlow {
  id: number;
  flight_id: number;
  check_in_count: number;
  security_queue_count: number;
  boarding_count: number;
  predicted_queue_time: number | null;
  terminal_zone: string | null;
  timestamp: string;
}

// ─── Runway ───────────────────────────────────────────────────────────────────

export interface Runway {
  id: number;
  runway_code: string;
  status: RunwayStatus;
  surface_condition: string | null;
  contamination_level: number | null;
  grip_score: number | null;
  hazard_detected: boolean;
  hazard_type: string | null;
  last_inspection_time: string | null;
}

export interface RunwayIssue {
  type: string;
  runway_id: number;
  runway_code: string;
  flight_id: number | null;
  flight_code: string | null;
  message: string;
  severity: string;
  suggested_action: string;
}

// ─── Resource ─────────────────────────────────────────────────────────────────

export interface Resource {
  id: number;
  resource_name: string;
  resource_type: string;
  status: ResourceStatus;
  assigned_to: string | null;
  location: string | null;
}

export interface ResourceIssue {
  type: string;
  resource_id: number | null;
  resource_name: string;
  flight_id: number | null;
  flight_code: string | null;
  message: string;
  severity: string;
  suggested_action: string;
}

// ─── Alert ────────────────────────────────────────────────────────────────────

export interface Alert {
  id: number;
  alert_type: string;
  severity: AlertSeverity;
  source_module: string | null;
  message: string;
  related_entity_type: string | null;
  related_entity_id: string | null;
  created_at: string;
  resolved: boolean;
  uniqueness_key: string | null;
  /** Operator-friendly suggested action (suggest only; system does not execute). */
  suggested_action: string | null;
}

export interface AlertIssue {
  type: string;
  alert_id: number;
  message: string;
  severity: string;
  suggested_action: string;
  related_entity_type: string | null;
  related_entity_id: string | null;
}

export interface FlightIssue {
  type: string;
  flight_id: number;
  flight_code: string | null;
  runway_id: number | null;
  runway_code: string | null;
  gate: string | null;
  message: string;
  severity: string;
  suggested_action: string;
}

// ─── Infrastructure ───────────────────────────────────────────────────────────

export interface InfrastructureIssue {
  type: string;
  asset_id: number;
  asset_name: string;
  message: string;
  severity: string;
  suggested_action: string;
}

export interface InfrastructureAsset {
  id: number;
  asset_name: string;
  asset_type: string;
  status: InfrastructureStatus;
  network_health: number | null;
  tamper_detected: boolean;
  location: string | null;
  last_updated: string | null;
}

// ─── Passenger Services ───────────────────────────────────────────────────────

export interface ServiceIssue {
  type: string;
  service_id: number;
  passenger_reference: string;
  message: string;
  severity: string;
  suggested_action: string;
}

export interface PassengerService {
  id: number;
  passenger_reference: string;
  service_type: string;
  status: ServiceStatus;
  request_time: string;
  completion_time: string | null;
  location: string | null;
}

// ─── Digital Identity ─────────────────────────────────────────────────────────

export interface DigitalIdentityStatus {
  id: number;
  passenger_reference: string;
  verification_status: VerificationStatus;
  verification_method: string | null;
  last_verified_at: string | null;
  token_reference: string | null;
}

// ─── Retail ───────────────────────────────────────────────────────────────────

export interface RetailEvent {
  id: number;
  passenger_reference: string;
  offer_type: string | null;
  order_status: OrderStatus;
  pickup_gate: string | null;
  created_at: string;
}

// ─── Overview ─────────────────────────────────────────────────────────────────

export interface OverviewResponse {
  current_flights: Flight[];
  passenger_queues: PassengerFlow[];
  runway_conditions: Runway[];
  active_alerts: Alert[];
  resource_status: Resource[];
  infrastructure_status: InfrastructureAsset[];
  service_requests: PassengerService[];
  identity_verification_counts: Record<string, number>;
  retail_activity: RetailEvent[];
}
