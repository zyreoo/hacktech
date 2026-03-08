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
    FlightReassignUpdate,
    FlightUpdateCreate,
    RunwayHazardUpdate,
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


def get_flight_issues(db: Session, limit: int = 500) -> List[dict]:
    """
    Self-healing and conflicts for flights (runway/gate alignment with operational state).
    Returns: list of { type, flight_id, flight_code?, runway_id?, runway_code?, gate?, message, severity, suggested_action }.
    """
    from collections import defaultdict
    flights = get_flights(db, skip=0, limit=limit)
    runways = get_runways(db)
    runway_by_id = {r.id: r for r in runways}
    issues: List[dict] = []

    for f in flights:
        if f.status and (f.status.lower() in ("cancelled", "departed", "arrived")):
            continue
        if f.runway_id is not None:
            rw = runway_by_id.get(f.runway_id)
            if rw and (rw.status or "").lower() in ("closed", "maintenance"):
                issues.append({
                    "type": "runway_unavailable",
                    "flight_id": f.id,
                    "flight_code": f.flight_code,
                    "runway_id": f.runway_id,
                    "runway_code": rw.runway_code,
                    "gate": getattr(f, "reconciled_gate", None) or f.gate,
                    "message": f"Flight {f.flight_code} is assigned to runway {rw.runway_code} which is {rw.status}.",
                    "severity": "critical",
                    "suggested_action": "Reassign flight to an active runway.",
                })

    flights_by_gate: dict = defaultdict(list)
    for f in flights:
        gate = getattr(f, "reconciled_gate", None) or f.gate
        if gate and (f.status or "").lower() not in ("cancelled", "departed", "arrived"):
            flights_by_gate[gate].append(f)
    for gate, flist in flights_by_gate.items():
        if len(flist) > 1:
            for f in flist:
                issues.append({
                    "type": "gate_conflict",
                    "flight_id": f.id,
                    "flight_code": f.flight_code,
                    "runway_id": None,
                    "runway_code": None,
                    "gate": gate,
                    "message": f"Gate {gate} shared by multiple flights: {[x.flight_code for x in flist]}.",
                    "severity": "critical",
                    "suggested_action": "Reassign one flight to another gate.",
                })
    return issues


def update_flight_status(db: Session, id: int, payload: FlightStatusUpdate) -> Optional[Flight]:
    flight = get_flight_by_id(db, id)
    if not flight:
        return None
    flight.status = payload.status
    db.commit()
    db.refresh(flight)
    return flight


def update_flight_reassign(db: Session, id: int, payload: FlightReassignUpdate) -> Optional[Flight]:
    """Reassign flight to another runway or gate (self-healing). Syncs Resource (gate) assignment when gate changes."""
    flight = get_flight_by_id(db, id)
    if not flight:
        return None
    old_gate = (flight.reconciled_gate or flight.gate) if (payload.gate is not None or payload.reconciled_gate is not None) else None
    if payload.runway_id is not None:
        flight.runway_id = payload.runway_id
    if payload.gate is not None:
        flight.gate = payload.gate
    if payload.reconciled_gate is not None:
        flight.reconciled_gate = payload.reconciled_gate
    new_gate = payload.reconciled_gate if payload.reconciled_gate is not None else payload.gate
    if new_gate:
        gate_resource = db.query(Resource).filter(Resource.resource_type == "gate", Resource.resource_name == new_gate).first()
        if gate_resource:
            gate_resource.assigned_to = flight.flight_code
            gate_resource.status = "assigned"
        if old_gate and old_gate != new_gate:
            old_resource = db.query(Resource).filter(Resource.resource_type == "gate", Resource.resource_name == old_gate).first()
            if old_resource and old_resource.assigned_to == flight.flight_code:
                old_resource.assigned_to = None
                old_resource.status = "available"
    db.commit()
    db.refresh(flight)
    return flight


def update_flight_prediction(db: Session, id: int, payload: FlightPredictionUpdate) -> Optional[Flight]:
    """Update flight with prediction results (called by arrival delay prediction service)."""
    flight = get_flight_by_id(db, id)
    if not flight:
        return None
    if payload.predicted_eta is not None:
        flight.predicted_eta = payload.predicted_eta
    if payload.predicted_arrival_delay_min is not None:
        flight.predicted_arrival_delay_min = payload.predicted_arrival_delay_min
    if payload.prediction_confidence is not None:
        flight.prediction_confidence = payload.prediction_confidence
    if payload.prediction_model_version is not None:
        flight.prediction_model_version = payload.prediction_model_version
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


def get_prediction_issues(db: Session, limit: int = 200) -> List[dict]:
    """
    Self-healing and quality issues for predictions.
    Grouped by (flight_id, type) to avoid UI flood; capped at 20 issues.
    Returns: list of { type, prediction_id, flight_id, message, severity, suggested_action }.
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    import json
    rows = list_predictions(db, skip=0, limit=limit)
    raw_issues: List[dict] = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(hours=2)
    flight_cache: dict = {}
    for a in rows:
        fid = a.flight_id
        if fid not in flight_cache:
            flight_cache[fid] = get_flight_by_id(db, fid)
        flight = flight_cache[fid]
        flight_departed = flight and (flight.status or "").lower() in ("departed", "arrived", "cancelled")
        ts = getattr(a, "prediction_timestamp", None) or getattr(a, "created_at", None)
        outcome = getattr(a, "prediction_outcome", None)
        conf = getattr(a, "confidence_score", None)
        iq = getattr(a, "input_quality_score", None)
        mf_raw = getattr(a, "missing_features", None)
        sdw_raw = getattr(a, "stale_data_warnings", None)
        missing_count = 0
        if mf_raw:
            try:
                mf = json.loads(mf_raw) if isinstance(mf_raw, str) else mf_raw
                missing_count = len(mf) if isinstance(mf, list) else 0
            except Exception:
                pass
        stale_count = 0
        if sdw_raw:
            try:
                sdw = json.loads(sdw_raw) if isinstance(sdw_raw, str) else sdw_raw
                stale_count = len(sdw) if isinstance(sdw, list) else 0
            except Exception:
                pass

        # Only report actionable issues: stale (re-run) and low confidence. Skip rules_fallback / poor_input_quality
        # so the UI is not flooded with expected demo behaviour (rules-based predictions are valid).
        if ts and ts < stale_threshold and not flight_departed:
            raw_issues.append({"type": "stale_prediction", "prediction_id": a.id, "flight_id": fid})
        if conf is not None and conf < 0.5:
            raw_issues.append({"type": "low_confidence", "prediction_id": a.id, "flight_id": fid, "conf": conf})

    # Group by (flight_id, type); one issue per group with representative prediction_id
    group_key_to_items: dict = defaultdict(list)
    for item in raw_issues:
        key = (item["flight_id"], item["type"])
        group_key_to_items[key].append(item)

    messages = {
        "stale_prediction": (
            "Flight #{} has {} prediction(s) over 2 hours old (flight may still be active).",
            "Re-run prediction to refresh ETA and delay.",
            "medium",
        ),
        "low_confidence": (
            "Flight #{} has {} prediction(s) with low confidence.",
            "Add more flight updates or verify data quality.",
            "medium",
        ),
        "fallback_or_insufficient": (
            "Flight #{} used rules fallback / insufficient data for {} prediction(s) (not full ML).",
            "Improve input data or accept rules-based estimate.",
            "low",
        ),
        "poor_input_quality": (
            "Flight #{} has {} prediction(s) with poor input quality (missing/stale data).",
            "Ingest more sources or refresh flight updates.",
            "medium",
        ),
    }
    issues: List[dict] = []
    for (fid, itype), items in sorted(group_key_to_items.items()):
        first = items[0]
        pred_id = first["prediction_id"]
        n = len(items)
        msg_tpl, action, sev = messages.get(itype, ("Flight #{} has {} prediction issue(s).", "Review prediction input.", "low"))
        message = msg_tpl.format(fid, n)
        issues.append({
            "type": itype,
            "prediction_id": pred_id,
            "flight_id": fid,
            "message": message,
            "severity": sev,
            "suggested_action": action,
        })
    return issues[:20]


# ----- PassengerFlow -----
def get_passenger_flow_issues(db: Session, limit: int = 300) -> List[dict]:
    """Self-healing / data quality for passenger flow: stale data (grouped by flight), orphan flight_id, invalid counts."""
    from datetime import datetime, timedelta
    flows = get_passenger_flows(db, skip=0, limit=limit)
    issues: List[dict] = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(minutes=30)
    # Group stale flows by flight to avoid flooding the UI (one issue per flight)
    stale_by_flight: dict[int, list] = {}
    for pf in flows:
        if pf.timestamp and pf.timestamp < stale_threshold:
            stale_by_flight.setdefault(pf.flight_id, []).append(pf)
    for flight_id, stale_flows in stale_by_flight.items():
        n = len(stale_flows)
        oldest = min(stale_flows, key=lambda p: p.timestamp or now)
        issues.append({
            "type": "stale_flow",
            "flow_id": oldest.id,
            "flight_id": flight_id,
            "message": f"Flight #{flight_id} has {n} flow record(s) over 30 min old (no recent queue data).",
            "severity": "medium",
            "suggested_action": "Refresh queue data or verify sensor feed.",
        })
    for pf in flows:
        flight = get_flight_by_id(db, pf.flight_id)
        if not flight:
            issues.append({
                "type": "orphan_flow",
                "flow_id": pf.id,
                "flight_id": pf.flight_id,
                "message": f"Flow record #{pf.id} references non-existent flight #{pf.flight_id}.",
                "severity": "high",
                "suggested_action": "Remove or reassign flow data.",
            })
        if (pf.security_queue_count or 0) < 0 or (pf.check_in_count or 0) < 0 or (pf.boarding_count or 0) < 0:
            issues.append({
                "type": "invalid_counts",
                "flow_id": pf.id,
                "flight_id": pf.flight_id,
                "message": f"Flow #{pf.id} has negative queue/count values.",
                "severity": "medium",
                "suggested_action": "Correct sensor or ingestion pipeline.",
            })
    return issues[:50]  # Cap total so UI never floods


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


def update_runway_status(db: Session, id: int, status: str) -> Optional[Runway]:
    runway = get_runway_by_id(db, id)
    if not runway:
        return None
    runway.status = status
    db.commit()
    db.refresh(runway)
    return runway


def get_runway_issues(db: Session) -> List[dict]:
    """
    Self-healing and conflict detection for runways vs flights.
    Returns: list of { type, runway_id, runway_code, flight_id?, flight_code?, message, severity, suggested_action }.
    """
    runways = get_runways(db)
    flights = get_flights(db, skip=0, limit=500)
    issues: List[dict] = []
    flights_by_runway: dict = {}
    for f in flights:
        if f.runway_id is not None:
            flights_by_runway.setdefault(f.runway_id, []).append(f)

    for r in runways:
        rid, rcode, status, hazard, grip = r.id, r.runway_code, (r.status or "").lower(), r.hazard_detected, r.grip_score
        assigned_flights = flights_by_runway.get(rid) or []

        if status in ("closed", "maintenance") and assigned_flights:
            for f in assigned_flights:
                if f.status not in ("cancelled", "departed", "arrived"):
                    issues.append({
                        "type": "runway_unavailable_assigned",
                        "runway_id": rid,
                        "runway_code": rcode,
                        "flight_id": f.id,
                        "flight_code": f.flight_code,
                        "message": f"Runway {rcode} is {status} but flight {f.flight_code} is still assigned to it.",
                        "severity": "critical",
                        "suggested_action": "Reassign flight to another runway or reopen runway.",
                    })
        if hazard and status == "active":
            issues.append({
                "type": "hazard_active_runway",
                "runway_id": rid,
                "runway_code": rcode,
                "flight_id": None,
                "flight_code": None,
                "message": f"Runway {rcode} has hazard detected but status is still active.",
                "severity": "high",
                "suggested_action": "Close runway or clear hazard and update status.",
            })
        if grip is not None and grip < 0.4 and assigned_flights:
            active = [f for f in assigned_flights if f.status not in ("cancelled", "departed", "arrived")]
            if active:
                issues.append({
                    "type": "low_grip_assigned",
                    "runway_id": rid,
                    "runway_code": rcode,
                    "flight_id": active[0].id,
                    "flight_code": active[0].flight_code,
                    "message": f"Runway {rcode} has low grip score ({grip:.2f}) with flight(s) assigned.",
                    "severity": "medium",
                    "suggested_action": "Inspect surface or reassign flights until grip improves.",
                })

    return issues


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
    # Allow clearing assignment when client sends assigned_to: null (release gate)
    if payload.assigned_to is not None:
        resource.assigned_to = payload.assigned_to
    else:
        resource.assigned_to = None
    # When releasing a gate, clear this gate from any flights that reference it so conflicts/orphan issues go away
    if (resource.resource_type or "").lower() == "gate" and payload.assigned_to is None:
        gate_name = resource.resource_name
        if gate_name:
            for flight in db.query(Flight).filter(
                (Flight.gate == gate_name) | (Flight.reconciled_gate == gate_name)
            ).all():
                if flight.gate == gate_name:
                    flight.gate = None
                if flight.reconciled_gate == gate_name:
                    flight.reconciled_gate = None
    db.commit()
    db.refresh(resource)
    return resource


def get_resource_issues(db: Session) -> List[dict]:
    """
    Self-healing and conflict detection for resources vs flights.
    Returns: list of { type, resource_id, resource_name, flight_id?, flight_code?, message, severity, suggested_action }.
    """
    from collections import defaultdict
    resources = get_resources(db, skip=0, limit=500)
    flights = get_flights(db, skip=0, limit=500)
    issues: List[dict] = []
    gate_resources = [r for r in resources if (r.resource_type or "").lower() == "gate"]
    flight_by_code = {f.flight_code: f for f in flights}
    # Flights by gate (gate/reconciled_gate)
    from collections import defaultdict
    flights_by_gate: dict = defaultdict(list)
    for f in flights:
        g = f.reconciled_gate or f.gate
        if g:
            flights_by_gate[g].append(f)

    for r in gate_resources:
        rid, rname, assigned = r.id, r.resource_name, r.assigned_to
        # Orphan: assigned_to flight that doesn't exist or is cancelled
        if assigned:
            flight = flight_by_code.get(assigned)
            if not flight:
                issues.append({
                    "type": "orphan_assignment",
                    "resource_id": rid,
                    "resource_name": rname,
                    "flight_id": None,
                    "flight_code": assigned,
                    "message": f"Gate {rname} assigned to {assigned} but no such flight in AODB.",
                    "severity": "high",
                    "suggested_action": "Unassign gate or add/correct flight.",
                })
            else:
                # Mismatch: flight has different gate than resource
                flight_gate = flight.reconciled_gate or flight.gate
                if flight_gate and flight_gate != rname:
                    issues.append({
                        "type": "gate_mismatch",
                        "resource_id": rid,
                        "resource_name": rname,
                        "flight_id": flight.id,
                        "flight_code": flight.flight_code,
                        "message": f"Gate {rname} assigned to {flight.flight_code} but flight shows gate {flight_gate}.",
                        "severity": "medium",
                        "suggested_action": "Align resource assignment with reconciled gate or update flight gate.",
                    })
                if flight.status in ("cancelled", "departed"):
                    issues.append({
                        "type": "stale_assignment",
                        "resource_id": rid,
                        "resource_name": rname,
                        "flight_id": flight.id,
                        "flight_code": flight.flight_code,
                        "message": f"Gate {rname} still assigned to {flight.flight_code} (status: {flight.status}).",
                        "severity": "medium",
                        "suggested_action": "Release gate for reuse.",
                    })

    # Conflict: multiple flights for same gate
    for gate_name, flist in flights_by_gate.items():
        if len(flist) > 1:
            resource = next((x for x in gate_resources if x.resource_name == gate_name), None)
            issues.append({
                "type": "gate_conflict",
                "resource_id": resource.id if resource else None,
                "resource_name": gate_name,
                "flight_id": None,
                "flight_code": ", ".join(f.flight_code for f in flist),
                "message": f"Gate {gate_name} claimed by multiple flights: {[f.flight_code for f in flist]}.",
                "severity": "critical",
                "suggested_action": "Reassign one flight to another gate or adjust schedule.",
            })

    return issues


# ----- Alerts -----
def get_alert_issues(db: Session, limit: int = 300) -> List[dict]:
    """
    Self-healing and data quality for alerts.
    Only considers unresolved alerts so resolved ones disappear from the issues list.
    Returns: list of { type, alert_id, message, severity, suggested_action, related_entity_type?, related_entity_id? }.
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    alerts = get_alerts(db, resolved=False, skip=0, limit=limit)
    issues: List[dict] = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(hours=24)

    for a in alerts:
        if not a.resolved and a.severity == "critical" and a.created_at < stale_threshold:
            issues.append({
                "type": "stale_critical",
                "alert_id": a.id,
                "message": f"Critical alert #{a.id} has been unresolved for over 24 hours.",
                "severity": "high",
                "suggested_action": "Resolve or escalate; consider auto-resolve policy for old critical alerts.",
                "related_entity_type": a.related_entity_type,
                "related_entity_id": a.related_entity_id,
            })
        entity_type, entity_id = a.related_entity_type, a.related_entity_id
        if entity_type and entity_id:
            rid = entity_id if isinstance(entity_id, str) else str(entity_id)
            exists = False
            if entity_type == "flight":
                try:
                    fid = int(rid)
                    exists = get_flight_by_id(db, fid) is not None
                except (ValueError, TypeError):
                    pass
            elif entity_type == "runway":
                try:
                    rwid = int(rid)
                    exists = get_runway_by_id(db, rwid) is not None
                except (ValueError, TypeError):
                    pass
            elif entity_type == "resource":
                try:
                    res_id = int(rid)
                    exists = get_resource_by_id(db, res_id) is not None
                except (ValueError, TypeError):
                    exists = db.query(Resource).filter(Resource.resource_name == rid).first() is not None
            elif entity_type == "passenger_flow":
                try:
                    pf_id = int(rid)
                    exists = db.query(PassengerFlow).filter(PassengerFlow.id == pf_id).first() is not None
                except (ValueError, TypeError):
                    pass
            elif entity_type == "infrastructure":
                try:
                    asset_id = int(rid)
                    exists = get_infrastructure_asset_by_id(db, asset_id) is not None
                except (ValueError, TypeError):
                    pass
            if not exists:
                issues.append({
                    "type": "orphan_alert",
                    "alert_id": a.id,
                    "message": f"Alert #{a.id} references {entity_type} {entity_id} which no longer exists.",
                    "severity": "medium",
                    "suggested_action": "Resolve alert or fix related entity reference.",
                    "related_entity_type": entity_type,
                    "related_entity_id": entity_id,
                })

    key_to_alerts: dict = defaultdict(list)
    for a in alerts:
        if not a.resolved and a.uniqueness_key:
            key_to_alerts[a.uniqueness_key].append(a)
    for key, group in key_to_alerts.items():
        if len(group) > 1:
            ids = [x.id for x in group]
            issues.append({
                "type": "duplicate_unresolved",
                "alert_id": group[0].id,
                "message": f"Multiple unresolved alerts share key '{key[:50]}...' (ids: {ids}).",
                "severity": "low",
                "suggested_action": "Resolve duplicates; ensure single alert per uniqueness_key.",
                "related_entity_type": group[0].related_entity_type,
                "related_entity_id": group[0].related_entity_id,
            })
    return issues


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


def _alert_entity_exists(db: Session, entity_type: Optional[str], entity_id: Optional[str]) -> bool:
    """Return True if the related entity exists so the alert is not orphaned."""
    if not entity_type or not entity_id:
        return True
    rid = str(entity_id)
    try:
        if entity_type == "flight":
            return get_flight_by_id(db, int(rid)) is not None
        if entity_type == "runway":
            return get_runway_by_id(db, int(rid)) is not None
        if entity_type == "resource":
            try:
                return get_resource_by_id(db, int(rid)) is not None
            except (ValueError, TypeError):
                return db.query(Resource).filter(Resource.resource_name == rid).first() is not None
        if entity_type == "passenger_flow":
            return db.query(PassengerFlow).filter(PassengerFlow.id == int(rid)).first() is not None
        if entity_type == "infrastructure":
            return get_infrastructure_asset_by_id(db, int(rid)) is not None
    except (ValueError, TypeError):
        pass
    return False


def resolve_orphan_alerts(db: Session) -> int:
    """Resolve all unresolved alerts whose related entity no longer exists. Returns count resolved."""
    alerts = get_alerts(db, resolved=False, skip=0, limit=500)
    resolved_count = 0
    for a in alerts:
        if not _alert_entity_exists(db, a.related_entity_type, a.related_entity_id):
            update_alert_resolve(db, a.id, AlertResolveUpdate(resolved=True))
            resolved_count += 1
    return resolved_count


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


def get_infrastructure_issues(db: Session) -> List[dict]:
    """Self-healing: degraded/offline assets, tamper detected."""
    assets = get_infrastructure_assets(db)
    issues: List[dict] = []
    for a in assets:
        if (a.status or "").lower() in ("degraded", "offline", "failed", "maintenance"):
            issues.append({
                "type": "asset_unhealthy",
                "asset_id": a.id,
                "asset_name": a.asset_name,
                "message": f"Asset {a.asset_name} is {a.status}.",
                "severity": "high" if (a.status or "").lower() in ("offline", "failed") else "medium",
                "suggested_action": "Inspect and set to operational when cleared.",
            })
        if getattr(a, "tamper_detected", False):
            issues.append({
                "type": "tamper_detected",
                "asset_id": a.id,
                "asset_name": a.asset_name,
                "message": f"Tamper detected on {a.asset_name}.",
                "severity": "critical",
                "suggested_action": "Verify asset and clear tamper flag when resolved.",
            })
    return issues


# ----- PassengerServices -----
def get_service_issues(db: Session, limit: int = 200) -> List[dict]:
    """Self-healing: stale pending services (e.g. pending > 2 hours)."""
    from datetime import datetime, timedelta
    services = get_passenger_services(db, status=None, skip=0, limit=limit)
    issues: List[dict] = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(hours=2)
    for s in services:
        if (s.status or "").lower() == "pending" and s.request_time < stale_threshold:
            issues.append({
                "type": "stale_pending_service",
                "service_id": s.id,
                "passenger_reference": s.passenger_reference,
                "message": f"Service #{s.id} ({s.service_type}) pending for over 2 hours.",
                "severity": "medium",
                "suggested_action": "Complete or cancel the service request.",
            })
    return issues


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
