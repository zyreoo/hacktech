# Arrival Delay Prediction Hardening (Self-Healing AODB)

## A. Proposed improvements (integrated hub, no microservices)

- **Prediction outcome type**: Every response and audit row records how the prediction was produced: `ml_model` | `rules_fallback` | `insufficient_data`. This supports operations dashboards and SLA reporting.
- **Confidence score (0–1)**: Kept; semantics: 0 = do not use for decisions, 1 = high trust. Fallback and insufficient-data outcomes carry lower confidence.
- **Fallback mode**: When no model is loaded or model predict fails, use rules-based delay propagation (origin delay × decay). Explicitly flagged so AODB/UI can show "estimated (rules)" vs "predicted (model)".
- **Missing features reporting**: Features that were imputed or absent (e.g. no `reported_eta`, no flight updates) are returned in `missing_features`. Supports data quality monitoring and targeting which feeds to improve.
- **Stale data detection**: Compare prediction_time to latest flight update and scheduled times. Emit warnings when latest update is older than a threshold (e.g. 2h) or flight is in the past. Stored in audit for traceability.
- **Input quality score (0–1)**: Single scalar from completeness and freshness: more recent updates and fewer missing critical features → higher score. Enables filtering or alerting when quality is low.
- **Operational reason codes**: In addition to ML factor names, return airport-operations language (e.g. "origin_delay", "no_live_eta", "scheduled_on_time"). Mapped from model/stub factors so AODB and ops teams get consistent explanations.
- **Feature freshness validation**: Before running model, check: (1) age of latest flight update vs `MAX_UPDATE_AGE_HOURS`, (2) whether scheduled times are in the past, (3) presence of required fields. Used to set outcome to `insufficient_data` when data is too stale or incomplete for a trustworthy prediction.
- **PredictionAudit extension**: Store `prediction_outcome`, `input_quality_score`, `missing_features` (JSON), `stale_data_warnings` (JSON), `operational_reason_codes` (JSON) so every prediction is traceable and auditable.

## B. Updated API contract

**POST /predict** request: unchanged — `{"flight_id": int}`.

**POST /predict** response (PredictResponse):

| Field | Type | Description |
|-------|------|-------------|
| flight_id | int | As requested |
| prediction_timestamp | datetime | When prediction was run |
| model_version | str | Model version or "rules-fallback" |
| predicted_arrival_delay_min | float | Minutes delay (may be 0 for insufficient_data) |
| predicted_arrival_time | datetime? | ETA if computable |
| confidence_score | float | 0–1 |
| **prediction_outcome** | str | "ml_model" \| "rules_fallback" \| "insufficient_data" |
| **fallback_used** | bool | True if rules used instead of ML |
| **input_quality_score** | float | 0–1 |
| **missing_features** | list[str] | Feature names missing or imputed |
| **stale_data_warnings** | list[str] | Human-readable staleness warnings |
| **operational_reason_codes** | list[{factor, contribution, operational_phrase}] | Ops language |
| reason_codes | list[{factor, contribution}] | ML/stub factor names (unchanged) |
| features_used | dict? | Snapshot for audit |

**GET /predictions**, **GET /predictions/flights/{id}**: response includes new audit fields where present.

## C. Updated PredictionAudit schema design

New/added columns (SQLite; migration in database.py):

| Column | Type | Description |
|--------|------|-------------|
| prediction_outcome | VARCHAR(32) | ml_model, rules_fallback, insufficient_data |
| input_quality_score | REAL | 0–1 |
| missing_features | TEXT | JSON array of feature names |
| stale_data_warnings | TEXT | JSON array of warning strings |
| operational_reason_codes | TEXT | JSON array of {factor, contribution, operational_phrase} |

Existing columns kept: flight_id, prediction_timestamp, model_version, predicted_arrival_delay_min, predicted_arrival_time, confidence_score, reason_codes, features_snapshot, created_at.

## D. Feature freshness and self-healing logic

- **Required for ML**: scheduled_departure and scheduled_arrival (or derived) present; at least one of reported_eta or delay_at_origin_min available for delay context (or we accept 0). Optional: latest update within MAX_UPDATE_AGE_HOURS.
- **Freshness checks**: (1) `latest_update_age_hours` = (prediction_time - latest reported_at); if > MAX_UPDATE_AGE_HOURS, add warning "Flight updates are older than X hours". (2) If scheduled_departure < prediction_time (flight already departed), add "Flight already departed; prediction based on schedule and last update".
- **Input quality score**: Start at 1.0. Deduct for: missing critical features (scheduled times, origin/destination); no flight updates; stale updates (e.g. −0.2 per threshold breach). Clamp to [0, 1].
- **Outcome decision**: If input_quality_score < MIN_QUALITY_FOR_ML (e.g. 0.3) or critical features missing → return `insufficient_data`, do not run model/fallback delay (or run fallback but tag outcome as insufficient_data). If model loaded and not insufficient_data → run model; on success outcome=ml_model, on exception outcome=rules_fallback. If model not loaded and not insufficient_data → outcome=rules_fallback.

## E. Evaluation plan (operations-focused)

- **By outcome**: Report MAE/RMSE and % within 5/10/15 min only for predictions where outcome=ml_model (and optionally rules_fallback) so we don’t penalize insufficient_data.
- **Insufficient_data rate**: % of prediction requests that return insufficient_data; target to reduce by improving data feeds.
- **Fallback rate**: % of requests served by rules_fallback; monitor after model deploy.
- **Operational metrics**: (1) % of predictions within 5 / 10 / 15 min of actual arrival delay; (2) false early / false late (predicted on-time but actual delayed, and vice versa); (3) calibration: average confidence vs actual accuracy by band.
- **TODO**: In production (e.g. PostgreSQL), add actual_arrival_time and actual_delay_min when available to compute these in the same DB; batch evaluation job can aggregate by outcome and time window.

---

## F. File-by-file code changes (implemented)

- **airport_data_hub/prediction/config.py**: Added MAX_UPDATE_AGE_HOURS, MIN_INPUT_QUALITY_FOR_ML, REQUIRED_FEATURES_FOR_ML.
- **airport_data_hub/prediction/operational_codes.py**: New module; maps ML factor names to operational_code and operational_phrase.
- **airport_data_hub/prediction/features.py**: build_features now returns (features, meta) with missing_features, input_quality_score, stale_data_warnings, latest_update_at.
- **airport_data_hub/prediction/inference.py**: Outcome type (ml_model | rules_fallback | insufficient_data), fallback path, operational_reason_codes, full response contract.
- **airport_data_hub/models.py**: PredictionAudit columns: prediction_outcome, input_quality_score, missing_features, stale_data_warnings, operational_reason_codes.
- **airport_data_hub/database.py**: _migrate_prediction_audit_columns() for new columns; init_db calls it.
- **airport_data_hub/schemas.py**: PredictResponse and PredictionAuditRead extended; OperationalReasonCode added.
- **airport_data_hub/crud.py**: create_prediction_audit accepts new optional params.
- **airport_data_hub/routes/prediction.py**: Passes new fields to audit and response; _audit_to_read parses new JSON fields.

**Deployment**: Existing SQLite DBs get new columns via `_migrate_prediction_audit_columns()` on next app startup (init_db). No manual migration step required.
