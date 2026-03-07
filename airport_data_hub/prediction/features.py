"""
Feature preparation for arrival delay prediction.
Builds a feature dict from flight + flight_updates (from hub DB).
Returns feature dict and metadata: missing_features, input_quality_score, stale_data_warnings.
"""
from datetime import datetime, timedelta
from typing import Any, Optional
import logging

from .config import MAX_UPDATE_AGE_HOURS, REQUIRED_FEATURES_FOR_ML

logger = logging.getLogger(__name__)


def build_features(
    flight: dict,
    flight_updates: list[dict],
    prediction_time: Optional[datetime] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Build feature dict and quality/freshness metadata.
    Returns (features, meta) where meta has:
      missing_features: list[str]
      input_quality_score: float 0-1
      stale_data_warnings: list[str]
      latest_update_at: datetime | None
    """
    pt = prediction_time or datetime.utcnow()
    features: dict[str, Any] = {}
    missing_features: list[str] = []
    stale_data_warnings: list[str] = []

    scheduled_departure = _parse_dt(flight.get("scheduled_time"))
    scheduled_arrival = _parse_dt(flight.get("estimated_time")) or _parse_dt(flight.get("scheduled_time"))
    if scheduled_arrival and scheduled_departure and scheduled_arrival == scheduled_departure:
        scheduled_arrival = scheduled_departure + timedelta(hours=2)

    for key in REQUIRED_FEATURES_FOR_ML:
        if key == "scheduled_departure" and not scheduled_departure:
            missing_features.append("scheduled_departure")
        elif key == "scheduled_arrival" and not scheduled_arrival:
            missing_features.append("scheduled_arrival")
        elif key in ("origin", "destination", "airline"):
            val = flight.get(key) or (features.get(key) if key in features else None)
            if not val or (isinstance(val, str) and val == "UNK"):
                missing_features.append(key)

    features["flight_id"] = flight.get("id")
    features["scheduled_departure"] = scheduled_departure
    features["scheduled_arrival"] = scheduled_arrival
    features["origin"] = flight.get("origin") or "UNK"
    features["destination"] = flight.get("destination") or "UNK"
    features["airline"] = flight.get("airline") or "UNK"

    if scheduled_departure:
        delta = (scheduled_departure - pt).total_seconds() / 3600.0
        features["hours_until_scheduled_departure"] = round(delta, 4)
        if scheduled_departure < pt:
            stale_data_warnings.append("Flight already departed; prediction based on schedule and last update")
    else:
        features["hours_until_scheduled_departure"] = None

    reported_eta: Optional[datetime] = None
    reported_status: Optional[str] = None
    reported_gate: Optional[str] = None
    latest_update_at: Optional[datetime] = None
    for u in sorted(flight_updates, key=lambda x: _parse_dt(x.get("reported_at")) or datetime.min, reverse=True):
        ra = _parse_dt(u.get("reported_at"))
        if ra and (latest_update_at is None or ra > latest_update_at):
            latest_update_at = ra
        if u.get("reported_eta"):
            reported_eta = _parse_dt(u["reported_eta"])
        if u.get("reported_status"):
            reported_status = u["reported_status"]
        if u.get("reported_gate"):
            reported_gate = u["reported_gate"]
        if reported_eta is not None and reported_status is not None:
            break

    if not flight_updates:
        missing_features.append("flight_updates")
    elif latest_update_at:
        age_hours = (pt - latest_update_at).total_seconds() / 3600.0
        if age_hours > MAX_UPDATE_AGE_HOURS:
            stale_data_warnings.append(
                f"Flight updates are older than {MAX_UPDATE_AGE_HOURS:.0f} hours ({age_hours:.1f}h)"
            )

    if not reported_eta and "reported_eta_latest" not in missing_features:
        missing_features.append("reported_eta_latest")
    features["reported_eta_latest"] = reported_eta
    features["reported_status_latest"] = reported_status or flight.get("status") or "unknown"
    features["reported_gate_latest"] = reported_gate or flight.get("gate")

    if reported_eta and scheduled_arrival:
        delay_min = (reported_eta - scheduled_arrival).total_seconds() / 60.0
        features["delay_at_origin_min"] = round(delay_min, 2)
    else:
        features["delay_at_origin_min"] = 0.0
        if not reported_eta:
            missing_features.append("delay_at_origin_min")

    if scheduled_departure:
        features["hour_of_day"] = scheduled_departure.hour
        features["day_of_week"] = scheduled_departure.weekday()
    else:
        features["hour_of_day"] = 0
        features["day_of_week"] = 0

    # Input quality: 1.0 minus deductions for missing and staleness
    input_quality_score = 1.0
    input_quality_score -= len(missing_features) * 0.15
    input_quality_score -= len(stale_data_warnings) * 0.2
    input_quality_score = max(0.0, min(1.0, round(input_quality_score, 4)))

    meta = {
        "missing_features": missing_features,
        "input_quality_score": input_quality_score,
        "stale_data_warnings": stale_data_warnings,
        "latest_update_at": latest_update_at,
    }
    return features, meta


def feature_vector_for_model(features: dict[str, Any], feature_names: list[str]) -> list[float]:
    """Convert feature dict to ordered numeric vector for model."""
    out = []
    for name in feature_names:
        v = features.get(name)
        if v is None:
            out.append(0.0)
        elif isinstance(v, (int, float)):
            out.append(float(v))
        elif isinstance(v, datetime):
            out.append(v.timestamp())
        elif isinstance(v, str):
            out.append(float(hash(v) % 10000) / 10000.0)
        else:
            out.append(0.0)
    return out


def _parse_dt(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    return None
