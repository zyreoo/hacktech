"""
Airport Data Hub - CRUD operations.
All data access goes through here so the hub stays the single source of truth.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from .models import (
    Flight,
    FlightUpdate,
    PassengerFlow,
    PredictionAudit,
    Runway,
    Resource,
    Alert,
    InfrastructureAsset,
    PassengerService,
    DigitalIdentityStatus,
    RetailEvent,
)
from .schemas import (
    FlightStatusUpdate,
    FlightPredictionUpdate,
    FlightUpdateCreate,
    RunwayHazardUpdate,
    RunwayStatusUpdate,
    ResourceStatusUpdate,
    AlertResolveUpdate,
    InfrastructureStatusUpdate,
)


# ----- Flights -----
def get_flights(db: Session, skip: int = 0, limit: int = 100) -> List[Flight]:
    return db.query(Flight).order_by(Flight.scheduled_time).offset(skip).limit(limit).all()


def get_flight_by_id(db: Session, id: int) -> Optional[Flight]:
    return db.query(Flight).filter(Flight.id == id).first()


def get_flight_by_code(db: Session, flight_code: str) -> Optional[Flight]:
    return db.query(Flight).filter(Flight.flight_code == flight_code).first()


def update_flight_status(db: Session, id: int, payload: FlightStatusUpdate) -> Optional[Flight]:
    flight = get_flight_by_id(db, id)
    if not flight:
        return None
    flight.status = payload.status
    db.commit()
    db.refresh(flight)
    return flight


def update_flight_prediction(db: Session, id: int, payload: FlightPredictionUpdate) -> Optional[Flight]:
    """Update flight with prediction results (prediction service or simulation/ops). Only updates fields present in payload (null clears delay)."""
    flight = get_flight_by_id(db, id)
    if not flight:
        return None
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(flight, key, value)
    flight.last_prediction_at = datetime.utcnow()
    db.commit()
    db.refresh(flight)
    return flight


def update_flight_reconciliation(
    db: Session,
    flight_id: int,
    reconciled_eta: Optional[datetime] = None,
    reconciled_status: Optional[str] = None,
    reconciled_gate: Optional[str] = None,
    reconciliation_reason: Optional[str] = None,
    reconciliation_confidence: Optional[float] = None,
) -> Optional[Flight]:
    """Write reconciled values for a flight (raw data stays in status/gate/estimated_time and FlightUpdate)."""
    flight = get_flight_by_id(db, flight_id)
    if not flight:
        return None
    if reconciled_eta is not None:
        flight.reconciled_eta = reconciled_eta
    if reconciled_status is not None:
        flight.reconciled_status = reconciled_status
    if reconciled_gate is not None:
        flight.reconciled_gate = reconciled_gate
    if reconciliation_reason is not None:
        flight.reconciliation_reason = reconciliation_reason
    if reconciliation_confidence is not None:
        flight.reconciliation_confidence = reconciliation_confidence
    flight.last_reconciled_at = datetime.utcnow()
    db.commit()
    db.refresh(flight)
    return flight


# ----- FlightUpdate (AODB multi-source inputs) -----
def create_flight_update(db: Session, payload: FlightUpdateCreate) -> FlightUpdate:
    u = FlightUpdate(
        flight_id=payload.flight_id,
        source_name=payload.source_name,
        reported_eta=payload.reported_eta,
        reported_status=payload.reported_status,
        reported_gate=payload.reported_gate,
        reported_at=payload.reported_at,
        confidence_score=payload.confidence_score,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_flight_updates_for_flight(db: Session, flight_id: int) -> List[FlightUpdate]:
    return db.query(FlightUpdate).filter(FlightUpdate.flight_id == flight_id).order_by(FlightUpdate.reported_at.desc()).all()


def list_flight_updates(db: Session, skip: int = 0, limit: int = 100) -> List[FlightUpdate]:
    return db.query(FlightUpdate).order_by(FlightUpdate.reported_at.desc()).offset(skip).limit(limit).all()


# ----- PredictionAudit (arrival delay) -----
def create_prediction_audit(
    db: Session,
    flight_id: int,
    prediction_timestamp: datetime,
    model_version: str,
    predicted_arrival_delay_min: float,
    predicted_arrival_time: Optional[datetime] = None,
    confidence_score: Optional[float] = None,
    reason_codes: Optional[str] = None,
    features_snapshot: Optional[str] = None,
    prediction_outcome: Optional[str] = None,
    input_quality_score: Optional[float] = None,
    missing_features: Optional[str] = None,
    stale_data_warnings: Optional[str] = None,
    operational_reason_codes: Optional[str] = None,
) -> PredictionAudit:
    a = PredictionAudit(
        flight_id=flight_id,
        prediction_timestamp=prediction_timestamp,
        model_version=model_version,
        predicted_arrival_delay_min=predicted_arrival_delay_min,
        predicted_arrival_time=predicted_arrival_time,
        confidence_score=confidence_score,
        reason_codes=reason_codes,
        features_snapshot=features_snapshot,
        prediction_outcome=prediction_outcome,
        input_quality_score=input_quality_score,
        missing_features=missing_features,
        stale_data_warnings=stale_data_warnings,
        operational_reason_codes=operational_reason_codes,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def get_latest_prediction_for_flight(db: Session, flight_id: int) -> Optional[PredictionAudit]:
    return db.query(PredictionAudit).filter(PredictionAudit.flight_id == flight_id).order_by(PredictionAudit.created_at.desc()).first()


def get_predictions_for_flight(db: Session, flight_id: int, limit: int = 20) -> List[PredictionAudit]:
    return db.query(PredictionAudit).filter(PredictionAudit.flight_id == flight_id).order_by(PredictionAudit.created_at.desc()).limit(limit).all()


def list_predictions(db: Session, skip: int = 0, limit: int = 50) -> List[PredictionAudit]:
    return db.query(PredictionAudit).order_by(PredictionAudit.created_at.desc()).offset(skip).limit(limit).all()


# ----- PassengerFlow -----
def get_passenger_flows(db: Session, skip: int = 0, limit: int = 200) -> List[PassengerFlow]:
    return db.query(PassengerFlow).order_by(PassengerFlow.timestamp.desc()).offset(skip).limit(limit).all()


def get_passenger_flow_by_flight(db: Session, flight_id: int) -> List[PassengerFlow]:
    return db.query(PassengerFlow).filter(PassengerFlow.flight_id == flight_id).order_by(PassengerFlow.timestamp.desc()).all()


# ----- Runways -----
def get_runways(db: Session) -> List[Runway]:
    return db.query(Runway).all()


def get_runway_by_id(db: Session, id: int) -> Optional[Runway]:
    return db.query(Runway).filter(Runway.id == id).first()


def update_runway_hazard(db: Session, id: int, payload: RunwayHazardUpdate) -> Optional[Runway]:
    runway = get_runway_by_id(db, id)
    if not runway:
        return None
    runway.hazard_detected = payload.hazard_detected
    runway.hazard_type = payload.hazard_type
    db.commit()
    db.refresh(runway)
    return runway


def update_runway_status(db: Session, id: int, payload: RunwayStatusUpdate) -> Optional[Runway]:
    """Simulation / ops: set runway status (active, closed, maintenance)."""
    runway = get_runway_by_id(db, id)
    if not runway:
        return None
    runway.status = payload.status
    db.commit()
    db.refresh(runway)
    return runway


# ----- Resources -----
def get_resources(db: Session, skip: int = 0, limit: int = 100) -> List[Resource]:
    return db.query(Resource).offset(skip).limit(limit).all()


def get_resource_by_id(db: Session, id: int) -> Optional[Resource]:
    return db.query(Resource).filter(Resource.id == id).first()


def update_resource_status(db: Session, id: int, payload: ResourceStatusUpdate) -> Optional[Resource]:
    resource = get_resource_by_id(db, id)
    if not resource:
        return None
    resource.status = payload.status
    if payload.assigned_to is not None:
        resource.assigned_to = payload.assigned_to
    db.commit()
    db.refresh(resource)
    return resource


# ----- Alerts -----
def get_alerts(db: Session, resolved: Optional[bool] = None, skip: int = 0, limit: int = 100) -> List[Alert]:
    q = db.query(Alert).order_by(Alert.created_at.desc())
    if resolved is not None:
        q = q.filter(Alert.resolved == resolved)
    return q.offset(skip).limit(limit).all()


def get_alert_by_id(db: Session, id: int) -> Optional[Alert]:
    return db.query(Alert).filter(Alert.id == id).first()


def get_unresolved_alert_by_uniqueness_key(db: Session, uniqueness_key: str) -> Optional[Alert]:
    """Return an unresolved alert with this key if any (for deduplication)."""
    return (
        db.query(Alert)
        .filter(Alert.uniqueness_key == uniqueness_key, Alert.resolved == False)
        .first()
    )


def get_unresolved_alert_by_entity(
    db: Session,
    alert_type: str,
    related_entity_type: Optional[str],
    related_entity_id: Optional[str],
) -> Optional[Alert]:
    """Fallback: return an unresolved alert matching type + entity (for legacy rows with null uniqueness_key)."""
    q = db.query(Alert).filter(
        Alert.alert_type == alert_type,
        Alert.resolved == False,
    )
    if related_entity_type is not None:
        q = q.filter(Alert.related_entity_type == related_entity_type)
    else:
        q = q.filter(Alert.related_entity_type.is_(None))
    rid = str(related_entity_id) if related_entity_id is not None else None
    if rid is not None:
        q = q.filter(Alert.related_entity_id == rid)
    else:
        q = q.filter(Alert.related_entity_id.is_(None))
    return q.first()


def update_alert_resolve(db: Session, id: int, payload: AlertResolveUpdate) -> Optional[Alert]:
    alert = get_alert_by_id(db, id)
    if not alert:
        return None
    alert.resolved = payload.resolved
    db.commit()
    db.refresh(alert)
    return alert


def create_alert(
    db: Session,
    alert_type: str,
    message: str,
    severity: str = "warning",
    source_module: str = "data_hub",
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    uniqueness_key: Optional[str] = None,
) -> Optional[Alert]:
    """
    Create an alert only if no logical duplicate exists. Check (1) unresolved with same
    uniqueness_key, then (2) unresolved with same alert_type + related_entity_type + related_entity_id
    (fallback for legacy rows with null uniqueness_key). Return None when duplicate.
    """
    if uniqueness_key:
        existing = get_unresolved_alert_by_uniqueness_key(db, uniqueness_key)
        if existing:
            return None
    existing = get_unresolved_alert_by_entity(
        db, alert_type, related_entity_type, str(related_entity_id) if related_entity_id is not None else None
    )
    if existing:
        return None
    a = Alert(
        alert_type=alert_type,
        severity=severity,
        source_module=source_module,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=str(related_entity_id) if related_entity_id is not None else None,
        uniqueness_key=uniqueness_key,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ----- Infrastructure -----
def get_infrastructure_assets(db: Session) -> List[InfrastructureAsset]:
    return db.query(InfrastructureAsset).all()


def get_infrastructure_asset_by_id(db: Session, id: int) -> Optional[InfrastructureAsset]:
    return db.query(InfrastructureAsset).filter(InfrastructureAsset.id == id).first()


def update_infrastructure_status(db: Session, id: int, payload: InfrastructureStatusUpdate) -> Optional[InfrastructureAsset]:
    asset = get_infrastructure_asset_by_id(db, id)
    if not asset:
        return None
    asset.status = payload.status
    if payload.tamper_detected is not None:
        asset.tamper_detected = payload.tamper_detected
    if payload.network_health is not None:
        asset.network_health = payload.network_health
    asset.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return asset


# ----- PassengerServices -----
def get_passenger_services(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[PassengerService]:
    q = db.query(PassengerService).order_by(PassengerService.request_time.desc())
    if status:
        q = q.filter(PassengerService.status == status)
    return q.offset(skip).limit(limit).all()


# ----- DigitalIdentityStatus -----
def get_digital_identity_statuses(db: Session, skip: int = 0, limit: int = 100) -> List[DigitalIdentityStatus]:
    return db.query(DigitalIdentityStatus).offset(skip).limit(limit).all()


# ----- RetailEvents -----
def get_retail_events(db: Session, skip: int = 0, limit: int = 100) -> List[RetailEvent]:
    return db.query(RetailEvent).order_by(RetailEvent.created_at.desc()).offset(skip).limit(limit).all()


# ----- Gate conflict check (for intelligence) -----
def get_flights_by_gate(db: Session, gate: str) -> List[Flight]:
    """All flights assigned to this gate (for overlap check in service layer)."""
    return db.query(Flight).filter(Flight.gate == gate).order_by(Flight.scheduled_time).all()
