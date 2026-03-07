"""
Synthetic data generator for the Airport Data Hub.

Continuously mutates the SQLite hub database so that:
- passenger flow counts move in real time
- runway conditions and hazards fluctuate
- infrastructure health / tamper flags change over time
- passenger journey states transition realistically
- passenger stress scores vary dynamically
- retail opportunities are generated

Designed for hackathon demos: runs in a lightweight background thread that
uses the same SQLAlchemy SessionLocal as the FastAPI app.
"""

from __future__ import annotations

import json
import random
import threading
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import (
    Flight, PassengerFlow, Runway, InfrastructureAsset, 
    PassengerJourneyState, PassengerJourneyEvent, PassengerStressMetric,
    RetailOpportunity, DigitalIdentityStatus, AssetStatusEvent,
    AssetMaintenanceRecord, NetworkMonitoringSession, InfrastructureIncident,
    SelfHealingAction
)
from ..services.passenger_journey import journey_engine
from ..services.passenger_intelligence import intelligence_engine
from ..services.retail_intelligence import retail_intelligence
from ..services.asset_monitoring import asset_monitoring
from ..services.asset_health_prediction import asset_health_prediction
from ..services.network_monitoring import network_monitoring
from ..services.incident_detection import incident_detection
from ..services.self_healing import self_healing
from ..services.queue_data_ingestion import queue_data_ingestion
from ..services.queue_state_engine import queue_state_engine
from ..services.queue_prediction import queue_prediction
from ..services.smart_lane_management import smart_lane_management
from ..services.passenger_wave_detection import passenger_wave_detection
from ..services.flow_visualization import flow_visualization

_generator_thread: Optional[threading.Thread] = None
_stop_event: Optional[threading.Event] = None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _select_active_flights(db: Session) -> list[Flight]:
    """Pick flights that are close to 'now' so changes are visible."""
    now = datetime.utcnow()
    window_start = now - timedelta(hours=2)
    window_end = now + timedelta(hours=4)
    return (
        db.query(Flight)
        .filter(Flight.scheduled_time >= window_start, Flight.scheduled_time <= window_end)
        .order_by(Flight.scheduled_time)
        .all()
    )


def _tick_once(db: Session) -> None:
    """Single synthetic update tick."""
    now = datetime.utcnow()

    # 1) Move passenger flows in real time for more flights with dramatic changes
    flights = _select_active_flights(db)
    if flights:
        sample_size = min(len(flights), 8)  # Increased from 5 to 8
        for flight in random.sample(flights, sample_size):
            # More dramatic passenger count variations
            base_security = random.randint(10, 250)  # Even wider range for more visibility
            # More frequent spikes to trigger alerts (50% chance vs 25%)
            if random.random() < 0.5:
                base_security = random.randint(200, 350)  # Much higher spikes

            pf = PassengerFlow(
                flight_id=flight.id,
                check_in_count=random.randint(10, 400),  # Much wider range
                security_queue_count=base_security,
                boarding_count=random.randint(0, 300),  # Higher max
                predicted_queue_time=random.uniform(1.0, 45.0),  # Wider time range
                terminal_zone=random.choice(["T1", "T2", "T3", "T4", "T5"]),  # More variety
                timestamp=now,
            )
            db.add(pf)

    # 1.5) Also update some existing passenger flows to make immediate changes visible
    existing_flows = db.query(PassengerFlow).order_by(PassengerFlow.timestamp.desc()).limit(20).all()
    if existing_flows:
        flows_to_update = random.sample(existing_flows, min(5, len(existing_flows)))
        for flow in flows_to_update:
            # Dramatically change existing values for immediate visibility
            flow.security_queue_count = random.randint(50, 300)
            flow.check_in_count = random.randint(100, 500)
            flow.boarding_count = random.randint(50, 250)
            flow.predicted_queue_time = random.uniform(5.0, 40.0)
            flow.timestamp = now  # Update timestamp to bring to top

    # 2) More dramatic runway changes
    runways = db.query(Runway).all()
    for r in runways:
        if r.grip_score is None:
            r.grip_score = random.uniform(0.4, 0.95)
        # Larger random walk changes
        if random.random() < 0.8:  # Increased from 0.6
            r.grip_score = _clamp(r.grip_score + random.uniform(-0.12, 0.12), 0.1, 1.0)

        # More frequent hazard changes (20% chance vs 10%)
        if random.random() < 0.2:
            r.hazard_detected = not r.hazard_detected
            if r.hazard_detected:
                r.hazard_type = random.choice([
                    "standing water", "rubber build-up", "FOD", "ice patches", 
                    "debris", "wildlife", "maintenance vehicle"
                ])
            else:
                r.hazard_type = None
        r.last_inspection_time = now

    # 3) More dynamic infrastructure changes
    assets = db.query(InfrastructureAsset).all()
    for asset in assets:
        # More dramatic network health changes
        if asset.network_health is None:
            asset.network_health = random.uniform(0.5, 1.0)
        if random.random() < 0.85:  # Increased from 0.7
            asset.network_health = _clamp(
                asset.network_health + random.uniform(-0.15, 0.15),
                0.1,
                1.0,
            )

        # More frequent status changes (20% chance vs 10%)
        if random.random() < 0.2:
            tamper = random.random() < 0.4  # Slightly higher tamper chance
            asset.tamper_detected = tamper
            if tamper:
                asset.status = random.choice(["degraded", "offline", "maintenance"])
            else:
                # More dynamic status recovery
                if asset.status in ("degraded", "offline", "maintenance") and random.random() < 0.7:
                    asset.status = "operational"

        asset.last_updated = now

    # 4) NEW: Add flight status changes for more visibility
    if flights and random.random() < 0.3:  # 30% chance to update flight statuses
        sample_flights = random.sample(flights, min(3, len(flights)))
        for flight in sample_flights:
            # Randomly update flight status
            if random.random() < 0.5:
                old_status = flight.status
                flight.status = random.choice([
                    "scheduled", "boarding", "departed", "in_air", 
                    "landed", "taxiing", "at_gate", "delayed"
                ])
                # Create a flight update for status change
                from ..models import FlightUpdate
                update = FlightUpdate(
                    flight_id=flight.id,
                    reported_status=flight.status,
                    reported_at=now,
                    source="synthetic_generator",
                )
                db.add(update)

    # 5) NEW: Add gate changes for more dynamic feel
    if flights and random.random() < 0.2:  # 20% chance for gate changes
        sample_flights = random.sample(flights, min(2, len(flights)))
        for flight in sample_flights:
            if random.random() < 0.6:
                old_gate = flight.gate
                flight.gate = random.choice(["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "D1"])
                # Create flight update for gate change
                from ..models import FlightUpdate
                update = FlightUpdate(
                    flight_id=flight.id,
                    reported_gate=flight.gate,
                    reported_at=now,
                    source="synthetic_generator",
                )
                db.add(update)

    # 6) NEW: Generate passenger journey states and events
    _generate_passenger_journey_data(db, flights, now)

    # 7) NEW: Generate passenger stress metrics
    _generate_passenger_stress_data(db, now)

    # 8) NEW: Generate retail opportunities
    _generate_retail_opportunities(db, now)

    # 9) NEW: Generate infrastructure monitoring data
    _generate_infrastructure_monitoring_data(db, now)

    # 10) NEW: Generate asset health prediction data
    _generate_asset_health_data(db, now)

    # 11) NEW: Generate network monitoring data
    _generate_network_monitoring_data(db, now)

    # 12) NEW: Generate incident detection data
    _generate_incident_data(db, now)

    # 13) NEW: Generate self-healing action data
    _generate_self_healing_data(db, now)

    # 14) NEW: Generate queue sensor data
    _generate_queue_sensor_data(db, now)

    # 15) NEW: Generate queue events
    _generate_queue_events(db, now)

    # 16) NEW: Update queue states
    _update_queue_states(db, now)

    # 17) NEW: Generate queue predictions
    _generate_queue_predictions(db, now)

    # 18) NEW: Generate lane recommendations
    _generate_lane_recommendations(db, now)

    # 19) NEW: Detect passenger waves
    _detect_passenger_waves(db, now)

    # 20) NEW: Generate flow visualization data
    _generate_flow_visualization_data(db, now)


def _generate_passenger_journey_data(db: Session, flights: list[Flight], now: datetime):
    """Generate synthetic passenger journey states and events."""
    
    if not flights:
        return
    
    # Select a few flights for journey generation
    sample_flights = random.sample(flights, min(3, len(flights)))
    
    for flight in sample_flights:
        # Generate or update passenger journey states
        existing_states = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.flight_id == flight.id
        ).all()
        
        # Create new passengers if needed
        if len(existing_states) < 5:
            for i in range(5 - len(existing_states)):
                passenger_ref = f"P{flight.id}_{random.randint(1000, 9999)}"
                
                # Create initial journey state
                state = PassengerJourneyState(
                    passenger_reference=passenger_ref,
                    flight_id=flight.id,
                    current_state=random.choice(["arrival", "check_in", "security", "post_security"]),
                    state_entered_at=now - timedelta(minutes=random.randint(5, 60)),
                    current_location=random.choice(["T1_check_in", "T1_security", "T2_gate_area", "T3_post_security"]),
                    stress_score=random.uniform(0.1, 0.8),
                    dwell_time_minutes=random.randint(5, 45)
                )
                db.add(state)
        else:
            # Update existing states occasionally
            if random.random() < 0.3:  # 30% chance to update states
                state_to_update = random.choice(existing_states)
                
                # Generate state transition event
                old_state = state_to_update.current_state
                new_state = random.choice(journey_engine.STATE_TRANSITIONS.get(old_state, [old_state]))
                
                if new_state != old_state:
                    event = PassengerJourneyEvent(
                        passenger_reference=state_to_update.passenger_reference,
                        flight_id=flight.id,
                        event_type=random.choice(["check_in", "security_scan", "gate_scan", "boarding_scan"]),
                        event_location=state_to_update.current_location,
                        previous_state=old_state,
                        new_state=new_state,
                        event_timestamp=now
                    )
                    db.add(event)
                    
                    # Update state
                    state_to_update.previous_state = old_state
                    state_to_update.current_state = new_state
                    state_to_update.last_state_change = now
                    state_to_update.dwell_time_minutes = random.randint(2, 30)


def _generate_passenger_stress_data(db: Session, now: datetime):
    """Generate synthetic passenger stress metrics."""
    
    # Get recent journey states
    recent_states = db.query(PassengerJourneyState).filter(
        PassengerJourneyState.current_state.in_(["security", "post_security", "gate"])
    ).limit(20).all()
    
    for state in recent_states:
        # Check if stress metric already exists recently
        existing_metric = db.query(PassengerStressMetric).filter(
            PassengerStressMetric.passenger_reference == state.passenger_reference,
            PassengerStressMetric.flight_id == state.flight_id,
            PassengerStressMetric.calculated_at >= now - timedelta(minutes=10)
        ).first()
        
        if not existing_metric:
            # Generate stress metric
            stress_score = random.uniform(0.1, 0.9)
            stress_level = intelligence_engine._get_stress_level(stress_score)
            
            metric = PassengerStressMetric(
                passenger_reference=state.passenger_reference,
                flight_id=state.flight_id,
                stress_score=stress_score,
                stress_level=stress_level,
                queue_length_factor=random.uniform(0.0, 0.8),
                time_pressure_factor=random.uniform(0.0, 0.9),
                walking_distance_factor=random.uniform(0.0, 0.5),
                flight_delay_factor=random.uniform(0.0, 0.7),
                current_location=state.current_location,
                time_to_boarding=random.randint(10, 90),
                calculated_at=now
            )
            db.add(metric)


def _generate_retail_opportunities(db: Session, now: datetime):
    """Generate synthetic retail opportunities."""
    
    # Get passengers in relevant states
    passengers = db.query(PassengerJourneyState).filter(
        PassengerJourneyState.current_state.in_(["post_security", "gate", "retail"])
    ).limit(15).all()
    
    for passenger in passengers:
        # Check if opportunity already exists
        existing_opp = db.query(RetailOpportunity).filter(
            RetailOpportunity.passenger_reference == passenger.passenger_reference,
            RetailOpportunity.flight_id == passenger.flight_id,
            RetailOpportunity.expires_at > now
        ).first()
        
        if not existing_opp and random.random() < 0.4:  # 40% chance to create opportunity
            # Generate opportunity
            duration = random.randint(10, 60)
            opportunity_start = now
            opportunity_end = now + timedelta(minutes=duration)
            
            opportunity = RetailOpportunity(
                passenger_reference=passenger.passenger_reference,
                flight_id=passenger.flight_id,
                opportunity_start=opportunity_start,
                opportunity_end=opportunity_end,
                duration_minutes=duration,
                terminal_zone=random.choice(["T1", "T2", "T3", "T4", "T5"]),
                current_location=passenger.current_location,
                nearest_retail_outlets='[{"id": "store1", "name": "Test Store", "distance": 5}]',
                stress_level=random.choice(["low", "medium", "high"]),
                time_pressure=random.choice(["low", "medium", "high"]),
                retail_readiness_score=random.uniform(0.3, 0.9),
                recommended_categories=json.dumps(random.sample(["food", "duty_free", "retail", "lounge"], 2)),
                created_at=now,
                expires_at=opportunity_end
            )
            db.add(opportunity)


def _generate_infrastructure_monitoring_data(db: Session, now: datetime):
    """Generate synthetic infrastructure monitoring data."""
    
    # Get existing assets
    assets = db.query(InfrastructureAsset).all()
    
    if not assets:
        # Create some initial assets if none exist
        _create_initial_assets(db)
        assets = db.query(InfrastructureAsset).all()
    
    # Update asset statuses and create events
    for asset in random.sample(assets, min(5, len(assets))):
        if random.random() < 0.3:  # 30% chance to update status
            # Generate status change
            new_status = random.choice(["operational", "degraded", "offline", "maintenance"])
            old_health = asset.health_score
            
            # Update asset
            asset.status = new_status
            asset.health_score = max(0.1, min(1.0, old_health + random.uniform(-0.2, 0.1)))
            asset.network_health = max(0.1, min(1.0, asset.network_health + random.uniform(-0.3, 0.1)))
            asset.last_heartbeat = now
            asset.error_count_24h = max(0, asset.error_count_24h + random.randint(-2, 3))
            asset.updated_at = now
            
            # Create status event
            event = AssetStatusEvent(
                asset_id=asset.id,
                event_type="status_change",
                previous_status=asset.status,
                new_status=new_status,
                event_message=f"Status changed to {new_status}",
                event_severity=random.choice(["info", "warning", "critical"]),
                network_latency_ms=random.uniform(10, 500),
                packet_loss_percentage=random.uniform(0, 5),
                automatic_detection=True
            )
            db.add(event)
    
    # Create network monitoring sessions
    for asset in random.sample(assets, min(3, len(assets))):
        if random.random() < 0.4:  # 40% chance to create monitoring session
            # Check if there's an active session
            active_session = db.query(NetworkMonitoringSession).filter(
                NetworkMonitoringSession.asset_id == asset.id,
                NetworkMonitoringSession.session_end.is_(None)
            ).first()
            
            if not active_session:
                session = NetworkMonitoringSession(
                    asset_id=asset.id,
                    session_start=now - timedelta(minutes=random.randint(10, 120)),
                    avg_latency_ms=random.uniform(20, 200),
                    max_latency_ms=random.uniform(100, 500),
                    min_latency_ms=random.uniform(5, 50),
                    packet_loss_percentage=random.uniform(0, 3),
                    jitter_ms=random.uniform(1, 20),
                    connection_stable=random.random() > 0.2,
                    disconnect_count=random.randint(0, 5),
                    reconnect_count=random.randint(0, 3),
                    services_monitored=json.dumps([80, 443, 8080]),
                    services_available=json.dumps([80, 443]),
                    services_degraded=json.dumps([8080] if random.random() < 0.3 else [])
                )
                db.add(session)
    
    # Create maintenance records
    for asset in random.sample(assets, min(2, len(assets))):
        if random.random() < 0.2:  # 20% chance to create maintenance record
            maintenance = AssetMaintenanceRecord(
                asset_id=asset.id,
                maintenance_type=random.choice(["preventive", "corrective", "emergency"]),
                maintenance_reason=random.choice(["Scheduled maintenance", "Error repair", "Performance upgrade"]),
                maintenance_description="Synthetic maintenance for testing",
                scheduled_start=now - timedelta(hours=random.randint(1, 24)),
                scheduled_end=now - timedelta(hours=random.randint(0, 23)),
                actual_start=now - timedelta(hours=random.randint(1, 24)),
                actual_end=now - timedelta(hours=random.randint(0, 23)),
                downtime_minutes=random.randint(15, 120),
                affected_operations=json.dumps(["primary_service", "monitoring"]),
                passenger_impact=random.choice(["none", "low", "medium"]),
                parts_replaced=json.dumps(["sensor_module", "cable", "power_supply"] if random.random() < 0.5 else []),
                technician_id=f"TECH_{random.randint(1000, 9999)}",
                maintenance_cost=random.uniform(100, 2000)
            )
            db.add(maintenance)


def _generate_asset_health_data(db: Session, now: datetime):
    """Generate synthetic asset health prediction data."""
    
    assets = db.query(InfrastructureAsset).limit(10).all()
    
    for asset in assets:
        if random.random() < 0.5:  # 50% chance to update health prediction
            # Calculate health score and predictions
            try:
                health_data = asset_health_prediction.calculate_asset_health_score(db, asset.id)
                
                # Update failure probability
                failure_prob = random.uniform(0.1, 0.8)
                asset.failure_probability_24h = failure_prob
                asset.failure_probability_7d = min(0.95, failure_prob * 1.5)
                
                # Predict failure time for high probability assets
                if failure_prob > 0.6:
                    hours_to_failure = int((1.0 - failure_prob) * 48)
                    asset.predicted_failure_time = now + timedelta(hours=hours_to_failure)
                
                asset.maintenance_priority = asset_health_prediction._calculate_maintenance_priority(failure_prob, asset)
                asset.updated_at = now
                
            except Exception:
                # Fallback to simple random values
                asset.failure_probability_24h = random.uniform(0.1, 0.7)
                asset.failure_probability_7d = random.uniform(0.2, 0.9)
                asset.maintenance_priority = random.choice(["critical", "high", "normal", "low"])


def _generate_network_monitoring_data(db: Session, now: datetime):
    """Generate synthetic network monitoring data."""
    
    # Get active monitoring sessions
    active_sessions = db.query(NetworkMonitoringSession).filter(
        NetworkMonitoringSession.session_end.is_(None)
    ).all()
    
    for session in random.sample(active_sessions, min(3, len(active_sessions))):
        if random.random() < 0.6:  # 60% chance to update session
            # Update session with new metrics
            session.avg_latency_ms = max(10, session.avg_latency_ms + random.uniform(-20, 50))
            session.max_latency_ms = max(session.max_latency_ms or 0, session.avg_latency_ms + random.uniform(50, 200))
            session.packet_loss_percentage = max(0, min(10, session.packet_loss_percentage + random.uniform(-1, 2)))
            
            # Simulate connection issues
            if random.random() < 0.1:  # 10% chance of disconnection
                session.disconnect_count += 1
                session.connection_stable = False
            elif random.random() < 0.2:  # 20% chance of reconnection
                session.reconnect_count += 1
                session.connection_stable = True


def _generate_incident_data(db: Session, now: datetime):
    """Generate synthetic infrastructure incidents."""
    
    assets = db.query(InfrastructureAsset).all()
    
    # Generate incidents for assets with poor health
    poor_health_assets = [asset for asset in assets if asset.health_score and asset.health_score < 0.6]
    
    for asset in random.sample(poor_health_assets, min(2, len(poor_health_assets))):
        if random.random() < 0.4:  # 40% chance to create incident
            incident_types = ["asset_offline", "repeated_errors", "network_degradation", "performance_anomaly"]
            
            incident = InfrastructureIncident(
                incident_id=f"INC-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                incident_type=random.choice(incident_types),
                severity=random.choice(["low", "medium", "high", "critical"]),
                title=f"Synthetic incident on {asset.asset_name}",
                description=f"Generated incident for testing purposes",
                primary_asset_id=asset.id,
                affected_assets=json.dumps([asset.id]),
                affected_services=json.dumps(["primary_service"]),
                detection_method="automated",
                detection_time=now - timedelta(minutes=random.randint(5, 60)),
                detection_confidence=random.uniform(0.6, 0.95),
                operational_impact=random.choice(["minimal", "low", "medium", "high", "critical"]),
                passenger_impact=random.choice(["none", "low", "medium", "high"]),
                status="open"
            )
            db.add(incident)
    
    # Auto-resolve some old incidents
    old_incidents = db.query(InfrastructureIncident).filter(
        InfrastructureIncident.status == "open",
        InfrastructureIncident.detection_time < now - timedelta(hours=2)
    ).limit(2).all()
    
    for incident in old_incidents:
        if random.random() < 0.3:  # 30% chance to resolve
            incident.status = "resolved"
            incident.resolution_time = now
            incident.resolution_description = "Auto-resolved for testing"
            incident.root_cause = "Synthetic root cause"
            incident.preventive_actions = json.dumps(["Enhanced monitoring", "Preventive maintenance"])
            incident.updated_at = now


def _generate_self_healing_data(db: Session, now: datetime):
    """Generate synthetic self-healing action data."""
    
    # Get open incidents
    open_incidents = db.query(InfrastructureIncident).filter(
        InfrastructureIncident.status == "open"
    ).all()
    
    for incident in random.sample(open_incidents, min(2, len(open_incidents))):
        if random.random() < 0.5:  # 50% chance to attempt healing
            action_types = ["restart", "reroute", "config_change", "notification"]
            
            healing_action = SelfHealingAction(
                incident_id=incident.id,
                asset_id=incident.primary_asset_id,
                action_type=random.choice(action_types),
                action_name=f"Auto {random.choice(['restart', 'reroute', 'config'])}",
                action_description="Automated healing action for testing",
                triggered_by="automated_system",
                executed_at=now,
                execution_status=random.choice(["pending", "executing", "completed", "failed"]),
                execution_result=json.dumps({"success": random.random() > 0.3}),
                successful=random.random() > 0.4,
                impact_assessment=random.choice(["positive", "neutral", "negative"]),
                passenger_disruption=random.choice([True, False]),
                priority=random.choice(["critical", "high", "normal", "low"]),
                recommended_maintenance=json.dumps(["Schedule inspection", "Update configuration"]),
                recommended_actions=json.dumps(["Monitor closely", "Prepare backup"])
            )
            db.add(healing_action)


def _create_initial_assets(db: Session):
    """Create initial infrastructure assets for testing."""
    
    initial_assets = [
        {
            "asset_type": "security_scanner",
            "asset_name": "Scanner-01",
            "location": "T1_Security_Point_A",
            "terminal": "T1",
            "ip_address": "192.168.1.101",
            "mac_address": "00:11:22:33:44:55"
        },
        {
            "asset_type": "belt",
            "asset_name": "Baggage-Belt-01",
            "location": "T1_Baggage_Claim_01",
            "terminal": "T1",
            "ip_address": "192.168.1.102",
            "mac_address": "00:11:22:33:44:56"
        },
        {
            "asset_type": "kiosk",
            "asset_name": "Check-in-Kiosk-01",
            "location": "T1_Check-in_A",
            "terminal": "T1",
            "ip_address": "192.168.1.103",
            "mac_address": "00:11:22:33:44:57"
        },
        {
            "asset_type": "pos",
            "asset_name": "POS-Retail-01",
            "location": "T1_Retail_A",
            "terminal": "T1",
            "ip_address": "192.168.1.104",
            "mac_address": "00:11:22:33:44:58"
        },
        {
            "asset_type": "display",
            "asset_name": "Display-Board-01",
            "location": "T1_Gate_A12",
            "terminal": "T1",
            "gate": "A12",
            "ip_address": "192.168.1.105",
            "mac_address": "00:11:22:33:44:59"
        }
    ]
    
    for asset_data in initial_assets:
        asset = InfrastructureAsset(
            asset_type=asset_data["asset_type"],
            asset_name=asset_data["asset_name"],
            location=asset_data["location"],
            terminal=asset_data["terminal"],
            gate=asset_data.get("gate"),
            ip_address=asset_data["ip_address"],
            mac_address=asset_data["mac_address"],
            status="operational",
            health_score=random.uniform(0.7, 1.0),
            network_health=random.uniform(0.8, 1.0),
            last_heartbeat=datetime.utcnow(),
            uptime_percentage=99.5,
            total_uptime_hours=random.uniform(100, 1000),
            error_count_24h=0,
            usage_cycles=random.randint(100, 1000),
            total_usage_time=random.uniform(500, 5000),
            maintenance_priority="normal",
            created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365))
        )
        db.add(asset)
    """Generate synthetic digital identity data."""
    
    # Get passengers without digital identity
    passengers = db.query(PassengerJourneyState).filter(
        ~PassengerJourneyState.passenger_reference.in_(
            db.query(DigitalIdentityStatus.passenger_reference)
        )
    ).limit(10).all()
    
    for passenger in passengers:
        if random.random() < 0.6:  # 60% chance to create identity record
            identity = DigitalIdentityStatus(
                passenger_reference=passenger.passenger_reference,
                verification_status=random.choice(["verified", "pending", "failed"]),
                verification_method=random.choice(["biometric", "document", "token"]),
                token_reference=f"TOKEN_{passenger.passenger_reference}_{random.randint(1000, 9999)}",
                last_verified_at=now - timedelta(minutes=random.randint(5, 60))
            )
            db.add(identity)


def _generator_loop(stop_event: threading.Event, interval_seconds: float = 1.5) -> None:
    """Background loop that periodically mutates the DB."""
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            _tick_once(db)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        # Wait with early-exit if stop requested
        if stop_event.wait(interval_seconds):
            break


def start_synthetic_feeder() -> None:
    """Start the background synthetic data generator thread (idempotent)."""
    global _generator_thread, _stop_event
    if _generator_thread and _generator_thread.is_alive():
        return

    stop_event = threading.Event()
    thread = threading.Thread(
        target=_generator_loop,
        args=(stop_event,),
        name="synthetic-data-feeder",
        daemon=True,
    )
    _stop_event = stop_event
    _generator_thread = thread
    thread.start()


def stop_synthetic_feeder(timeout: float = 2.0) -> None:
    """Signal the background generator to stop and wait briefly."""
    global _generator_thread, _stop_event
    if not _stop_event or not _generator_thread:
        return

    _stop_event.set()
    if _generator_thread.is_alive():
        _generator_thread.join(timeout=timeout)


def _generate_queue_sensor_data(db: Session, now: datetime):
    """Generate synthetic queue sensor data from multiple sources."""
    # Generate camera data
    camera_data = {
        "sensor_id": f"CAM-{random.choice(['SEC1', 'SEC2', 'CHK1', 'CHK2', 'BRD1'])}",
        "checkpoint_type": random.choice(["security", "checkin", "boarding"]),
        "terminal": random.choice(["T1", "T2", "T3"]),
        "gate": random.choice(["A1", "A2", "B1", "B2", "C1"]) if random.random() < 0.5 else None,
        "passenger_count": random.randint(5, 80),
        "queue_length_meters": random.uniform(2.0, 25.0),
        "flow_rate_ppm": random.uniform(1.0, 15.0),
        "dwell_time_seconds": random.uniform(30, 300),
        "lane_id": random.choice(["lane_1", "lane_2", "lane_3"]) if random.random() < 0.6 else None,
        "confidence": random.uniform(0.7, 0.95),
        "lighting_level": random.choice(["excellent", "good", "moderate"]),
        "camera_angle": random.uniform(0, 45),
        "camera_height": random.uniform(2.5, 4.0),
        "sensor_timestamp": now
    }
    
    try:
        queue_data_ingestion.ingest_camera_data(db, camera_data)
    except:
        pass  # Ignore errors in synthetic generation
    
    # Generate manual staff data occasionally
    if random.random() < 0.3:
        manual_data = {
            "sensor_id": f"MAN-{random.choice(['SEC1', 'CHK1', 'BRD1'])}",
            "checkpoint_type": random.choice(["security", "checkin", "boarding"]),
            "terminal": random.choice(["T1", "T2", "T3"]),
            "passenger_count": random.randint(3, 60),
            "queue_length_meters": random.uniform(1.5, 20.0),
            "flow_rate_ppm": random.uniform(0.8, 12.0),
            "staff_notes": random.choice(["Normal flow", "High volume", "Minor delay", "Processing smoothly"]),
            "reporting_delay": random.randint(1, 5),
            "sensor_timestamp": now
        }
        
        try:
            queue_data_ingestion.ingest_manual_data(db, manual_data)
        except:
            pass


def _generate_queue_events(db: Session, now: datetime):
    """Generate synthetic queue events from sensor data."""
    # These will be automatically created when sensor data is ingested
    # But we can add some manual events for variety
    if random.random() < 0.4:
        from ..models import QueueEvent
        event = QueueEvent(
            event_id=f"EV-{now.strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}",
            checkpoint_id=f"CP-{random.choice(['SEC1', 'CHK1', 'BRD1', 'IMM1'])}",
            checkpoint_type=random.choice(["security", "checkin", "boarding", "immigration"]),
            terminal=random.choice(["T1", "T2", "T3"]),
            gate=random.choice(["A1", "A2", "B1", "B2"]) if random.random() < 0.5 else None,
            current_queue_length=random.randint(2, 50),
            queue_density=random.uniform(0.1, 2.5),
            average_wait_time=random.randint(1, 25),
            peak_wait_time=random.randint(5, 40),
            service_rate=random.uniform(0.5, 10.0),
            capacity_utilization=random.uniform(0.1, 0.9),
            arrival_rate=random.uniform(0.5, 8.0),
            departure_rate=random.uniform(0.5, 8.0),
            flow_efficiency=random.uniform(0.3, 1.0),
            congestion_level=random.choice(["low", "medium", "high", "critical"]),
            trend_direction=random.choice(["increasing", "stable", "decreasing"]),
            anomaly_detected=random.random() < 0.1,
            contributing_flights=json.dumps([random.randint(1000, 9999) for _ in range(random.randint(1, 3))]),
            event_timestamp=now,
            created_at=now
        )
        db.add(event)


def _update_queue_states(db: Session, now: datetime):
    """Update synthetic queue states."""
    # Get existing states and update them
    states = db.query(QueueState).all()
    
    if not states:
        # Create initial states
        for i in range(5):
            state = QueueState(
                checkpoint_id=f"CP-{i+1}",
                checkpoint_type=random.choice(["security", "checkin", "boarding", "immigration"]),
                terminal=random.choice(["T1", "T2", "T3"]),
                gate=random.choice(["A1", "A2", "B1", "B2"]) if random.random() < 0.5 else None,
                current_queue_length=random.randint(2, 40),
                current_wait_time=random.randint(1, 20),
                current_capacity_utilization=random.uniform(0.1, 0.8),
                total_lanes=random.randint(2, 4),
                active_lanes=random.randint(1, 3),
                lane_status=json.dumps({
                    f"lane_{j+1}": {
                        "status": random.choice(["active", "inactive"]),
                        "queue_length": random.randint(0, 20)
                    } for j in range(random.randint(2, 4))
                }),
                average_service_time=random.uniform(1.0, 4.0),
                peak_queue_length=random.randint(10, 60),
                total_processed_today=random.randint(100, 1000),
                predicted_length_10min=random.randint(5, 45),
                predicted_length_20min=random.randint(5, 45),
                predicted_length_30min=random.randint(5, 45),
                prediction_confidence=random.uniform(0.5, 0.9),
                alert_threshold_length=random.randint(25, 40),
                alert_threshold_wait=random.randint(15, 25),
                last_updated=now,
                created_at=now
            )
            db.add(state)
    else:
        # Update existing states
        for state in states:
            # Update with realistic changes
            state.current_queue_length = max(0, state.current_queue_length + random.randint(-5, 8))
            state.current_wait_time = max(0, state.current_wait_time + random.randint(-2, 4))
            state.current_capacity_utilization = max(0, min(1, state.current_capacity_utilization + random.uniform(-0.1, 0.15)))
            state.total_processed_today += random.randint(5, 25)
            state.last_updated = now


def _generate_queue_predictions(db: Session, now: datetime):
    """Generate synthetic queue predictions."""
    states = db.query(QueueState).all()
    
    for state in states:
        if random.random() < 0.6:  # 60% chance to generate predictions
            for horizon in [10, 20, 30]:
                prediction = QueuePrediction(
                    checkpoint_id=state.checkpoint_id,
                    prediction_horizon=horizon,
                    model_version="synthetic_v1.0",
                    current_queue_length=state.current_queue_length,
                    current_wait_time=state.current_wait_time,
                    flight_schedules=json.dumps([
                        {"flight_id": random.randint(1000, 9999), "passengers": random.randint(50, 300)}
                        for _ in range(random.randint(1, 3))
                    ]),
                    historical_patterns=json.dumps({
                        "hour_of_day": now.hour,
                        "factor": random.uniform(0.8, 1.2)
                    }),
                    predicted_queue_length=state.current_queue_length + random.randint(-10, 15),
                    predicted_wait_time=state.current_wait_time + random.randint(-3, 5),
                    confidence_score=random.uniform(0.5, 0.9),
                    prediction_range=json.dumps({
                        "min": max(0, state.current_queue_length - 10),
                        "max": state.current_queue_length + 20,
                        "std": random.uniform(2, 8)
                    }),
                    prediction_timestamp=now,
                    target_timestamp=now + timedelta(minutes=horizon),
                    created_at=now
                )
                db.add(prediction)


def _generate_lane_recommendations(db: Session, now: datetime):
    """Generate synthetic lane recommendations."""
    states = db.query(QueueState).all()
    
    for state in states:
        if random.random() < 0.3:  # 30% chance to generate recommendations
            recommendation = LaneRecommendation(
                recommendation_id=f"LR-{now.strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}",
                checkpoint_id=state.checkpoint_id,
                recommendation_type=random.choice(["open_lane", "close_lane", "reconfigure"]),
                current_lanes=state.total_lanes,
                active_lanes=state.active_lanes,
                current_queue_length=state.current_queue_length,
                current_wait_time=state.current_wait_time,
                recommended_lanes=state.active_lanes + random.choice([-1, 0, 1]),
                recommended_action=random.choice([
                    "Open additional lane to reduce wait times",
                    "Close underutilized lane to save resources",
                    "Reconfigure lane assignment for better flow"
                ]),
                priority_level=random.choice(["low", "medium", "high", "critical"]),
                impact_assessment=random.choice([
                    "Expected 30% reduction in wait time",
                    "Cost savings of $50 per hour",
                    "Improved passenger flow efficiency"
                ]),
                trigger_metric=random.choice(["queue_length", "wait_time", "utilization"]),
                trigger_value=random.uniform(10, 50),
                threshold_exceeded=random.choice([True, False]),
                recommended_by="automated_system",
                created_at=now,
                expires_at=now + timedelta(hours=random.randint(1, 4))
            )
            db.add(recommendation)


def _detect_passenger_waves(db: Session, now: datetime):
    """Generate synthetic passenger wave detections."""
    if random.random() < 0.4:  # 40% chance to detect waves
        wave = PassengerWave(
            wave_id=f"WV-{now.strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}",
            wave_type=random.choice(["departure_wave", "arrival_wave", "transfer_wave"]),
            terminal=random.choice(["T1", "T2", "T3"]),
            start_time=now - timedelta(minutes=random.randint(30, 120)),
            peak_time=now - timedelta(minutes=random.randint(15, 60)),
            end_time=now + timedelta(minutes=random.randint(30, 90)),
            duration_minutes=random.randint(60, 180),
            clustered_flights=json.dumps([
                {"flight_id": random.randint(1000, 9999), "passengers": random.randint(100, 400)}
                for _ in range(random.randint(2, 6))
            ]),
            total_passengers=random.randint(200, 1500),
            peak_flow_rate=random.uniform(5, 25),
            average_flow_rate=random.uniform(3, 15),
            affected_checkpoints=json.dumps([f"CP-{i}" for i in range(1, random.randint(3, 6))]),
            peak_queue_lengths=json.dumps({
                f"CP-{i}": random.randint(20, 80) for i in range(1, random.randint(3, 6))
            }),
            congestion_duration=random.randint(30, 120),
            predicted_start_time=now - timedelta(minutes=random.randint(45, 90)) if random.random() < 0.6 else None,
            predicted_peak_flow=random.uniform(8, 30) if random.random() < 0.5 else None,
            prediction_confidence=random.uniform(0.5, 0.9),
            detected_at=now,
            updated_at=now
        )
        db.add(wave)


def _generate_flow_visualization_data(db: Session, now: datetime):
    """Generate synthetic flow visualization data."""
    terminals = ["T1", "T2", "T3"]
    
    for terminal in terminals:
        if random.random() < 0.5:  # 50% chance to generate heatmap
            # Create density grid
            grid_width, grid_height = 40, 30
            density_grid = []
            
            for y in range(grid_height):
                row = []
                for x in range(grid_width):
                    # Create realistic density patterns
                    base_density = random.uniform(0, 0.3)
                    
                    # Add some hotspots
                    if random.random() < 0.1:
                        base_density = random.uniform(0.7, 1.0)
                    
                    row.append(base_density)
                density_grid.append(row)
            
            # Identify congestion zones
            congestion_zones = []
            for i in range(random.randint(1, 4)):
                zone = {
                    "zone_id": i,
                    "cells": [(random.randint(5, 35), random.randint(5, 25)) for _ in range(random.randint(3, 8))],
                    "center_x": random.randint(10, 30),
                    "center_y": random.randint(10, 20),
                    "peak_density": random.uniform(0.6, 1.0),
                    "area_size": random.randint(3, 8)
                }
                congestion_zones.append(zone)
            
            heatmap = TerminalHeatmap(
                heatmap_id=f"HM-{terminal}-{now.strftime('%Y%m%d%H%M%S')}",
                terminal=terminal,
                floor_level=random.choice(["ground", "departure", "arrival"]),
                grid_resolution=5,
                grid_width=grid_width,
                grid_height=grid_height,
                density_data=json.dumps(density_grid),
                congestion_zones=json.dumps(congestion_zones),
                flow_directions=json.dumps([
                    {"checkpoint_id": f"CP-{i}", "direction": random.choice(["north", "south", "east", "west"]), 
                     "magnitude": random.uniform(0.1, 1.0), "angle": random.randint(0, 360)}
                    for i in range(1, random.randint(2, 5))
                ]),
                congestion_levels=json.dumps({
                    "low": "#00FF00", "medium": "#FFFF00", 
                    "high": "#FFA500", "critical": "#FF0000"
                }),
                peak_density=max(max(row) for row in density_grid),
                average_density=sum(sum(row) for row in density_grid) / (grid_width * grid_height),
                total_passengers=random.randint(100, 800),
                timestamp=now,
                contributing_flights=json.dumps([random.randint(1000, 9999) for _ in range(random.randint(1, 5))]),
                created_at=now,
                expires_at=now + timedelta(minutes=15)
            )
            db.add(heatmap)

    _generator_thread = None
    _stop_event = None

