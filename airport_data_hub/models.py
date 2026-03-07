"""
Airport Data Hub - SQLAlchemy ORM models.
Single source of truth for all operational domains; schema anticipates
hazard detection, runway grip, machinery security, disruption copilot,
resource planning, passenger flow, AODB, satisfaction, navigation, retail, identity.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_code = Column(String(20), unique=True, nullable=False, index=True)
    airline = Column(String(100), nullable=False)
    origin = Column(String(10), nullable=False)
    destination = Column(String(10), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    estimated_time = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="scheduled")  # scheduled, boarding, departed, delayed, cancelled
    gate = Column(String(20), nullable=True)
    stand = Column(String(20), nullable=True)
    runway_id = Column(Integer, ForeignKey("runways.id"), nullable=True)
    # AI-Native AODB: reconciliation (raw source data separate; reconciled values + reason/confidence/timestamp)
    predicted_eta = Column(DateTime, nullable=True)  # from prediction module
    reconciled_eta = Column(DateTime, nullable=True)  # reconciled from reported_eta / predicted_eta / schedule
    reconciled_status = Column(String(50), nullable=True)
    reconciled_gate = Column(String(20), nullable=True)
    reconciliation_reason = Column(String(200), nullable=True)
    reconciliation_confidence = Column(Float, nullable=True)
    last_reconciled_at = Column(DateTime, nullable=True)
    # AODB: arrival delay prediction (pushed by prediction service)
    predicted_arrival_delay_min = Column(Float, nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    prediction_model_version = Column(String(50), nullable=True)
    last_prediction_at = Column(DateTime, nullable=True)


class FlightUpdate(Base):
    """Raw flight data from a single source (airline, radar, airport_ops, manual). For AODB reconciliation."""
    __tablename__ = "flight_updates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False, index=True)
    source_name = Column(String(50), nullable=False)  # airline, radar, airport_ops, manual
    reported_eta = Column(DateTime, nullable=True)
    reported_status = Column(String(50), nullable=True)
    reported_gate = Column(String(20), nullable=True)
    reported_at = Column(DateTime, nullable=False)
    confidence_score = Column(Float, nullable=True)


class PassengerFlow(Base):
    __tablename__ = "passenger_flow"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False, index=True)
    check_in_count = Column(Integer, default=0)
    security_queue_count = Column(Integer, default=0)
    boarding_count = Column(Integer, default=0)
    predicted_queue_time = Column(Float, nullable=True)  # minutes
    terminal_zone = Column(String(50), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)


class Runway(Base):
    __tablename__ = "runways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    runway_code = Column(String(20), unique=True, nullable=False)
    status = Column(String(50), nullable=False, default="active")  # active, closed, maintenance
    surface_condition = Column(String(50), nullable=True)  # dry, wet, slush, ice
    contamination_level = Column(Float, nullable=True)  # 0-1
    grip_score = Column(Float, nullable=True)  # 0-1, 1 = best
    hazard_detected = Column(Boolean, default=False)
    hazard_type = Column(String(100), nullable=True)
    last_inspection_time = Column(DateTime, nullable=True)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_name = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)  # gate, stand, desk, vehicle, staff_slot
    status = Column(String(50), nullable=False, default="available")  # available, assigned, maintenance
    assigned_to = Column(String(200), nullable=True)  # flight_code or entity id
    location = Column(String(100), nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False)  # queue, runway_hazard, grip, gate_conflict, machinery, security
    severity = Column(String(20), nullable=False, default="info")  # info, warning, critical
    source_module = Column(String(50), nullable=True)  # data_hub, passenger_flow, runway_grip, etc.
    message = Column(Text, nullable=False)
    related_entity_type = Column(String(50), nullable=True)  # flight, runway, resource, infrastructure
    related_entity_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    uniqueness_key = Column(String(128), nullable=True, index=True)  # stable key for dedup: type:entity_type:id


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_name = Column(String(100), nullable=False)
    asset_type = Column(String(50), nullable=False)  # jet_bridge, baggage_belt, camera, sensor
    status = Column(String(50), nullable=False, default="operational")
    network_health = Column(Float, nullable=True)  # 0-1
    tamper_detected = Column(Boolean, default=False)
    location = Column(String(100), nullable=True)
    last_updated = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class PassengerService(Base):
    __tablename__ = "passenger_services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    service_type = Column(String(50), nullable=False)  # assistance, lounge, transfer, info
    status = Column(String(50), nullable=False, default="pending")  # pending, in_progress, completed
    request_time = Column(DateTime, nullable=False)
    completion_time = Column(DateTime, nullable=True)
    location = Column(String(100), nullable=True)


class DigitalIdentityStatus(Base):
    __tablename__ = "digital_identity_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    verification_status = Column(String(50), nullable=False)  # verified, pending, failed
    verification_method = Column(String(50), nullable=True)  # biometric, document, token
    last_verified_at = Column(DateTime, nullable=True)
    token_reference = Column(String(200), nullable=True)


class RetailEvent(Base):
    __tablename__ = "retail_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    offer_type = Column(String(50), nullable=True)  # food, duty_free, lounge
    order_status = Column(String(50), nullable=False, default="placed")  # placed, prepared, picked_up
    pickup_gate = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PredictionAudit(Base):
    """
    Arrival delay prediction audit: every prediction stored (same DB as hub).
    Traceable: outcome, input quality, missing features, staleness, operational reason codes.
    """
    __tablename__ = "prediction_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, nullable=False, index=True)
    prediction_timestamp = Column(DateTime, nullable=False)
    model_version = Column(String(50), nullable=False)
    predicted_arrival_delay_min = Column(Float, nullable=False)
    predicted_arrival_time = Column(DateTime, nullable=True)
    confidence_score = Column(Float, nullable=True)
    reason_codes = Column(Text, nullable=True)  # JSON: [{"factor", "contribution"}]
    features_snapshot = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Hardening: outcome type, quality, explainability
    prediction_outcome = Column(String(32), nullable=True)  # ml_model | rules_fallback | insufficient_data
    input_quality_score = Column(Float, nullable=True)  # 0-1
    missing_features = Column(Text, nullable=True)  # JSON array
    stale_data_warnings = Column(Text, nullable=True)  # JSON array
    operational_reason_codes = Column(Text, nullable=True)  # JSON: [{"factor", "contribution", "operational_code", "operational_phrase"}]
