"""
Airport Data Hub - Pydantic schemas for API request/response.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator


# ----- Flights -----
class FlightBase(BaseModel):
    flight_code: str
    airline: str
    origin: str
    destination: str
    scheduled_time: datetime
    estimated_time: Optional[datetime] = None
    status: str = "scheduled"
    gate: Optional[str] = None
    stand: Optional[str] = None
    runway_id: Optional[int] = None


class FlightCreate(FlightBase):
    pass


class FlightResponse(FlightBase):
    id: int
    predicted_eta: Optional[datetime] = None
    reconciled_eta: Optional[datetime] = None
    reconciled_status: Optional[str] = None
    reconciled_gate: Optional[str] = None
    reconciliation_reason: Optional[str] = None
    reconciliation_confidence: Optional[float] = None
    last_reconciled_at: Optional[datetime] = None
    predicted_arrival_delay_min: Optional[float] = None
    prediction_confidence: Optional[float] = None
    prediction_model_version: Optional[str] = None
    last_prediction_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class FlightStatusUpdate(BaseModel):
    status: str


class FlightPredictionUpdate(BaseModel):
    """Pushed by arrival delay prediction to update AODB flight view."""
    predicted_eta: Optional[datetime] = None
    predicted_arrival_delay_min: Optional[float] = None
    prediction_confidence: Optional[float] = None
    prediction_model_version: Optional[str] = None


# ----- Arrival delay prediction -----
class ReasonCode(BaseModel):
    factor: str
    contribution: float


class OperationalReasonCode(BaseModel):
    """Airport-operations language explainability."""
    factor: str
    contribution: float
    operational_code: str
    operational_phrase: str


class PredictRequest(BaseModel):
    flight_id: int


class PredictResponse(BaseModel):
    flight_id: int
    prediction_timestamp: datetime
    model_version: str
    predicted_arrival_delay_min: float
    predicted_arrival_time: Optional[datetime] = None
    confidence_score: Optional[float] = None
    prediction_outcome: Optional[str] = None  # ml_model | rules_fallback | insufficient_data
    fallback_used: bool = False
    input_quality_score: Optional[float] = None
    missing_features: List[str] = []
    stale_data_warnings: List[str] = []
    operational_reason_codes: Optional[List[OperationalReasonCode]] = None
    reason_codes: List[ReasonCode] = []
    features_used: Optional[dict] = None


class PredictionAuditRead(BaseModel):
    id: int
    flight_id: int
    prediction_timestamp: datetime
    model_version: str
    predicted_arrival_delay_min: float
    predicted_arrival_time: Optional[datetime] = None
    confidence_score: Optional[float] = None
    reason_codes: Optional[List[ReasonCode]] = None
    created_at: datetime
    prediction_outcome: Optional[str] = None
    input_quality_score: Optional[float] = None
    missing_features: Optional[List[str]] = None
    stale_data_warnings: Optional[List[str]] = None
    operational_reason_codes: Optional[List[OperationalReasonCode]] = None
    model_config = ConfigDict(from_attributes=True)


# ----- FlightUpdate (AODB multi-source inputs) -----
class FlightUpdateCreate(BaseModel):
    flight_id: int
    source_name: str
    reported_eta: Optional[datetime] = None
    reported_status: Optional[str] = None
    reported_gate: Optional[str] = None
    reported_at: datetime
    confidence_score: Optional[float] = None


class FlightUpdateRead(BaseModel):
    id: int
    flight_id: int
    source_name: str
    reported_eta: Optional[datetime] = None
    reported_status: Optional[str] = None
    reported_gate: Optional[str] = None
    reported_at: datetime
    confidence_score: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


# ----- PassengerFlow -----
class PassengerFlowBase(BaseModel):
    flight_id: int
    check_in_count: int = 0
    security_queue_count: int = 0
    boarding_count: int = 0
    predicted_queue_time: Optional[float] = None
    terminal_zone: Optional[str] = None
    timestamp: Optional[datetime] = None


class PassengerFlowResponse(PassengerFlowBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# ----- Runways -----
class RunwayBase(BaseModel):
    runway_code: str
    status: str = "active"
    surface_condition: Optional[str] = None
    contamination_level: Optional[float] = None
    grip_score: Optional[float] = None
    hazard_detected: bool = False
    hazard_type: Optional[str] = None
    last_inspection_time: Optional[datetime] = None


class RunwayResponse(RunwayBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RunwayHazardUpdate(BaseModel):
    hazard_detected: bool
    hazard_type: Optional[str] = None


# ----- Resources -----
class ResourceBase(BaseModel):
    resource_name: str
    resource_type: str
    status: str = "available"
    assigned_to: Optional[str] = None
    location: Optional[str] = None


class ResourceResponse(ResourceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ResourceStatusUpdate(BaseModel):
    status: str
    assigned_to: Optional[str] = None


# ----- Alerts -----
# Operator-friendly suggested actions by alert_type (suggest only; system does not execute).
ALERT_SUGGESTED_ACTIONS: dict[str, str] = {
    "queue": "Deploy extra security lanes or redirect passengers to reduce queue depth; monitor wait times.",
    "runway_hazard": "Inspect runway and clear hazard; consider temporary closure until cleared.",
    "grip": "Schedule runway surface treatment or restrict operations until grip improves.",
    "security": "Verify asset integrity and secure area; escalate to security if tamper confirmed.",
    "gate_conflict": "Reassign gate for one of the flights or adjust schedule to resolve overlap.",
}


def get_suggested_action(alert_type: str) -> Optional[str]:
    """Return operator-friendly suggested action for an alert type, or None if unknown."""
    return ALERT_SUGGESTED_ACTIONS.get(alert_type)


class AlertBase(BaseModel):
    alert_type: str
    severity: str = "info"
    source_module: Optional[str] = None
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None


class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    resolved: bool = False
    uniqueness_key: Optional[str] = None
    suggested_action: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_suggested_action_from_type(self) -> "AlertResponse":
        if self.suggested_action is None:
            self.suggested_action = get_suggested_action(self.alert_type)
        return self


class AlertResolveUpdate(BaseModel):
    resolved: bool = True


# ----- Infrastructure -----
class InfrastructureAssetBase(BaseModel):
    asset_name: str
    asset_type: str
    status: str = "operational"
    network_health: Optional[float] = None
    tamper_detected: bool = False
    location: Optional[str] = None
    last_updated: Optional[datetime] = None


class InfrastructureAssetResponse(InfrastructureAssetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class InfrastructureStatusUpdate(BaseModel):
    status: str
    tamper_detected: Optional[bool] = None
    network_health: Optional[float] = None


# ----- PassengerServices -----
class PassengerServiceBase(BaseModel):
    passenger_reference: str
    service_type: str
    status: str = "pending"
    request_time: datetime
    completion_time: Optional[datetime] = None
    location: Optional[str] = None


class PassengerServiceResponse(PassengerServiceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ----- DigitalIdentityStatus -----
class DigitalIdentityStatusBase(BaseModel):
    passenger_reference: str
    verification_status: str
    verification_method: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    token_reference: Optional[str] = None


class DigitalIdentityStatusResponse(DigitalIdentityStatusBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ----- RetailEvents -----
class RetailEventBase(BaseModel):
    passenger_reference: str
    offer_type: Optional[str] = None
    order_status: str = "placed"
    pickup_gate: Optional[str] = None
    created_at: Optional[datetime] = None


class RetailEventResponse(RetailEventBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----- Overview (unified snapshot) -----
class OverviewResponse(BaseModel):
    """Unified airport operations snapshot for dashboard / modules."""
    current_flights: List[FlightResponse] = []
    passenger_queues: List[PassengerFlowResponse] = []
    runway_conditions: List[RunwayResponse] = []
    active_alerts: List[AlertResponse] = []
    resource_status: List[ResourceResponse] = []
    infrastructure_status: List[InfrastructureAssetResponse] = []
    service_requests: List[PassengerServiceResponse] = []
    identity_verification_counts: dict = {}  # e.g. {"verified": 10, "pending": 2}
    retail_activity: List[RetailEventResponse] = []
