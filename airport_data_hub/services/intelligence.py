"""
Rules-based intelligence: auto-create alerts from hub data.
Makes the Data Hub feel AI-ready and feeds Disruption Copilot / dashboard.
"""
from datetime import timedelta
from sqlalchemy.orm import Session

from ..crud import (
    get_passenger_flows,
    get_runways,
    get_infrastructure_assets,
    get_flights,
    get_flight_by_id,
    get_flights_by_gate,
    create_alert,
)
from ..models import Flight

# Thresholds (hackathon-friendly; can move to config later)
SECURITY_QUEUE_THRESHOLD = 80
GRIP_SCORE_LOW_THRESHOLD = 0.4
GATE_OCCUPANCY_DEFAULT_MINUTES = 90


def _flight_end_time(f: Flight):
    """Use estimated_time or scheduled + default occupancy for overlap check."""
    if f.estimated_time is not None:
        return f.estimated_time
    return f.scheduled_time + timedelta(minutes=GATE_OCCUPANCY_DEFAULT_MINUTES)


def run_queue_alerts(db: Session) -> int:
    """If any recent passenger_flow has security_queue_count > threshold, create alert (dedup by uniqueness_key)."""
    created = 0
    flows = get_passenger_flows(db, skip=0, limit=50)
    for pf in flows:
        if pf.security_queue_count >= SECURITY_QUEUE_THRESHOLD:
            flight = get_flight_by_id(db, pf.flight_id)
            flight_ref = flight.flight_code if flight else f"flight_id={pf.flight_id}"
            key = f"queue:passenger_flow:{pf.id}"
            if create_alert(
                db,
                alert_type="queue",
                message=f"Security queue count high: {pf.security_queue_count} at {pf.terminal_zone or 'N/A'} for {flight_ref}",
                severity="warning",
                source_module="data_hub",
                related_entity_type="passenger_flow",
                related_entity_id=pf.id,
                uniqueness_key=key,
            ):
                created += 1
    return created


def run_runway_hazard_alerts(db: Session) -> int:
    """If hazard_detected on any runway, create alert. If grip_score too low, create alert (dedup by uniqueness_key)."""
    created = 0
    for r in get_runways(db):
        if r.hazard_detected:
            key = f"runway_hazard:runway:{r.id}"
            if create_alert(
                db,
                alert_type="runway_hazard",
                message=f"Runway {r.runway_code}: hazard detected - {r.hazard_type or 'unknown'}",
                severity="critical",
                source_module="data_hub",
                related_entity_type="runway",
                related_entity_id=r.id,
                uniqueness_key=key,
            ):
                created += 1
        if r.grip_score is not None and r.grip_score < GRIP_SCORE_LOW_THRESHOLD:
            key = f"grip:runway:{r.id}"
            if create_alert(
                db,
                alert_type="grip",
                message=f"Runway {r.runway_code}: low grip score {r.grip_score:.2f}",
                severity="warning",
                source_module="data_hub",
                related_entity_type="runway",
                related_entity_id=r.id,
                uniqueness_key=key,
            ):
                created += 1
    return created


def run_tamper_alerts(db: Session) -> int:
    """If tamper_detected on any infrastructure asset, create critical alert (dedup by uniqueness_key)."""
    created = 0
    for asset in get_infrastructure_assets(db):
        if asset.tamper_detected:
            key = f"security:infrastructure:{asset.id}"
            if create_alert(
                db,
                alert_type="security",
                message=f"Infrastructure tamper detected: {asset.asset_name} at {asset.location or 'N/A'}",
                severity="critical",
                source_module="data_hub",
                related_entity_type="infrastructure",
                related_entity_id=asset.id,
                uniqueness_key=key,
            ):
                created += 1
    return created


def run_gate_conflict_alerts(db: Session) -> int:
    """If two flights share the same gate with overlapping times, create conflict alert (dedup by uniqueness_key)."""
    created = 0
    flights = get_flights(db, limit=200)
    gates_seen = set()
    for f in flights:
        if not f.gate or f.gate in gates_seen:
            continue
        gates_seen.add(f.gate)
        by_gate = get_flights_by_gate(db, f.gate)
        for i, a in enumerate(by_gate):
            end_a = _flight_end_time(a)
            for b in by_gate[i + 1 :]:
                start_b = b.scheduled_time
                end_b = _flight_end_time(b)
                if start_b < end_a and a.scheduled_time < end_b:
                    key = f"gate_conflict:flight:{a.id}_{b.id}"
                    if create_alert(
                        db,
                        alert_type="gate_conflict",
                        message=f"Gate {a.gate}: flights {a.flight_code} and {b.flight_code} overlap",
                        severity="warning",
                        source_module="data_hub",
                        related_entity_type="flight",
                        related_entity_id=f"{a.id}_{b.id}",
                        uniqueness_key=key,
                    ):
                        created += 1
    return created


def run_all_intelligence(db: Session) -> dict:
    """Run all rules and return counts of alerts created per rule type."""
    return {
        "queue_alerts": run_queue_alerts(db),
        "runway_alerts": run_runway_hazard_alerts(db),
        "tamper_alerts": run_tamper_alerts(db),
        "gate_conflict_alerts": run_gate_conflict_alerts(db),
    }
