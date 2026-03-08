"""Arrival delay prediction: POST /predict, GET /predictions, GET /predictions/flights/{id}.
Hardened: outcome type, confidence, fallback, missing features, staleness, operational reason codes.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..crud import (
    get_flight_by_id,
    get_flight_updates_for_flight,
    update_flight_prediction,
    create_prediction_audit,
    list_predictions,
    get_predictions_for_flight,
    get_prediction_issues,
)
from ..schemas import (
    PredictRequest,
    PredictResponse,
    PredictionAuditRead,
    PredictionIssueResponse,
    FlightPredictionUpdate,
    ReasonCode,
    OperationalReasonCode,
)
from ..prediction import inference

router = APIRouter(tags=["prediction"])


def _flight_to_dict(flight) -> dict:
    return {
        "id": flight.id,
        "scheduled_time": flight.scheduled_time,
        "estimated_time": flight.estimated_time,
        "origin": flight.origin,
        "destination": flight.destination,
        "airline": flight.airline,
        "status": flight.status,
        "gate": flight.gate,
    }


def _flight_update_to_dict(u) -> dict:
    return {
        "reported_eta": u.reported_eta,
        "reported_status": u.reported_status,
        "reported_gate": u.reported_gate,
        "reported_at": u.reported_at,
    }


@router.post("/predict", response_model=PredictResponse)
def post_predict(payload: PredictRequest, db: Session = Depends(get_db)):
    """Run arrival delay prediction for a flight; store audit and update flight record."""
    flight = get_flight_by_id(db, payload.flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    updates = get_flight_updates_for_flight(db, payload.flight_id)
    flight_dict = _flight_to_dict(flight)
    updates_list = [_flight_update_to_dict(u) for u in updates]
    result = inference.predict(flight_dict, updates_list)

    create_prediction_audit(
        db,
        flight_id=payload.flight_id,
        prediction_timestamp=result["prediction_timestamp"],
        model_version=result["model_version"],
        predicted_arrival_delay_min=result["predicted_arrival_delay_min"],
        predicted_arrival_time=result.get("predicted_arrival_time"),
        confidence_score=result.get("confidence_score"),
        reason_codes=json.dumps(result.get("reason_codes", [])),
        features_snapshot=json.dumps(result.get("features_used") or {}),
        prediction_outcome=result.get("prediction_outcome"),
        input_quality_score=result.get("input_quality_score"),
        missing_features=json.dumps(result.get("missing_features", [])),
        stale_data_warnings=json.dumps(result.get("stale_data_warnings", [])),
        operational_reason_codes=json.dumps(result.get("operational_reason_codes", [])),
    )
    update_flight_prediction(
        db,
        payload.flight_id,
        FlightPredictionUpdate(
            predicted_eta=result.get("predicted_arrival_time"),
            predicted_arrival_delay_min=result["predicted_arrival_delay_min"],
            prediction_confidence=result.get("confidence_score"),
            prediction_model_version=result["model_version"],
        ),
    )

    op_codes = result.get("operational_reason_codes") or []
    return PredictResponse(
        flight_id=payload.flight_id,
        prediction_timestamp=result["prediction_timestamp"],
        model_version=result["model_version"],
        predicted_arrival_delay_min=result["predicted_arrival_delay_min"],
        predicted_arrival_time=result.get("predicted_arrival_time"),
        confidence_score=result.get("confidence_score"),
        prediction_outcome=result.get("prediction_outcome"),
        fallback_used=result.get("fallback_used", False),
        input_quality_score=result.get("input_quality_score"),
        missing_features=result.get("missing_features", []),
        stale_data_warnings=result.get("stale_data_warnings", []),
        operational_reason_codes=[OperationalReasonCode(**x) for x in op_codes] if op_codes else None,
        reason_codes=[ReasonCode(factor=r["factor"], contribution=r["contribution"]) for r in result.get("reason_codes", [])],
        features_used=result.get("features_used"),
    )


@router.get("/predictions", response_model=list[PredictionAuditRead])
def get_predictions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List recent predictions (audit trail)."""
    rows = list_predictions(db, skip=skip, limit=limit)
    return [_audit_to_read(r) for r in rows]


@router.get("/predictions/issues", response_model=list[PredictionIssueResponse])
def get_predictions_issues(limit: int = 200, db: Session = Depends(get_db)):
    """Self-healing and quality: stale, low confidence, fallback, poor input quality."""
    raw = get_prediction_issues(db, limit=limit)
    return [PredictionIssueResponse(**item) for item in raw]


@router.get("/predictions/flights/{flight_id}", response_model=list[PredictionAuditRead])
def get_predictions_for_flight_route(flight_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """List predictions for a specific flight."""
    rows = get_predictions_for_flight(db, flight_id, limit=limit)
    return [_audit_to_read(r) for r in rows]


def _audit_to_read(a) -> PredictionAuditRead:
    reason_codes = None
    if a.reason_codes:
        try:
            raw = json.loads(a.reason_codes)
            reason_codes = [ReasonCode(factor=r["factor"], contribution=r["contribution"]) for r in raw] if isinstance(raw, list) else []
        except Exception:
            reason_codes = []
    missing_features = None
    if getattr(a, "missing_features", None):
        try:
            missing_features = json.loads(a.missing_features)
        except Exception:
            missing_features = []
    stale_data_warnings = None
    if getattr(a, "stale_data_warnings", None):
        try:
            stale_data_warnings = json.loads(a.stale_data_warnings)
        except Exception:
            stale_data_warnings = []
    operational_reason_codes = None
    if getattr(a, "operational_reason_codes", None):
        try:
            raw = json.loads(a.operational_reason_codes)
            operational_reason_codes = [OperationalReasonCode(**x) for x in raw] if isinstance(raw, list) else []
        except Exception:
            operational_reason_codes = []
    return PredictionAuditRead(
        id=a.id,
        flight_id=a.flight_id,
        prediction_timestamp=a.prediction_timestamp,
        model_version=a.model_version,
        predicted_arrival_delay_min=a.predicted_arrival_delay_min,
        predicted_arrival_time=a.predicted_arrival_time,
        confidence_score=a.confidence_score,
        reason_codes=reason_codes,
        created_at=a.created_at,
        prediction_outcome=getattr(a, "prediction_outcome", None),
        input_quality_score=getattr(a, "input_quality_score", None),
        missing_features=missing_features,
        stale_data_warnings=stale_data_warnings,
        operational_reason_codes=operational_reason_codes,
    )
