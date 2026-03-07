"""
Model loading and inference for arrival delay prediction.
Hardened: outcome type (ml_model | rules_fallback | insufficient_data),
confidence, fallback mode, missing features, stale data warnings, operational reason codes.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .config import (
    DEFAULT_MODEL_PATH,
    MODEL_VERSION,
    REASON_CODES_TOP_K,
    MIN_INPUT_QUALITY_FOR_ML,
)
from . import features as feat
from . import operational_codes as op_codes

logger = logging.getLogger(__name__)

_model_obj: Any = None
_feature_names: list[str] = []

# Outcome types for audit and API
OUTCOME_ML_MODEL = "ml_model"
OUTCOME_RULES_FALLBACK = "rules_fallback"
OUTCOME_INSUFFICIENT_DATA = "insufficient_data"


def get_feature_names() -> list[str]:
    """Order of features expected by the model. Must match training."""
    return [
        "hours_until_scheduled_departure",
        "delay_at_origin_min",
        "hour_of_day",
        "day_of_week",
        "airline_enc",
        "origin_enc",
        "destination_enc",
        "reported_status_enc",
    ]


def load_model(path: Optional[Path] = None) -> bool:
    """Load model from disk. Returns True if loaded, False if using stub."""
    global _model_obj, _feature_names
    path = path or DEFAULT_MODEL_PATH
    if not path.exists():
        logger.warning("No model at %s; using stub predictor.", path)
        _model_obj = None
        _feature_names = get_feature_names()
        return False
    try:
        import joblib
        _model_obj = joblib.load(path)
        if isinstance(_model_obj, dict):
            _feature_names = _model_obj.get("feature_names", get_feature_names())
            _model_obj = _model_obj.get("model", _model_obj)
        else:
            _feature_names = get_feature_names()
        logger.info("Loaded model from %s", path)
        return True
    except Exception as e:
        logger.exception("Failed to load model: %s", e)
        _model_obj = None
        _feature_names = get_feature_names()
        return False


def _stub_predict(features: dict[str, Any]) -> tuple[float, float, list[tuple[str, float]]]:
    """Rules-based fallback: propagate origin delay with decay."""
    delay_at_origin = features.get("delay_at_origin_min") or 0.0
    delay_min = delay_at_origin * 0.9
    confidence = 0.5  # Lower than ML to signal fallback
    reason_codes = [
        ("delay_at_origin_min", delay_at_origin),
        ("hours_until_scheduled_departure", 0.0),
    ]
    return delay_min, confidence, reason_codes[:REASON_CODES_TOP_K]


def _encode_features_for_vector(features: dict[str, Any]) -> dict[str, Any]:
    out = dict(features)
    for key in ["airline", "origin", "destination", "reported_status_latest"]:
        v = features.get(key) or "UNK"
        out[f"{key.replace('_latest','')}_enc"] = float(hash(str(v)) % 10000) / 10000.0
    return out


def predict(
    flight: dict,
    flight_updates: list[dict],
    prediction_time: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Run prediction. Returns dict with:
    - predicted_arrival_delay_min, predicted_arrival_time, confidence_score
    - prediction_outcome: ml_model | rules_fallback | insufficient_data
    - fallback_used: bool
    - input_quality_score, missing_features, stale_data_warnings
    - reason_codes (ML/stub factor names), operational_reason_codes (airport-ops language)
    - features_used, model_version, prediction_timestamp
    """
    pt = prediction_time or datetime.utcnow()
    features, meta = feat.build_features(flight, flight_updates, pt)
    missing_features = meta.get("missing_features", [])
    input_quality_score = meta.get("input_quality_score", 0.0)
    stale_data_warnings = meta.get("stale_data_warnings", [])

    # Insufficient data: do not run model/fallback for delay; return safe default
    if input_quality_score < MIN_INPUT_QUALITY_FOR_ML:
        features_snapshot = _serialize_features(features)
        sched = features.get("scheduled_arrival")
        pred_time = sched if isinstance(sched, datetime) else None
        return {
            "predicted_arrival_delay_min": 0.0,
            "predicted_arrival_time": pred_time,
            "confidence_score": 0.0,
            "prediction_outcome": OUTCOME_INSUFFICIENT_DATA,
            "fallback_used": False,
            "input_quality_score": input_quality_score,
            "missing_features": missing_features,
            "stale_data_warnings": stale_data_warnings,
            "reason_codes": [],
            "operational_reason_codes": [{
                "factor": "insufficient_data",
                "contribution": 0.0,
                "operational_code": "insufficient_data",
                "operational_phrase": "Insufficient or stale data for prediction",
            }],
            "features_used": features_snapshot,
            "model_version": MODEL_VERSION,
            "prediction_timestamp": pt,
        }

    encoded = _encode_features_for_vector(features)
    feature_names = get_feature_names()
    vector = feat.feature_vector_for_model(encoded, feature_names)

    outcome = OUTCOME_RULES_FALLBACK
    model_version_used = f"{MODEL_VERSION}-rules"
    delay_min: float = 0.0
    confidence: float = 0.5
    reason_codes: list[tuple[str, float]] = []

    if _model_obj is not None:
        try:
            import numpy as np
            X = np.array([vector])
            delay_min = float(_model_obj.predict(X)[0])
            delay_min = max(-60.0, min(300.0, delay_min))
            if hasattr(_model_obj, "feature_importances_"):
                imp = _model_obj.feature_importances_
                indices = sorted(range(len(imp)), key=lambda i: -imp[i])[:REASON_CODES_TOP_K]
                reason_codes = [(feature_names[i], float(imp[i])) for i in indices]
            elif hasattr(_model_obj, "coef_"):
                coef = _model_obj.coef_
                indices = sorted(range(len(coef)), key=lambda i: -abs(coef[i]))[:REASON_CODES_TOP_K]
                reason_codes = [(feature_names[i], float(coef[i])) for i in indices]
            else:
                reason_codes = [("model_internal", 1.0)]
            confidence = 0.7
            outcome = OUTCOME_ML_MODEL
            model_version_used = MODEL_VERSION
        except Exception as e:
            logger.exception("Model predict failed: %s", e)
            delay_min, confidence, reason_codes = _stub_predict(features)
            outcome = OUTCOME_RULES_FALLBACK
            model_version_used = f"{MODEL_VERSION}-rules"
    else:
        delay_min, confidence, reason_codes = _stub_predict(features)

    scheduled_arrival = features.get("scheduled_arrival")
    if scheduled_arrival and isinstance(scheduled_arrival, datetime):
        predicted_arrival_time = scheduled_arrival + timedelta(minutes=delay_min)
    else:
        predicted_arrival_time = None

    operational_reason_codes = op_codes.to_operational(reason_codes)
    features_snapshot = _serialize_features(features)

    return {
        "predicted_arrival_delay_min": round(delay_min, 2),
        "predicted_arrival_time": predicted_arrival_time,
        "confidence_score": round(confidence, 4),
        "prediction_outcome": outcome,
        "fallback_used": outcome == OUTCOME_RULES_FALLBACK,
        "input_quality_score": input_quality_score,
        "missing_features": missing_features,
        "stale_data_warnings": stale_data_warnings,
        "reason_codes": [{"factor": f, "contribution": round(c, 4)} for f, c in reason_codes],
        "operational_reason_codes": operational_reason_codes,
        "features_used": features_snapshot,
        "model_version": model_version_used,
        "prediction_timestamp": pt,
    }


def _serialize_features(features: dict[str, Any]) -> dict[str, Any]:
    """JSON-safe feature snapshot for audit."""
    out = {}
    for k, v in features.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
