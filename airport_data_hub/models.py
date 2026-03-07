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
    asset_type = Column(String(50), nullable=False)  # security_scanner, belt, kiosk, pos, display, sensor
    asset_name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)  # terminal, gate, security_point, baggage_claim
    terminal = Column(String(10), nullable=True)  # T1, T2, T3, T4, T5
    gate = Column(String(10), nullable=True)
    
    # Status and health
    status = Column(String(20), nullable=False, default="operational")  # operational, degraded, offline, maintenance, failed
    health_score = Column(Float, nullable=True)  # 0-1, higher = healthier
    network_health = Column(Float, nullable=True)  # 0-1
    last_heartbeat = Column(DateTime, nullable=True)
    uptime_percentage = Column(Float, nullable=True)  # Last 24 hours
    
    # Operational metrics
    total_uptime_hours = Column(Float, nullable=True)
    error_count_24h = Column(Integer, default=0)
    last_error_time = Column(DateTime, nullable=True)
    last_maintenance = Column(DateTime, nullable=True)
    next_maintenance = Column(DateTime, nullable=True)
    
    # Usage tracking
    usage_cycles = Column(Integer, default=0)  # Number of usage cycles
    total_usage_time = Column(Float, default=0)  # Total operating hours
    peak_usage_time = Column(DateTime, nullable=True)
    
    # Network and connectivity
    ip_address = Column(String(45), nullable=True)
    mac_address = Column(String(17), nullable=True)
    network_latency_ms = Column(Float, nullable=True)
    packet_loss_percentage = Column(Float, nullable=True)
    
    # Security and tamper detection
    tamper_detected = Column(Boolean, default=False)
    tamper_alert_count = Column(Integer, default=0)
    last_tamper_time = Column(DateTime, nullable=True)
    
    # Predictive maintenance
    failure_probability_24h = Column(Float, nullable=True)  # 0-1
    failure_probability_7d = Column(Float, nullable=True)  # 0-1
    predicted_failure_time = Column(DateTime, nullable=True)
    maintenance_priority = Column(String(20), default="normal")  # critical, high, normal, low
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    last_updated_by = Column(String(50), nullable=True)  # system, operator, auto_healing


class AssetStatusEvent(Base):
    """Track status changes and events per asset"""
    __tablename__ = "asset_status_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.id"), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # status_change, error, maintenance, heartbeat, tamper
    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    event_severity = Column(String(20), default="info")  # critical, warning, info
    
    # Event data
    event_message = Column(Text, nullable=True)
    event_data = Column(Text, nullable=True)  # JSON: error codes, metrics, etc.
    error_code = Column(String(20), nullable=True)
    
    # Network metrics for this event
    network_latency_ms = Column(Float, nullable=True)
    packet_loss_percentage = Column(Float, nullable=True)
    
    # Context
    operator_id = Column(String(50), nullable=True)
    automatic_detection = Column(Boolean, default=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AssetMaintenanceRecord(Base):
    """Maintenance history for predictive analysis"""
    __tablename__ = "asset_maintenance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.id"), nullable=False)
    
    # Maintenance details
    maintenance_type = Column(String(50), nullable=False)  # preventive, corrective, emergency, upgrade
    maintenance_reason = Column(String(200), nullable=True)
    maintenance_description = Column(Text, nullable=True)
    
    # Timing
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    downtime_minutes = Column(Integer, nullable=True)
    
    # Impact
    affected_operations = Column(Text, nullable=True)  # JSON: list of affected services
    passenger_impact = Column(String(20), default="none")  # none, low, medium, high
    
    # Resolution
    parts_replaced = Column(Text, nullable=True)  # JSON: list of parts
    technician_id = Column(String(50), nullable=True)
    maintenance_cost = Column(Float, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class NetworkMonitoringSession(Base):
    """Network heartbeat and connectivity monitoring"""
    __tablename__ = "network_monitoring_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.id"), nullable=False)
    
    # Session details
    session_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    session_end = Column(DateTime, nullable=True)
    session_duration_minutes = Column(Integer, nullable=True)
    
    # Network metrics
    avg_latency_ms = Column(Float, nullable=True)
    max_latency_ms = Column(Float, nullable=True)
    min_latency_ms = Column(Float, nullable=True)
    packet_loss_percentage = Column(Float, nullable=True)
    jitter_ms = Column(Float, nullable=True)
    
    # Connectivity status
    connection_stable = Column(Boolean, default=True)
    disconnect_count = Column(Integer, default=0)
    reconnect_count = Column(Integer, default=0)
    
    # Service availability
    services_monitored = Column(Text, nullable=True)  # JSON: list of services
    services_available = Column(Text, nullable=True)  # JSON: list of available services
    services_degraded = Column(Text, nullable=True)  # JSON: list of degraded services
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class InfrastructureIncident(Base):
    """Infrastructure incidents and anomalies"""
    __tablename__ = "infrastructure_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(50), nullable=False, unique=True)  # Unique incident identifier
    
    # Incident details
    incident_type = Column(String(50), nullable=False)  # asset_offline, repeated_errors, network_degradation, anomaly
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Affected assets
    primary_asset_id = Column(Integer, ForeignKey("infrastructure_assets.id"), nullable=False)
    affected_assets = Column(Text, nullable=True)  # JSON: list of affected asset IDs
    affected_services = Column(Text, nullable=True)  # JSON: list of affected services
    
    # Detection
    detection_method = Column(String(50), nullable=False)  # automated, manual, network_monitoring, pattern_analysis
    detection_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    detection_confidence = Column(Float, nullable=True)  # 0-1
    
    # Impact assessment
    operational_impact = Column(String(20), nullable=True)  # critical, high, medium, low, minimal
    passenger_impact = Column(String(20), nullable=True)  # high, medium, low, none
    flight_impact = Column(Text, nullable=True)  # JSON: list of affected flight IDs
    
    # Resolution
    status = Column(String(20), default="open")  # open, investigating, resolved, closed
    resolution_time = Column(DateTime, nullable=True)
    resolution_description = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    preventive_actions = Column(Text, nullable=True)
    
    # Auto-healing
    auto_healing_attempted = Column(Boolean, default=False)
    auto_healing_successful = Column(Boolean, nullable=True)
    auto_healing_actions = Column(Text, nullable=True)  # JSON: list of actions taken
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class SelfHealingAction(Base):
    """Self-healing actions and recommendations"""
    __tablename__ = "self_healing_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("infrastructure_incidents.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.id"), nullable=False)
    
    # Action details
    action_type = Column(String(50), nullable=False)  # restart, reroute, maintenance_window, notification, config_change
    action_name = Column(String(100), nullable=False)
    action_description = Column(Text, nullable=True)
    
    # Execution
    triggered_by = Column(String(50), nullable=False)  # automated_system, predictive_alert, incident_detection
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    execution_status = Column(String(20), default="pending")  # pending, executing, completed, failed
    execution_result = Column(Text, nullable=True)
    
    # Impact
    successful = Column(Boolean, nullable=True)
    impact_assessment = Column(String(20), nullable=True)  # positive, neutral, negative
    passenger_disruption = Column(Boolean, default=False)
    
    # Recommendations
    recommended_maintenance = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)  # JSON: follow-up actions
    priority = Column(String(20), default="normal")  # critical, high, normal, low
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class PassengerService(Base):
    __tablename__ = "passenger_services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    service_type = Column(String(50), nullable=False)  # assistance, lounge, transfer, info
    status = Column(String(50), nullable=False, default="pending")  # pending, in_progress, completed
    request_time = Column(DateTime, nullable=False)
    completion_time = Column(DateTime, nullable=True)
    location = Column(String(100), nullable=True)


class PassengerJourneyState(Base):
    """Passenger journey state engine: arrival → security → gate → boarding"""
    __tablename__ = "passenger_journey_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    
    # Journey state
    current_state = Column(String(50), nullable=False, default="arrival")  # arrival, check_in, security, post_security, gate, boarding, completed
    previous_state = Column(String(50), nullable=True)
    
    # State transitions
    state_entered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_state_change = Column(DateTime, nullable=True)
    
    # Location and timing
    current_location = Column(String(100), nullable=True)  # terminal, zone, gate
    estimated_gate_arrival = Column(DateTime, nullable=True)
    estimated_boarding_time = Column(DateTime, nullable=True)
    
    # Stress and experience metrics
    stress_score = Column(Float, nullable=True)  # 0-1
    dwell_time_minutes = Column(Integer, nullable=True)  # time spent in current state
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class PassengerJourneyEvent(Base):
    """Events that trigger state transitions (scans, interactions)"""
    __tablename__ = "passenger_journey_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # check_in, security_scan, gate_scan, boarding_scan, retail_purchase
    event_location = Column(String(100), nullable=True)  # terminal, security_point, gate
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Scan/token data
    token_reference = Column(String(200), nullable=True)  # temporary digital token
    scan_data = Column(Text, nullable=True)  # JSON: scan details, biometric hash, etc.
    
    # State transition
    previous_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PassengerStressMetric(Base):
    """Passenger stress score calculations and factors"""
    __tablename__ = "passenger_stress_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    
    # Stress score (0-1, higher = more stress)
    stress_score = Column(Float, nullable=False)
    stress_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Contributing factors
    queue_length_factor = Column(Float, nullable=True)  # 0-1
    time_pressure_factor = Column(Float, nullable=True)  # 0-1
    walking_distance_factor = Column(Float, nullable=True)  # 0-1
    flight_delay_factor = Column(Float, nullable=True)  # 0-1
    
    # Context
    current_location = Column(String(100), nullable=True)
    time_to_boarding = Column(Integer, nullable=True)  # minutes
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # Add missing created_at field


class RetailOpportunity(Base):
    """Retail intelligence: passenger free-time windows and opportunities"""
    __tablename__ = "retail_opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    passenger_reference = Column(String(100), nullable=False, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    
    # Opportunity window
    opportunity_start = Column(DateTime, nullable=False)
    opportunity_end = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    # Location and context
    terminal_zone = Column(String(20), nullable=True)
    current_location = Column(String(100), nullable=True)
    nearest_retail_outlets = Column(Text, nullable=True)  # JSON: list of outlet IDs and distances
    
    # Passenger profile
    stress_level = Column(String(20), nullable=True)  # low, medium, high
    time_pressure = Column(String(20), nullable=True)  # low, medium, high
    
    # Opportunity metrics
    retail_readiness_score = Column(Float, nullable=True)  # 0-1, likelihood to purchase
    recommended_categories = Column(Text, nullable=True)  # JSON: food, duty_free, lounge, etc.
    status = Column(String(20), nullable=False, default="active")  # active, expired, completed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class PassengerInsight(Base):
    """Passenger journey insights and analytics"""
    __tablename__ = "passenger_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    
    # Aggregated metrics for flight
    total_passengers = Column(Integer, nullable=False)
    avg_stress_score = Column(Float, nullable=True)
    high_stress_count = Column(Integer, nullable=True)  # passengers with stress > 0.7
    
    # Journey timing analytics
    avg_check_in_to_security = Column(Integer, nullable=True)  # minutes
    avg_security_to_gate = Column(Integer, nullable=True)  # minutes
    avg_dwell_time_post_security = Column(Integer, nullable=True)  # minutes
    
    # Gate arrival predictions
    on_time_gate_arrival_rate = Column(Float, nullable=True)  # percentage
    late_gate_arrival_count = Column(Integer, nullable=True)
    
    # Retail potential
    total_retail_opportunity_minutes = Column(Integer, nullable=True)
    retail_ready_passengers = Column(Integer, nullable=True)
    
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    flight_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # Add missing created_at field


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


# ===== ENHANCED PASSENGER FLOW MODELS =====

class QueueSensorData(Base):
    """Raw sensor data from queue monitoring systems"""
    __tablename__ = "queue_sensor_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Sensor identification
    sensor_id = Column(String(50), nullable=False, index=True)
    sensor_type = Column(String(30), nullable=False)  # camera, manual, infrared, weight_sensor
    checkpoint_type = Column(String(30), nullable=False)  # security, checkin, boarding, immigration
    terminal = Column(String(10), nullable=False)
    gate = Column(String(10), nullable=True)
    
    # Sensor data
    passenger_count = Column(Integer, nullable=False)
    queue_length_meters = Column(Float, nullable=True)
    flow_rate_ppm = Column(Float, nullable=True)  # passengers per minute
    dwell_time_seconds = Column(Float, nullable=True)
    lane_id = Column(String(20), nullable=True)  # for multi-lane checkpoints
    
    # Data quality and source
    confidence_score = Column(Float, nullable=True)  # 0-1
    data_source = Column(String(30), nullable=False)  # automatic, manual, hybrid
    staff_notes = Column(Text, nullable=True)
    
    # Timestamps
    sensor_timestamp = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class QueueEvent(Base):
    """Normalized queue events processed from sensor data"""
    __tablename__ = "queue_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event identification
    event_id = Column(String(50), nullable=False, unique=True, index=True)
    checkpoint_id = Column(String(50), nullable=False, index=True)
    checkpoint_type = Column(String(30), nullable=False)  # security, checkin, boarding, immigration
    terminal = Column(String(10), nullable=False)
    gate = Column(String(10), nullable=True)
    lane_id = Column(String(20), nullable=True)
    
    # Queue metrics
    current_queue_length = Column(Integer, nullable=False)  # number of passengers
    queue_density = Column(Float, nullable=True)  # passengers per square meter
    average_wait_time = Column(Integer, nullable=True)  # minutes
    peak_wait_time = Column(Integer, nullable=True)  # minutes
    service_rate = Column(Float, nullable=True)  # passengers per minute
    capacity_utilization = Column(Float, nullable=True)  # 0-1
    
    # Flow metrics
    arrival_rate = Column(Float, nullable=True)  # passengers per minute
    departure_rate = Column(Float, nullable=True)  # passengers per minute
    flow_efficiency = Column(Float, nullable=True)  # 0-1
    
    # Event classification
    congestion_level = Column(String(20), nullable=False)  # low, medium, high, critical
    trend_direction = Column(String(10), nullable=True)  # increasing, stable, decreasing
    anomaly_detected = Column(Boolean, default=False)
    
    # Context
    contributing_flights = Column(Text, nullable=True)  # JSON: list of flight IDs
    time_window_minutes = Column(Integer, default=5)
    
    # Timestamps
    event_timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class QueueState(Base):
    """Real-time queue state for each checkpoint"""
    __tablename__ = "queue_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Checkpoint identification
    checkpoint_id = Column(String(50), nullable=False, unique=True, index=True)
    checkpoint_type = Column(String(30), nullable=False)
    terminal = Column(String(10), nullable=False)
    gate = Column(String(10), nullable=True)
    
    # Current state
    current_queue_length = Column(Integer, nullable=False)
    current_wait_time = Column(Integer, nullable=False)  # minutes
    current_capacity_utilization = Column(Float, nullable=False)  # 0-1
    
    # Lane management
    total_lanes = Column(Integer, default=1)
    active_lanes = Column(Integer, default=1)
    lane_status = Column(Text, nullable=True)  # JSON: {lane_id: status, queue_length}
    
    # Performance metrics
    average_service_time = Column(Float, nullable=True)  # minutes per passenger
    peak_queue_length = Column(Integer, nullable=True)
    total_processed_today = Column(Integer, default=0)
    
    # Predictions
    predicted_length_10min = Column(Integer, nullable=True)
    predicted_length_20min = Column(Integer, nullable=True)
    predicted_length_30min = Column(Integer, nullable=True)
    prediction_confidence = Column(Float, nullable=True)  # 0-1
    
    # Alerts and thresholds
    alert_threshold_length = Column(Integer, nullable=True)
    alert_threshold_wait = Column(Integer, nullable=True)
    last_alert_time = Column(DateTime, nullable=True)
    
    # Timestamps
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class QueuePrediction(Base):
    """Queue prediction model results"""
    __tablename__ = "queue_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Prediction identification
    checkpoint_id = Column(String(50), nullable=False, index=True)
    prediction_horizon = Column(Integer, nullable=False)  # minutes ahead
    model_version = Column(String(20), nullable=False)
    
    # Input features
    current_queue_length = Column(Integer, nullable=False)
    current_wait_time = Column(Integer, nullable=False)
    flight_schedules = Column(Text, nullable=True)  # JSON: flight departures in next 2 hours
    historical_patterns = Column(Text, nullable=True)  # JSON: historical averages by time
    weather_conditions = Column(String(50), nullable=True)
    special_events = Column(Text, nullable=True)  # JSON: events affecting flow
    
    # Predictions
    predicted_queue_length = Column(Integer, nullable=False)
    predicted_wait_time = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0-1
    prediction_range = Column(Text, nullable=True)  # JSON: min, max, std
    
    # Accuracy tracking
    actual_queue_length = Column(Integer, nullable=True)
    actual_wait_time = Column(Integer, nullable=True)
    prediction_error = Column(Float, nullable=True)
    
    # Timestamps
    prediction_timestamp = Column(DateTime, nullable=False)
    target_timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    evaluated_at = Column(DateTime, nullable=True)


class LaneRecommendation(Base):
    """Smart lane management recommendations"""
    __tablename__ = "lane_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Recommendation identification
    recommendation_id = Column(String(50), nullable=False, unique=True, index=True)
    checkpoint_id = Column(String(50), nullable=False, index=True)
    recommendation_type = Column(String(30), nullable=False)  # open_lane, close_lane, reconfigure
    
    # Current state
    current_lanes = Column(Integer, nullable=False)
    active_lanes = Column(Integer, nullable=False)
    current_queue_length = Column(Integer, nullable=False)
    current_wait_time = Column(Integer, nullable=False)
    
    # Recommendation details
    recommended_lanes = Column(Integer, nullable=False)
    recommended_action = Column(Text, nullable=False)
    priority_level = Column(String(20), nullable=False)  # low, medium, high, critical
    impact_assessment = Column(Text, nullable=True)  # expected improvement
    
    # Trigger conditions
    trigger_metric = Column(String(30), nullable=False)  # queue_length, wait_time, utilization
    trigger_value = Column(Float, nullable=False)
    threshold_exceeded = Column(Boolean, nullable=False)
    
    # Implementation
    recommended_by = Column(String(50), nullable=False)  # automated_system, staff_name
    implementation_time = Column(DateTime, nullable=True)
    implemented = Column(Boolean, default=False)
    implementation_result = Column(Text, nullable=True)
    
    # Effectiveness tracking
    before_queue_length = Column(Integer, nullable=True)
    after_queue_length = Column(Integer, nullable=True)
    improvement_percentage = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    implemented_at = Column(DateTime, nullable=True)


class PassengerWave(Base):
    """Detected passenger arrival waves and patterns"""
    __tablename__ = "passenger_waves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Wave identification
    wave_id = Column(String(50), nullable=False, unique=True, index=True)
    wave_type = Column(String(30), nullable=False)  # departure_wave, arrival_wave, transfer_wave
    terminal = Column(String(10), nullable=False)
    
    # Wave characteristics
    start_time = Column(DateTime, nullable=False)
    peak_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    # Flight clustering
    clustered_flights = Column(Text, nullable=False)  # JSON: list of flight IDs
    total_passengers = Column(Integer, nullable=False)
    peak_flow_rate = Column(Float, nullable=False)  # passengers per minute
    average_flow_rate = Column(Float, nullable=False)  # passengers per minute
    
    # Impact analysis
    affected_checkpoints = Column(Text, nullable=True)  # JSON: list of checkpoint IDs
    peak_queue_lengths = Column(Text, nullable=True)  # JSON: {checkpoint: max_length}
    congestion_duration = Column(Integer, nullable=True)  # minutes above threshold
    
    # Prediction
    predicted_start_time = Column(DateTime, nullable=True)
    predicted_peak_flow = Column(Float, nullable=True)
    prediction_confidence = Column(Float, nullable=True)  # 0-1
    
    # Timestamps
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class TerminalHeatmap(Base):
    """Terminal congestion heatmap data"""
    __tablename__ = "terminal_heatmaps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Heatmap identification
    heatmap_id = Column(String(50), nullable=False, index=True)
    terminal = Column(String(10), nullable=False, index=True)
    floor_level = Column(String(20), nullable=True)  # ground, departure, arrival
    
    # Grid data
    grid_resolution = Column(Integer, nullable=False)  # meters per cell
    grid_width = Column(Integer, nullable=False)  # number of cells
    grid_height = Column(Integer, nullable=False)  # number of cells
    
    # Heatmap data
    density_data = Column(Text, nullable=False)  # JSON: 2D array of passenger densities
    congestion_zones = Column(Text, nullable=True)  # JSON: list of congested areas
    flow_directions = Column(Text, nullable=True)  # JSON: flow vectors
    
    # Color coding
    congestion_levels = Column(Text, nullable=True)  # JSON: {level: color, threshold}
    peak_density = Column(Float, nullable=False)
    average_density = Column(Float, nullable=False)
    
    # Context
    total_passengers = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    contributing_flights = Column(Text, nullable=True)  # JSON: flight IDs
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    stale_data_warnings = Column(Text, nullable=True)  # JSON array
    operational_reason_codes = Column(Text, nullable=True)  # JSON: [{"factor", "contribution", "operational_code", "operational_phrase"}]
