"""
Flight reconciliation: merge conflicting sources (Flight base + FlightUpdates + predicted_eta)
into single reconciled values with reason, confidence, timestamp.
Raw source data stays in Flight (status, gate, estimated_time) and FlightUpdate; reconciled in Flight.reconciled_*.
"""
from datetime import datetime
from sqlalchemy.orm import Session

from ..crud import (
    get_flights,
    get_flight_updates_for_flight,
    update_flight_reconciliation,
)


def _latest_update(updates: list) -> object | None:
    """Return the most recent update by reported_at, or None if empty."""
    if not updates:
        return None
    return max(updates, key=lambda u: u.reported_at or datetime.min)


def run_flight_reconciliation(db: Session) -> int:
    """
    For each flight: compute reconciled_eta, reconciled_status, reconciled_gate from
    latest FlightUpdate (reported_eta, reported_status, reported_gate) or fallback to Flight fields / predicted_eta.
    Every reconciliation sets: reconciled value, confidence, reason, last_reconciled_at.
    Returns number of flights updated.
    """
    updated = 0
    flights = get_flights(db, limit=500)
    for flight in flights:
        updates = get_flight_updates_for_flight(db, flight.id)
        latest = _latest_update(updates)

        # ETA: latest reported_eta > predicted_eta > estimated_time > scheduled_time
        reconciled_eta = None
        eta_reason = ""
        eta_confidence = 0.0
        if latest and getattr(latest, "reported_eta", None):
            reconciled_eta = latest.reported_eta
            eta_reason = "latest_reported"
            eta_confidence = getattr(latest, "confidence_score", None) or 0.9
        elif flight.predicted_eta:
            reconciled_eta = flight.predicted_eta
            eta_reason = "prediction"
            eta_confidence = flight.prediction_confidence or 0.7
        elif flight.estimated_time:
            reconciled_eta = flight.estimated_time
            eta_reason = "canonical_estimated"
            eta_confidence = 0.6
        else:
            reconciled_eta = flight.scheduled_time
            eta_reason = "schedule"
            eta_confidence = 0.5

        # Status: latest reported_status or flight.status
        if latest and getattr(latest, "reported_status", None):
            reconciled_status = latest.reported_status
            status_reason = "latest_reported"
        else:
            reconciled_status = flight.status
            status_reason = "canonical"

        # Gate: latest reported_gate or flight.gate
        if latest and getattr(latest, "reported_gate", None):
            reconciled_gate = latest.reported_gate
            gate_reason = "latest_reported"
        else:
            reconciled_gate = flight.gate
            gate_reason = "canonical"

        reason = f"eta={eta_reason} status={status_reason} gate={gate_reason}"
        confidence = min(eta_confidence, 0.9)  # single scalar for record

        update_flight_reconciliation(
            db,
            flight.id,
            reconciled_eta=reconciled_eta,
            reconciled_status=reconciled_status,
            reconciled_gate=reconciled_gate,
            reconciliation_reason=reason,
            reconciliation_confidence=round(confidence, 4),
        )
        updated += 1
    return updated
