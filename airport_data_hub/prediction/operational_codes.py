"""
Map ML/stub factor names to airport-operations language for explainability.
Operations teams see operational_phrase; ML factor names remain in reason_codes for audit.
"""
from typing import List, Tuple

# ML feature name -> (short_code, operational_phrase)
OPERATIONAL_PHRASES: dict[str, tuple[str, str]] = {
    "delay_at_origin_min": ("origin_delay", "Delay at origin airport"),
    "hours_until_scheduled_departure": ("time_to_departure", "Time until scheduled departure"),
    "hour_of_day": ("time_of_day", "Time of day"),
    "day_of_week": ("day_of_week", "Day of week"),
    "airline_enc": ("airline", "Airline"),
    "origin_enc": ("origin", "Origin airport"),
    "destination_enc": ("destination", "Destination airport"),
    "reported_status_enc": ("live_status", "Latest reported status"),
    "reported_status_latest": ("live_status", "Latest reported status"),
    "scheduled_time_proximity": ("scheduled_proximity", "Scheduled time proximity"),
    "model_internal": ("model_estimate", "Model-based estimate"),
}


def to_operational(
    reason_codes: List[Tuple[str, float]],
) -> List[dict]:
    """
    Convert list of (factor, contribution) to list of dicts with operational_phrase.
    For API and audit in airport-operations language.
    """
    out = []
    for factor, contribution in reason_codes:
        code, phrase = OPERATIONAL_PHRASES.get(
            factor, (factor, factor.replace("_", " ").title())
        )
        out.append({
            "factor": factor,
            "contribution": round(contribution, 4),
            "operational_code": code,
            "operational_phrase": phrase,
        })
    return out
