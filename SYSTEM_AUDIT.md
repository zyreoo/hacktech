# Airport Data Hub – Full System Audit

**Purpose:** Complete technical inventory of the existing system. No code changes; documentation only.

---

## 1. Project Structure

```
hacktechairport/
├── .gitignore
├── README.md                    # Project/docs
├── requirements.txt             # Python dependencies (FastAPI, SQLAlchemy, uvicorn, etc.)
├── run_hub.py                   # Entry point: runs uvicorn for airport_data_hub.main:app (e.g. port 8090)
├── start-servers.sh              # Script to start backend + UI (hub + npm run dev)
├── airport_data_hub/            # Backend package
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, CORS, lifespan (init_db, seed, load_model, start_synthetic_feeder)
│   ├── database.py              # SQLite engine, SessionLocal, get_db, init_db, migrations
│   ├── models.py                # SQLAlchemy ORM: Flight, FlightUpdate, PassengerFlow, Runway, Resource, Alert, etc.
│   ├── schemas.py               # Pydantic request/response models (FlightResponse, AlertResponse, OverviewResponse, etc.)
│   ├── crud.py                  # All DB access: get_*, create_*, update_* for every entity
│   ├── seed.py                  # Demo data seeder (flights, runways, flows, alerts, resources, assets, services, identity, retail)
│   ├── run.py                   # Alternate entry (run app)
│   ├── airport_hub.db           # SQLite DB (created at runtime; can be .bak backup)
│   ├── routes/                  # HTTP endpoints
│   │   ├── __init__.py
│   │   ├── flights.py           # GET/PATCH /flights, /flights/{id}, /flights/{id}/updates, /flights/{id}/status, /flights/{id}/prediction
│   │   ├── flight_updates.py    # GET/POST /flight-updates
│   │   ├── runways.py           # GET /runways, GET/PATCH /runways/{id}, /runways/{id}/hazard
│   │   ├── resources.py         # GET /resources, GET/PATCH /resources/{id}, /resources/{id}/status
│   │   ├── alerts.py            # GET /alerts, GET /alerts/{id}, PATCH /alerts/{id}/resolve
│   │   ├── infrastructure.py    # GET /infrastructure, GET/PATCH /infrastructure/{id}, /infrastructure/{id}/status
│   │   ├── passenger_flow.py   # GET /passenger-flow, GET /passenger-flow/by-flight/{flight_id}
│   │   ├── services.py         # GET /services (passenger services)
│   │   ├── identity.py         # GET /identity (digital identity status)
│   │   ├── retail.py           # GET /retail
│   │   ├── overview.py         # GET /overview (intelligence + reconciliation + get_overview)
│   │   ├── aodb.py             # GET /aodb/flights, /aodb/flights/{id}, /aodb/overview
│   │   └── prediction.py       # POST /predict, GET /predictions, GET /predictions/flights/{flight_id}
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── intelligence.py     # Rules that create alerts (queue, runway_hazard, grip, tamper, gate_conflict)
│   │   ├── reconciliation.py    # Computes reconciled_eta, reconciled_status, reconciled_gate per flight
│   │   ├── overview.py         # Builds OverviewResponse from CRUD data (get_overview)
│   │   └── synthetic.py        # Background thread: mutates passenger_flow, runways, infrastructure, optional flight updates
│   ├── prediction/              # Arrival delay prediction
│   │   ├── __init__.py
│   │   ├── config.py           # Model path, version, thresholds (MIN_INPUT_QUALITY_FOR_ML, MAX_UPDATE_AGE_HOURS)
│   │   ├── features.py         # build_features, feature_vector_for_model (from flight + flight_updates)
│   │   ├── inference.py        # load_model, predict (ML or stub fallback), outcome type, reason codes
│   │   └── operational_codes.py # Maps ML factor names to operational_phrase for explainability
│   └── training/               # Model training (separate from runtime)
│       ├── __init__.py
│       ├── train.py            # Train delay model
│       └── evaluate.py         # Evaluation
├── ui/                          # Next.js frontend (not part of this backend audit)
└── venv/                        # Python virtualenv
```

**Root:** `run_hub.py` starts the FastAPI app; `start-servers.sh` can start both backend and UI. **Backend core:** `main.py` wires lifespan (init_db, seed, load prediction model, start synthetic feeder), CORS, and all routers. **Data:** `database.py` defines one SQLite DB (`airport_hub.db` by default); `models.py` defines tables; `crud.py` is the only place that talks to the DB from routes/services. **Routes** expose REST endpoints; **services** implement intelligence, reconciliation, overview building, and synthetic data. **Prediction** is a self-contained module (features, inference, config) used by `routes/prediction.py`.

---

## 2. API Endpoints

| Method | Path | Route file | Function | Returns | Calls |
|--------|------|------------|----------|---------|-------|
| GET | `/` | main.py | root | JSON: message, docs, overview, aodb, predict | — |
| GET | `/overview` | overview.py | overview | OverviewResponse | run_all_intelligence, run_flight_reconciliation, get_overview |
| GET | `/aodb/flights` | aodb.py | aodb_flights | list[FlightResponse] | get_flights |
| GET | `/aodb/flights/{id}` | aodb.py | aodb_flight | FlightResponse | get_flight_by_id |
| GET | `/aodb/overview` | aodb.py | aodb_overview | OverviewResponse | run_all_intelligence, run_flight_reconciliation, get_overview |
| GET | `/flights` | flights.py | list_flights | list[FlightResponse] | get_flights |
| GET | `/flights/{id}` | flights.py | get_flight | FlightResponse | get_flight_by_id |
| GET | `/flights/{id}/updates` | flights.py | get_flight_updates | list[FlightUpdateRead] | get_flight_by_id, get_flight_updates_for_flight |
| PATCH | `/flights/{id}/status` | flights.py | patch_flight_status | FlightResponse | update_flight_status |
| PATCH | `/flights/{id}/prediction` | flights.py | patch_flight_prediction | FlightResponse | update_flight_prediction |
| GET | `/flight-updates` | flight_updates.py | list_updates | list[FlightUpdateRead] | list_flight_updates |
| POST | `/flight-updates` | flight_updates.py | post_flight_update | FlightUpdateRead | get_flight_by_id, create_flight_update |
| GET | `/runways` | runways.py | list_runways | list[RunwayResponse] | get_runways |
| GET | `/runways/{id}` | runways.py | get_runway | RunwayResponse | get_runway_by_id |
| PATCH | `/runways/{id}/hazard` | runways.py | patch_runway_hazard | RunwayResponse | update_runway_hazard |
| GET | `/resources` | resources.py | list_resources | list[ResourceResponse] | get_resources |
| GET | `/resources/{id}` | resources.py | get_resource | ResourceResponse | get_resource_by_id |
| PATCH | `/resources/{id}/status` | resources.py | patch_resource_status | ResourceResponse | update_resource_status |
| GET | `/alerts` | alerts.py | list_alerts | list[AlertResponse] | get_alerts |
| GET | `/alerts/{id}` | alerts.py | get_alert | AlertResponse | get_alert_by_id |
| PATCH | `/alerts/{id}/resolve` | alerts.py | patch_alert_resolve | AlertResponse | update_alert_resolve |
| GET | `/infrastructure` | infrastructure.py | list_infrastructure | list[InfrastructureAssetResponse] | get_infrastructure_assets |
| GET | `/infrastructure/{id}` | infrastructure.py | get_infrastructure_asset | InfrastructureAssetResponse | get_infrastructure_asset_by_id |
| PATCH | `/infrastructure/{id}/status` | infrastructure.py | patch_infrastructure_status | InfrastructureAssetResponse | update_infrastructure_status |
| GET | `/passenger-flow` | passenger_flow.py | list_passenger_flow | list[PassengerFlowResponse] | get_passenger_flows |
| GET | `/passenger-flow/by-flight/{flight_id}` | passenger_flow.py | get_flow_by_flight | list[PassengerFlowResponse] | get_passenger_flow_by_flight |
| GET | `/services` | services.py | list_services | list[PassengerServiceResponse] | get_passenger_services |
| GET | `/identity` | identity.py | list_identity | list[DigitalIdentityStatusResponse] | get_digital_identity_statuses |
| GET | `/retail` | retail.py | list_retail | list[RetailEventResponse] | get_retail_events |
| POST | `/predict` | prediction.py | post_predict | PredictResponse | get_flight_by_id, get_flight_updates_for_flight, inference.predict, create_prediction_audit, update_flight_prediction |
| GET | `/predictions` | prediction.py | get_predictions | list[PredictionAuditRead] | list_predictions |
| GET | `/predictions/flights/{flight_id}` | prediction.py | get_predictions_for_flight_route | list[PredictionAuditRead] | get_predictions_for_flight |

All route handlers that need a DB session use `Depends(get_db)` and receive a `Session`; they call CRUD or services and return Pydantic response models.

---

## 3. Database Schema

**Engine:** SQLite, single file `airport_data_hub/airport_hub.db` (or path from `AIRPORT_HUB_DB`). Connection uses `check_same_thread=False` and `timeout=15` for concurrent access (e.g. synthetic thread + request handlers).

| Table | Purpose | Important columns | Relationships |
|-------|---------|-------------------|---------------|
| **flights** | Core flight record: schedule, status, gate, plus reconciled and prediction fields | id, flight_code, airline, origin, destination, scheduled_time, estimated_time, status, gate, runway_id; reconciled_eta, reconciled_status, reconciled_gate, reconciliation_reason, reconciliation_confidence, last_reconciled_at; predicted_eta, predicted_arrival_delay_min, prediction_confidence, prediction_model_version, last_prediction_at | runway_id → runways.id; referenced by flight_updates.flight_id, passenger_flow.flight_id |
| **flight_updates** | Raw reports per source (airline, radar, etc.) per flight | id, flight_id, source_name, reported_eta, reported_status, reported_gate, reported_at, confidence_score | flight_id → flights.id |
| **passenger_flow** | Queue/check-in/boarding counts per flight | id, flight_id, check_in_count, security_queue_count, boarding_count, predicted_queue_time, terminal_zone, timestamp | flight_id → flights.id |
| **runways** | Runway state and hazards | id, runway_code, status, surface_condition, contamination_level, grip_score, hazard_detected, hazard_type, last_inspection_time | Referenced by flights.runway_id |
| **resources** | Gates, stands, desks, vehicles, staff slots | id, resource_name, resource_type, status, assigned_to, location | — |
| **alerts** | Operational alerts created by rules | id, alert_type, severity, source_module, message, related_entity_type, related_entity_id, created_at, resolved, uniqueness_key | Logical link to entity via related_entity_type/id (no FK) |
| **infrastructure_assets** | Jet bridges, belts, cameras, sensors; tamper/health | id, asset_name, asset_type, status, network_health, tamper_detected, location, last_updated | — |
| **passenger_services** | Assistance, lounge, transfer, info requests | id, passenger_reference, service_type, status, request_time, completion_time, location | — |
| **digital_identity_status** | Verification status per passenger ref | id, passenger_reference, verification_status, verification_method, last_verified_at, token_reference | — |
| **retail_events** | Retail orders/offers | id, passenger_reference, offer_type, order_status, pickup_gate, created_at | — |
| **prediction_audit** | One row per prediction call; full traceability | id, flight_id, prediction_timestamp, model_version, predicted_arrival_delay_min, predicted_arrival_time, confidence_score, reason_codes, features_snapshot, created_at; prediction_outcome, input_quality_score, missing_features, stale_data_warnings, operational_reason_codes | flight_id logical (no FK) |

**Migrations (in `init_db`):** Add prediction columns to `flights` if missing; add prediction_audit columns; add/backfill `uniqueness_key` on `alerts`; add `reconciled_eta` (and related) on `flights`; one-time queue alert message update (flight_id → flight code in message text).

---

## 4. Business Logic Modules (services/)

### 4.1 Intelligence (`services/intelligence.py`)

- **Trigger:** Called at the start of GET `/overview` and GET `/aodb/overview` (before reconciliation and overview build).
- **Reads:** Passenger flows, runways, infrastructure assets, flights (and flights by gate) via CRUD.
- **Writes:** Inserts new rows into `alerts` via `create_alert` when rules fire; no updates to other tables.

**Rules:**

1. **Queue** (`run_queue_alerts`): For each passenger_flow with `security_queue_count >= SECURITY_QUEUE_THRESHOLD` (80), creates one alert with `uniqueness_key = "queue:passenger_flow:{pf.id}"`, message includes count, zone, and flight code (from flight_id lookup).
2. **Runway hazard** (`run_runway_hazard_alerts`): For each runway with `hazard_detected`, creates alert with key `runway_hazard:runway:{id}`. If `grip_score < GRIP_SCORE_LOW_THRESHOLD` (0.4), creates separate alert with key `grip:runway:{id}`.
3. **Tamper** (`run_tamper_alerts`): For each infrastructure asset with `tamper_detected`, creates alert with key `security:infrastructure:{id}`.
4. **Gate conflict** (`run_gate_conflict_alerts`): For each gate with at least two flights, checks time overlap (using estimated_time or scheduled + 90 min); if overlap, creates alert with key `gate_conflict:flight:{a.id}_{b.id}`.

`create_alert` in CRUD enforces deduplication (see Alert system below).

### 4.2 Reconciliation (`services/reconciliation.py`)

- **Trigger:** Called after intelligence in GET `/overview` and GET `/aodb/overview`.
- **Reads:** All flights (limit 500), and for each flight its `FlightUpdate` rows via `get_flight_updates_for_flight`.
- **Writes:** Only `flights`: `reconciled_eta`, `reconciled_status`, `reconciled_gate`, `reconciliation_reason`, `reconciliation_confidence`, `last_reconciled_at` via `update_flight_reconciliation`. Raw `Flight` and `FlightUpdate` rows are not modified.

**Logic:** For each flight, latest update by `reported_at` is used. ETA: prefer latest `reported_eta`, else `predicted_eta`, else `estimated_time`, else `scheduled_time`; reason and confidence set accordingly. Status: latest `reported_status` or `flight.status`. Gate: latest `reported_gate` or `flight.gate`. One combined reason string and a single confidence value (capped).

### 4.3 Overview builder (`services/overview.py`)

- **Trigger:** Called at the end of GET `/overview` and GET `/aodb/overview` (after intelligence and reconciliation).
- **Reads:** Flights, passenger_flows, runways, alerts (resolved=False), resources, infrastructure_assets, passenger_services, digital_identity_statuses, retail_events via CRUD.
- **Writes:** None. Builds an in-memory `OverviewResponse`.

**Behaviour:** Maps each entity list to Pydantic response types (e.g. `_to_flight_response`, `_to_alert_response` with `get_suggested_action(alert_type)` for suggested_action). Identity list is aggregated to counts by verification_status. Returns one snapshot object containing all current_flights, passenger_queues, runway_conditions, active_alerts, resource_status, infrastructure_status, service_requests, identity_verification_counts, retail_activity.

### 4.4 Synthetic generator (`services/synthetic.py`)

- **Trigger:** Started once in app lifespan (`start_synthetic_feeder`); runs in a daemon background thread until shutdown (`stop_synthetic_feeder`).
- **Reads:** Flights (in a time window), passenger_flow, runways, infrastructure_assets.
- **Writes:** Inserts new `PassengerFlow` rows; updates existing passenger_flow rows (counts, timestamp); updates runways (grip_score, hazard_detected, hazard_type, last_inspection_time); updates infrastructure_assets (network_health, tamper_detected, status, last_updated). Optionally updates some flights’ status/gate and inserts `FlightUpdate` rows with `source_name="synthetic_generator"`.

**Loop:** Every ~1.5 seconds, opens a new session, runs `_tick_once` (randomized changes), commits, closes session. No coordination with request handlers except via shared DB and connection timeout.

---

## 5. Prediction System (`prediction/`)

- **Features (`features.py`):**  
  `build_features(flight, flight_updates, prediction_time)` builds a feature dict from flight + sorted updates: scheduled_departure/arrival, origin, destination, airline, hours_until_scheduled_departure, reported_eta/status/gate (latest), delay_at_origin_min, hour_of_day, day_of_week. Also returns metadata: `missing_features`, `input_quality_score` (1.0 minus deductions for missing/stale), `stale_data_warnings`, `latest_update_at`. `feature_vector_for_model` turns that dict into an ordered numeric vector for the model using `get_feature_names()`.

- **Model load (`inference.py`):**  
  `load_model(path)` is called at app startup (lifespan). Tries to load `delay_model.joblib` from `airport_data_hub/models/`. If file missing or load fails, `_model_obj` stays `None` and only stub prediction is used. Feature names are taken from the model dict or default list.

- **Inference (`inference.py`):**  
  `predict(flight, flight_updates, prediction_time)` calls `build_features`, then:
  - If `input_quality_score < MIN_INPUT_QUALITY_FOR_ML` (0.3): returns outcome `insufficient_data`, no model/fallback delay, safe default (e.g. 0 delay, confidence 0).
  - Else: encodes features for vector, builds vector. If `_model_obj` is set, runs `model.predict`, clamps delay to [-60, 300] min, builds reason_codes from feature_importances_ or coef_; otherwise calls `_stub_predict` (origin delay * 0.9, confidence 0.5). Maps reason_codes to `operational_reason_codes` via `operational_codes.to_operational`. Computes `predicted_arrival_time` from scheduled_arrival + delay. Returns dict with predicted_arrival_delay_min, predicted_arrival_time, confidence_score, prediction_outcome (ml_model | rules_fallback | insufficient_data), fallback_used, input_quality_score, missing_features, stale_data_warnings, reason_codes, operational_reason_codes, features_used, model_version, prediction_timestamp.

- **Storage:**  
  The prediction route calls `create_prediction_audit` (insert into `prediction_audit`) and `update_flight_prediction` (update `flights`: predicted_eta, predicted_arrival_delay_min, prediction_confidence, prediction_model_version, last_prediction_at). Every prediction is audited; flight row is updated with latest prediction.

- **Fallback when model missing:**  
  If the model file is absent or load fails, `_model_obj` is None and `predict` always uses `_stub_predict` (rules-based delay from origin delay and time-to-departure), with outcome `rules_fallback` and `fallback_used=True`.

---

## 6. Data Flow

### A) GET `/overview`

1. Route: `routes/overview.py` → `overview(db)`.
2. `run_all_intelligence(db)` (services/intelligence.py): runs queue, runway_hazard, tamper, gate_conflict rules; each may call `create_alert` (CRUD), which deduplicates and optionally inserts into `alerts`.
3. `run_flight_reconciliation(db)` (services/reconciliation.py): for each flight, reads flight + flight_updates, computes reconciled_eta/status/gate and reason/confidence, calls `update_flight_reconciliation` (CRUD) to update `flights`.
4. `get_overview(db)` (services/overview.py): reads flights, passenger_flows, runways, alerts (resolved=False), resources, infrastructure_assets, passenger_services, digital_identity_statuses, retail_events via CRUD; maps each to response DTOs (with suggested_action for alerts); builds and returns `OverviewResponse`.

### B) GET `/aodb/overview`

Same as GET `/overview`: route in `aodb.py` calls `run_all_intelligence(db)`, `run_flight_reconciliation(db)`, then `get_overview(db)` and returns the same `OverviewResponse`. Only the URL prefix differs.

### C) POST `/predict`

1. Route: `routes/prediction.py` → `post_predict(payload, db)`.
2. Load flight: `get_flight_by_id(db, payload.flight_id)`; 404 if missing.
3. Load updates: `get_flight_updates_for_flight(db, payload.flight_id)`.
4. Convert to dicts: `_flight_to_dict(flight)`, `_flight_update_to_dict(u)` for each update.
5. Inference: `inference.predict(flight_dict, updates_list)` → features, then ML or stub, then result dict.
6. Persist: `create_prediction_audit(db, ...)` with full result (including outcome, quality, missing_features, operational_reason_codes as JSON); `update_flight_prediction(db, flight_id, FlightPredictionUpdate(...))`.
7. Return: Build `PredictResponse` from result dict and return.

---

## 7. Alert System

- **Where generated:** In `services/intelligence.py`, by the four rule functions (queue, runway_hazard, tamper, gate_conflict), each calling `crud.create_alert(...)` with a stable `uniqueness_key`.

- **Rules:** See section 4.1 (queue threshold 80, grip threshold 0.4, hazard/tamper/gate overlap).

- **Deduplication:** In `crud.create_alert`: (1) If `uniqueness_key` is set, look up an unresolved alert with that key (`get_unresolved_alert_by_uniqueness_key`). If found, return None (no insert). (2) Else look up by `(alert_type, related_entity_type, related_entity_id)` (`get_unresolved_alert_by_entity`). If found, return None. Only if both checks pass is a new `Alert` row inserted.

- **uniqueness_key:** Stored on `Alert`; format used in intelligence is `"{alert_type}:{related_entity_type}:{related_entity_id}"` (e.g. `queue:passenger_flow:19`, `gate_conflict:flight:3_7`). Legacy rows with null key are backfilled in `_backfill_alerts_uniqueness_key` in database.py. New alerts always pass the key; the entity fallback still prevents duplicates when key was missing.

- **Resolution:** Alerts are resolved only by operator action: PATCH `/alerts/{id}/resolve` (body optional, default `resolved: true`) calls `update_alert_resolve`, which sets `Alert.resolved`. Resolving does not change underlying data (e.g. queue or runway); the same condition can produce a new alert on a later `/overview` once the previous one is resolved.

- **Suggested actions:** In schemas, `ALERT_SUGGESTED_ACTIONS` maps alert_type to operator-facing text; `AlertResponse` includes `suggested_action` (set by validator from `get_suggested_action(alert_type)`). The system suggests only; it does not execute actions.

---

## 8. Reconciliation System

- **Computed values:** For each flight, one reconciled ETA, one reconciled status, one reconciled gate, plus a single reason string and a single confidence score. Source priority: latest `FlightUpdate` (by `reported_at`) for ETA/status/gate, then flight’s predicted_eta, estimated_time, scheduled_time for ETA; then flight’s status and gate.

- **Data sources:** `Flight` (scheduled_time, estimated_time, status, gate, predicted_eta, prediction_confidence) and `FlightUpdate` (reported_eta, reported_status, reported_gate, reported_at, confidence_score).

- **Confidence:** ETA: 0.9 if from latest reported, 0.7 from prediction, 0.6 from canonical estimated, 0.5 from schedule. Final stored confidence is min(eta_confidence, 0.9) rounded.

- **Fields updated on flights:** `reconciled_eta`, `reconciled_status`, `reconciled_gate`, `reconciliation_reason`, `reconciliation_confidence`, `last_reconciled_at`. Raw columns and `FlightUpdate` rows are unchanged.

---

## 9. Stored Data vs Derived Data

- **Raw / source data:**  
  `flights`: flight_code, airline, origin, destination, scheduled_time, estimated_time, status, gate, stand, runway_id.  
  `flight_updates`: all columns (reported_eta, reported_status, reported_gate, reported_at, source_name, confidence_score).  
  `passenger_flow`, `runways`, `resources`, `infrastructure_assets`, `passenger_services`, `digital_identity_status`, `retail_events`: all stored as entered or seeded/synthetic.

- **System-generated (rules):**  
  `alerts`: every column is written by the system when rules fire (message, severity, uniqueness_key, etc.).

- **AI prediction data:**  
  `flights`: predicted_eta, predicted_arrival_delay_min, prediction_confidence, prediction_model_version, last_prediction_at (written by prediction route).  
  `prediction_audit`: full prediction result (outcome, quality, reason_codes, operational_reason_codes, etc.) per request.

- **Reconciliation outputs:**  
  `flights`: reconciled_eta, reconciled_status, reconciled_gate, reconciliation_reason, reconciliation_confidence, last_reconciled_at. Computed on each `/overview` and `/aodb/overview` and written by reconciliation service.

---

## 10. System Capabilities

- Expose flights (list, by id, updates, status, prediction write-back) and AODB-style flight list and overview.
- Ingest raw flight updates (POST flight-updates) and store them without overwriting.
- Run rules-based intelligence to create alerts (queue, runway hazard, low grip, tamper, gate conflict) with deduplication.
- Reconcile flight ETA/status/gate from updates and prediction into a single view per flight.
- Build and return a unified operations overview (flights, queues, runways, alerts, resources, infrastructure, services, identity counts, retail).
- Run arrival delay prediction (POST /predict) with ML or stub, audit every prediction, and update flight prediction fields.
- Expose prediction history (list and by flight).
- Resolve or reopen alerts via PATCH (operator-driven).
- CRUD for runways, resources, infrastructure, passenger flow, passenger services, identity, retail (as implemented in routes).
- Seed demo data when DB is empty (on startup).
- Run a background synthetic data generator to mutate passenger flows, runways, and infrastructure (and optionally flights/updates) for live demos.

---

## 11. System Limitations

- No authentication or authorization on any endpoint.
- No real-time data ingestion from external systems (AODB, sensors); data comes from seed, synthetic generator, and manual API calls.
- No event streaming or WebSockets; clients poll (e.g. overview, alerts).
- Single SQLite DB and file-based storage; no replication, no connection pooling beyond the process.
- Prediction model is optional (stub used if file missing); no automatic model training or deployment pipeline from this repo.
- Alerts are suggestions only; no automated remediation or workflows.
- Reconciliation runs only when `/overview` or `/aodb/overview` is called; not a continuous background job.
- No versioned API or long-term schema migrations (Alembic); only in-process migrations in `init_db`.
- No rate limiting, request validation beyond Pydantic, or audit logging of who changed what.

---

## 12. Architecture Summary

```
                    Client (e.g. browser / UI)
                              │
                              ▼
                    FastAPI (main.py)
                    CORS, lifespan
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    Routes (HTTP)      Prediction route      Root /
    /overview,           POST /predict       GET /
    /aodb/overview,      GET /predictions
    /flights, /alerts,
    /runways, ...
         │                    │
         ▼                    ▼
    Services             prediction.inference
    intelligence             (features + model
    reconciliation           or stub)
    overview                 │
    (synthetic in             │
     background)              │
         │                    │
         └──────────┬─────────┘
                    ▼
              CRUD (crud.py)
              get_*, create_*,
              update_*
                    │
                    ▼
              SQLite (database.py)
              engine, SessionLocal
              airport_hub.db
```

**Prediction engine:** Loaded at startup (inference.load_model). Used only by the prediction route: route gets flight + updates from CRUD, calls inference.predict (which uses features + optional ML model or stub), then CRUD writes prediction_audit and updates flight prediction fields. It does not run on overview or in the background.

---

## 13. Plain-Language Explanation

The **Airport Data Hub** is a single FastAPI backend that acts as the central data store and “brain” for an airport operations dashboard. It uses one SQLite database and exposes REST APIs for flights, alerts, runways, resources, passenger flow, and more.

When the dashboard asks for the **overview** (GET `/overview` or `/aodb/overview`), the server first runs **intelligence rules**: it looks at passenger queues, runways, infrastructure, and flight–gate assignments and creates **alerts** (e.g. “queue too long”, “runway hazard”, “gate conflict”) if thresholds are exceeded. It avoids duplicate alerts for the same situation using a **uniqueness_key**. Then it runs **reconciliation**: for every flight it takes the latest external updates and the current prediction and decides one “best” ETA, status, and gate, and writes those into the flight row as **reconciled_***. Finally it **builds the overview**: it reads all the main tables (flights, queues, runways, alerts, resources, etc.), turns them into JSON-friendly shapes (with suggested actions for alerts), and returns one big snapshot. So one overview request both updates alerts and reconciled flight state and then returns the current picture.

**Flights** and **flight updates** are stored separately: the core schedule and status live in `flights`, and each report from an airline or radar is a row in `flight_updates`. Reconciliation and prediction only *write* to the flight row (reconciled_* and predicted_*); they don’t delete or overwrite the raw updates.

**Predictions** are triggered by POST `/predict` with a flight id. The server loads that flight and its updates, builds **features** (times, delays, airline, origin, etc.), and either runs a trained **model** (if the file exists) or a **stub** that estimates delay from origin delay. The result is saved in **prediction_audit** (full trace) and the **flight** row is updated with the latest predicted delay and ETA. So the “AI” is only used when someone (or the UI) calls the predict endpoint; it doesn’t run automatically on every overview.

A **background synthetic generator** runs in a separate thread and periodically inserts or updates passenger flows, runways, and infrastructure (and optionally flight status/gate) so the demo always has changing numbers. It shares the same DB and connection settings; no separate services.

Everything that touches the database goes through **CRUD**: routes and services never use raw SQL or the session directly for reads/writes. That keeps a single place for how each entity is read or updated. The **prediction** logic lives in its own folder (features, inference, config) and is invoked only by the prediction route; the rest of the app just uses CRUD and the three services (intelligence, reconciliation, overview) to keep the hub consistent and to serve the overview and entity APIs.
