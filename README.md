Airport Data Hub – How It Works (Teaching Guide)
1. Architecture overview
Main components
* FastAPI app (airport_data_hub/main.py): single app, one process. It creates the app, adds CORS, and mounts all routers. On startup (lifespan) it calls init_db() and inference.load_model(...).
* Database (database.py): one SQLite DB (airport_hub.db). engine, SessionLocal, Base. get_db() is the FastAPI dependency that gives each request a session and closes it after the request. init_db() creates tables and runs small migrations/backfills (prediction columns, prediction_audit columns, alerts uniqueness_key, flights reconciled_eta).
* Models (models.py): SQLAlchemy ORM for all tables (Flight, FlightUpdate, PassengerFlow, Runway, Resource, Alert, InfrastructureAsset, PassengerService, DigitalIdentityStatus, RetailEvent, PredictionAudit).
* CRUD (crud.py): all reads/writes go through here. No route or service talks to the DB directly; they call crud functions.
* Routes (routes/*.py): HTTP entrypoints. Each file is a router (e.g. flights, alerts, overview, aodb, prediction). Routes use Depends(get_db), call crud and/or services, and return Pydantic responses.
* Services (services/): business logic that uses crud and sometimes the DB session:
* intelligence.py: rules that create alerts (queue, runway, grip, tamper, gate conflict).
* overview.py: builds the single “overview” snapshot (flights, queues, runways, alerts, resources, etc.) by calling crud and mapping to response schemas.
* reconciliation.py: computes reconciled ETA/status/gate per flight and updates Flight via crud.
* Prediction (prediction/): feature building (features.py), model load + inference (inference.py), config (config.py), operational reason codes (operational_codes.py). No HTTP; called from routes/prediction.py.
Data flow (high level)
* Client → FastAPI route → (optional) service layer → crud → SQLite → same path back.
* For /overview and /aodb/overview: route → intelligence (alerts) → reconciliation (flights) → overview builder (read via crud) → response.
* For POST /predict: route → crud (read flight + updates) → prediction (features + inference) → crud (audit + update flight) → response.
How a request moves
1. FastAPI matches the path to a router (e.g. routes/overview.py).
2. Dependencies run (e.g. get_db() opens a session).
3. The route handler runs (often calling a service and/or crud).
4. The handler returns a Pydantic model → FastAPI serializes to JSON.
5. After the response, get_db()’s finally closes the session.

2. Execution flow for three endpoints
GET /overview
1. Route: routes/overview.py → overview(db).
2. run_all_intelligence(db) (services/intelligence.py):
* run_queue_alerts(db) → crud: get_passenger_flows, then for each flow over threshold, create_alert(..., uniqueness_key=...) (crud deduplicates by key and by entity).
* run_runway_hazard_alerts(db) → crud: get_runways, then create_alert for hazard and for low grip (with keys).
* run_tamper_alerts(db) → crud: get_infrastructure_assets, then create_alert for tamper (with key).
* run_gate_conflict_alerts(db) → crud: get_flights, get_flights_by_gate, then for each overlapping pair create_alert (with key).
1. run_flight_reconciliation(db) (services/reconciliation.py):
* crud: get_flights; for each flight, get_flight_updates_for_flight(db, flight.id).
* For each flight, compute reconciled_eta, reconciled_status, reconciled_gate, reason, confidence; then crud: update_flight_reconciliation(...).
1. get_overview(db) (services/overview.py):
* crud: get_flights, get_passenger_flows, get_runways, get_alerts(resolved=False), get_resources, get_infrastructure_assets, get_passenger_services, get_digital_identity_statuses, get_retail_events.
* Map each to response schemas (_to_flight_response, _to_alert_response, etc.), build OverviewResponse.
1. Return OverviewResponse to the client.
GET /aodb/overview
Same as GET /overview: routes/aodb.py → aodb_overview(db) runs run_all_intelligence(db), then run_flight_reconciliation(db), then get_overview(db), and returns the same OverviewResponse. So /overview and /aodb/overview are the same pipeline with different URL prefixes.
POST /predict
1. Route: routes/prediction.py → post_predict(payload: PredictRequest, db).
2. Load flight and updates:
get_flight_by_id(db, payload.flight_id) → 404 if missing.
get_flight_updates_for_flight(db, payload.flight_id).
1. To dicts: _flight_to_dict(flight), [_flight_update_to_dict(u) for u in updates].
2. Inference: inference.predict(flight_dict, updates_list) (prediction/inference.py):
* feat.build_features(flight_dict, updates_list) → (features, meta) (missing features, quality score, staleness).
* If meta["input_quality_score"] < MIN_INPUT_QUALITY_FOR_ML → return “insufficient_data” result (no model/fallback).
* Else: encode features, build vector, run loaded model (or _stub_predict), compute delay, predicted time, reason codes; map to operational phrases; return full dict.
1. Persist:
create_prediction_audit(db, ...) with all result fields (including outcome, quality, missing_features, operational_reason_codes as JSON).
update_flight_prediction(db, flight_id, FlightPredictionUpdate(predicted_eta, delay_min, confidence, model_version)).
1. Response: Build PredictResponse from the inference result and return it.

3. Where the “AI” actually is
* Files: airport_data_hub/prediction/ (and the route that calls it).
* inference.py: model load, prediction, fallback, outcome type, reason codes.
* features.py: turn flight + updates into a feature dict and quality/staleness meta.
* config.py: model path, version, thresholds (e.g. MIN_INPUT_QUALITY_FOR_ML, MAX_UPDATE_AGE_HOURS).
* operational_codes.py: map ML factor names to airport-ops phrases.
* Functions:
* inference.load_model(path): called once at app startup from main.py lifespan. Tries to load airport_data_hub/models/delay_model.joblib (or the path passed). Sets global _model_obj and _feature_names; if file missing or load fails, keeps _model_obj = None (stub only).
* inference.predict(flight, flight_updates, prediction_time): builds features (via features.build_features), decides insufficient_data vs model vs stub, runs model or _stub_predict, returns dict with delay, confidence, reason codes, operational phrases, outcome, quality, etc.
* features.build_features(flight, flight_updates, prediction_time): returns (features, meta). Features: schedule, origin/destination/airline, hours_until_departure, latest reported ETA/status/gate, delay_at_origin, hour_of_day, day_of_week. Meta: missing_features, input_quality_score, stale_data_warnings, latest_update_at.
* How the model is loaded: In main.py lifespan, inference.load_model(Path(__file__).parent / "models" / "delay_model.joblib") runs. So the process has one in-memory model (or none for stub).
* How predictions are written: In routes/prediction.py, after inference.predict(...), the route calls create_prediction_audit(db, ...) (insert into prediction_audit) and update_flight_prediction(db, ...) (update flights columns: predicted_eta, predicted_arrival_delay_min, prediction_confidence, prediction_model_version, last_prediction_at).

4. Main folders / files
* airport_data_hub/models.py
SQLAlchemy model classes for every table. Defines columns and table names; no logic. Used by database.py (Base.metadata.create_all) and by crud when querying. Defines Flight (with raw + reconciled + prediction columns), FlightUpdate, PassengerFlow, Runway, Resource, Alert (with uniqueness_key), InfrastructureAsset, PassengerService, DigitalIdentityStatus, RetailEvent, PredictionAudit.
* airport_data_hub/crud.py
Single place for DB access. Functions like get_flights, get_flight_by_id, create_alert, get_unresolved_alert_by_uniqueness_key, get_unresolved_alert_by_entity, create_prediction_audit, update_flight_prediction, update_flight_reconciliation, etc. Routes and services call these; they don’t use the Session for raw SQL/ORM elsewhere.
* airport_data_hub/routes/
One module per domain: flights, flight_updates, runways, resources, alerts, infrastructure, passenger_flow, services, identity, retail, overview, aodb, prediction. Each defines a router and endpoints (GET/POST/PATCH). They use Depends(get_db), call crud and/or services, and return schema models.
* airport_data_hub/services/
Business logic that uses crud (and the same DB session):
* intelligence.py: rule functions that create alerts (queue, runway hazard, grip, tamper, gate conflict) with a stable uniqueness_key; they call create_alert which deduplicates.
* overview.py: get_overview(db) gathers all entity lists via crud and assembles OverviewResponse.
* reconciliation.py: run_flight_reconciliation(db) computes reconciled ETA/status/gate per flight and calls update_flight_reconciliation.
* airport_data_hub/prediction/
Arrival delay “AI”: config.py (paths, thresholds), features.py (build_features, feature_vector_for_model), inference.py (load_model, predict, stub, operational codes), operational_codes.py (ML factor → ops phrase). Used only by routes/prediction.py; no HTTP inside prediction.

5. Data flow: Flight → FlightUpdate → Prediction → Reconciliation → Overview
* Flight: Core record in flights: schedule, status, gate, estimated_time (raw/canonical). Plus reconciled_eta, reconciled_status, reconciled_gate, reconciliation_* and prediction_* fields written by reconciliation and prediction.
* FlightUpdate: Raw reports per source (airline, radar, etc.): reported_eta, reported_status, reported_gate, reported_at. Stored in flight_updates; never overwritten by prediction or reconciliation.
* Prediction: On POST /predict, the route reads Flight + FlightUpdates, runs features + inference, then: (1) inserts into prediction_audit, (2) updates Flight’s predicted_eta, predicted_arrival_delay_min, prediction_confidence, prediction_model_version, last_prediction_at. So prediction writes both audit and flight.
* Reconciliation: On GET /overview (and GET /aodb/overview), after intelligence, run_flight_reconciliation runs. For each flight it reads Flight and its FlightUpdates, picks “best” ETA (reported_eta → predicted_eta → estimated_time → scheduled_time), status (reported_status or status), gate (reported_gate or gate), and writes Flight.reconciled_eta, reconciled_status, reconciled_gate, reconciliation_reason, reconciliation_confidence, last_reconciled_at. Raw fields and FlightUpdates are unchanged.
* Overview response: get_overview reads flights (and everything else) via crud. Each flight is mapped to FlightResponse, which includes both raw and reconciled/prediction fields. So the client sees one flight object with schedule, status, gate, predicted_eta, reconciled_eta, reconciliation_, etc.
So: Flight and FlightUpdate are the source of truth; prediction adds predicted_* and audit rows; reconciliation overwrites only reconciled_* and reason/confidence/timestamp; overview just reads and returns that combined view.

6. Alert system
* Where rules live: services/intelligence.py. Functions: run_queue_alerts, run_runway_hazard_alerts, run_tamper_alerts, run_gate_conflict_alerts. Each uses thresholds (e.g. SECURITY_QUEUE_THRESHOLD, GRIP_SCORE_LOW_THRESHOLD), fetches data via crud, and calls create_alert(..., uniqueness_key=...). run_all_intelligence(db) runs all four.
* Deduplication: In crud.create_alert: (1) If uniqueness_key is set, look up an unresolved alert with that key (get_unresolved_alert_by_uniqueness_key). (2) If not found, look up by (alert_type, related_entity_type, related_entity_id) (get_unresolved_alert_by_entity). If either finds a row, create_alert returns None and no row is inserted. So at most one unresolved alert per logical condition.
* uniqueness_key: Stored on Alert. Format used in intelligence: "{alert_type}:{related_entity_type}:{related_entity_id}", e.g. queue:passenger_flow:5, gate_conflict:flight:3_7. Legacy rows with null key are backfilled in _backfill_alerts_uniqueness_key() in database.py (same format). New alerts get the key; the fallback check by (type, entity_type, entity_id) catches duplicates even when a legacy row exists without a key.

7. Reconciliation system
* Where: services/reconciliation.py → run_flight_reconciliation(db).
* Input: For each flight, crud gives the Flight row and its FlightUpdates (via get_flights, get_flight_updates_for_flight).
* Logic: For each flight, take the latest update by reported_at. Then:
* ETA: use latest reported_eta if present (with confidence from update), else flight.predicted_eta, else flight.estimated_time, else flight.scheduled_time; store in reconciled_eta; reason e.g. "latest_reported" / "prediction" / "schedule".
* Status: latest reported_status or flight.status → reconciled_status.
* Gate: latest reported_gate or flight.gate → reconciled_gate.
* One combined reconciliation_reason string (e.g. "eta=... status=... gate=..."), one reconciliation_confidence, and last_reconciled_at = now.
* Storage: Only Flight is updated, via crud update_flight_reconciliation(flight_id, reconciled_eta=..., reconciled_status=..., reconciled_gate=..., reconciliation_reason=..., reconciliation_confidence=...). Raw fields and FlightUpdate rows are not modified.

8. Prediction lifecycle (end to end)
1. Feature extraction: Route gets Flight + FlightUpdates from crud, converts to dicts. features.build_features(flight_dict, updates_list) returns (features, meta). Features include schedule, origin/destination/airline, hours_until_scheduled_departure, delay_at_origin_min, hour_of_day, day_of_week, latest reported ETA/status/gate; meta includes missing_features, input_quality_score, stale_data_warnings.
2. Model inference: inference.predict(flight_dict, updates_list) uses those features. If quality too low → insufficient_data response. Else encodes features, builds a numeric vector, runs the loaded model (or _stub_predict), clamps delay, gets reason codes (and maps to operational phrases), returns a single dict (delay, predicted_arrival_time, confidence, outcome, reason_codes, operational_reason_codes, features_used, etc.).
3. Response: Route builds PredictResponse from that dict and returns it to the client.
4. Audit: Route calls create_prediction_audit(db, ...) with all relevant fields (including JSON for reason_codes, features_snapshot, missing_features, stale_data_warnings, operational_reason_codes). One row per prediction in prediction_audit.
5. Flight update: Route calls update_flight_prediction(db, flight_id, FlightPredictionUpdate(predicted_eta, predicted_arrival_delay_min, prediction_confidence, prediction_model_version)). So the same request that returns the prediction also writes the audit and updates the flight.

9. Database tables (purpose in simple terms)
* flights: One row per flight. Schedule, status, gate, estimated_time (raw). Plus reconciled_eta/status/gate and reconciliation_* (from reconciliation), and predicted_eta, predicted_arrival_delay_min, prediction_* (from POST /predict).
* flight_updates: Raw reports per source per flight (reported_eta, reported_status, reported_gate, reported_at). Never overwritten; used for features and reconciliation.
* passenger_flow: Queue/check-in/boarding counts per flight (and terminal, timestamp). Used by intelligence for queue alerts and by overview.
* runways: Runway state (grip, hazard). Used by intelligence for runway/grip alerts and by overview.
* resources: Gates, stands, etc. Shown in overview.
* alerts: One row per alert (type, message, severity, related_entity_type/id, resolved, uniqueness_key). Created by intelligence; deduplicated by key and by (type, entity_type, entity_id).
* infrastructure_assets: Assets and tamper flag. Used by intelligence for tamper alerts and by overview.
* passenger_services, digital_identity_status, retail_events: Domain data; overview reads them for the snapshot.
* prediction_audit: One row per POST /predict: flight_id, timestamp, model version, predicted delay/time, confidence, reason_codes and operational_reason_codes (JSON), features_snapshot, outcome, input_quality_score, missing_features, stale_data_warnings. Full traceability.

10. Simple flow diagram (text)
Client
  │
  ├─ GET /overview (or GET /aodb/overview)
  │     → routes/overview.py (or aodb.py)
  │     → services/intelligence.run_all_intelligence(db)  → crud (get_* + create_alert)
  │     → services/reconciliation.run_flight_reconciliation(db)  → crud (get_flights, get_flight_updates_for_flight, update_flight_reconciliation)
  │     → services/overview.get_overview(db)  → crud (get_flights, get_passenger_flows, get_runways, get_alerts, …)
  │     → OverviewResponse
  │
  ├─ POST /predict  body: { "flight_id": N }
  │     → routes/prediction.post_predict
  │     → crud: get_flight_by_id, get_flight_updates_for_flight
  │     → prediction/inference.predict(flight_dict, updates_list)
  │         → prediction/features.build_features  → (features, meta)
  │         → model or stub  → delay, confidence, reason codes, operational phrases
  │     → crud: create_prediction_audit, update_flight_prediction
  │     → PredictResponse
  │
  └─ GET /flights, GET /alerts, PATCH /alerts/{id}/resolve, etc.
        → routes/*  → crud  → DB  → schema response



DB (SQLite)
  ↑↓
crud (get_*, create_*, update_*)
  ↑
services (intelligence, overview, reconciliation)   and   routes/prediction → prediction (features, inference)
  ↑
routes (overview, aodb, prediction, flights, alerts, …)
  ↑
FastAPI app (main.py)  ← lifespan: init_db(), inference.load_model()
  ↑
Client (HTTP)


11. Plain-language summary (for a junior dev)
This app is a single backend for “airport operations data”: flights, queues, runways, resources, alerts, and a bit of passenger/retail/identity data. Everything is stored in one SQLite database.
When you call GET /overview (or GET /aodb/overview), the server (1) runs intelligence rules that create alerts (e.g. “queue too long”, “runway hazard”, “gate conflict”) but only if an equivalent alert doesn’t already exist (dedup by a key and by entity). (2) Reconciles each flight: it picks one “best” ETA, status, and gate from many possible sources (latest report, prediction, or schedule) and saves those in the flight row. (3) Reads all the main entities and returns one big JSON snapshot (current_flights, active_alerts, runway_conditions, etc.). So one request both “fixes” alerts and reconciled flight state and then returns that state.
When you call POST /predict with a flight id, the server loads that flight and its flight updates (raw ETA/status/gate reports), turns them into features (schedule, delay at origin, time of day, etc.). It then runs either a trained model (if the file exists at startup) or a simple rule (“stub”) to predict arrival delay. It saves that prediction in two places: an audit table (every prediction for traceability) and the flight row (predicted_eta, delay minutes, confidence). So the “AI” is: feature building + one model (or stub) call; the rest is just reading/writing through crud.
Flights keep both raw data (status, gate, estimated_time) and reconciled values (reconciled_eta, reconciled_status, reconciled_gate) and prediction values (predicted_eta, predicted_arrival_delay_min, etc.). Flight updates are never changed; they’re the raw feed. Reconciliation runs on overview and overwrites only the reconciled_* fields. Prediction runs only when you call POST /predict and overwrites only the prediction_* fields. So: one backend, one DB, one FastAPI app; routes call services and crud; the only “AI” is in the prediction package (features + inference), and the rest is rules and data plumbing.














































Client
  │
  ├─ GET /overview (or GET /aodb/overview)
  │     → routes/overview.py (or aodb.py)
  │     → services/intelligence.run_all_intelligence(db)  → crud (get_* + create_alert)
  │     → services/reconciliation.run_flight_reconciliation(db)  → crud (get_flights, get_flight_updates_for_flight, update_flight_reconciliation)
  │     → services/overview.get_overview(db)  → crud (get_flights, get_passenger_flows, get_runways, get_alerts, …)
  │     → OverviewResponse
  │
  ├─ POST /predict  body: { "flight_id": N }
  │     → routes/prediction.post_predict
  │     → crud: get_flight_by_id, get_flight_updates_for_flight
  │     → prediction/inference.predict(flight_dict, updates_list)
  │         → prediction/features.build_features  → (features, meta)
  │         → model or stub  → delay, confidence, reason codes, operational phrases
  │     → crud: create_prediction_audit, update_flight_prediction
  │     → PredictResponse
  │
  └─ GET /flights, GET /alerts, PATCH /alerts/{id}/resolve, etc.
        → routes/*  → crud  → DB  → schema response









































DB (SQLite)
  ↑↓
crud (get_*, create_*, update_*)
  ↑
services (intelligence, overview, reconciliation)   and   routes/prediction → prediction (features, inference)
  ↑
routes (overview, aodb, prediction, flights, alerts, …)
  ↑
FastAPI app (main.py)  ← lifespan: init_db(), inference.load_model()
  ↑
Client (HTTP)














11. Plain-language summary (for a junior dev)
This app is a single backend for “airport operations data”: flights, queues, runways, resources, alerts, and a bit of passenger/retail/identity data. Everything is stored in one SQLite database.
When you call GET /overview (or GET /aodb/overview), the server (1) runs intelligence rules that create alerts (e.g. “queue too long”, “runway hazard”, “gate conflict”) but only if an equivalent alert doesn’t already exist (dedup by a key and by entity). (2) Reconciles each flight: it picks one “best” ETA, status, and gate from many possible sources (latest report, prediction, or schedule) and saves those in the flight row. (3) Reads all the main entities and returns one big JSON snapshot (current_flights, active_alerts, runway_conditions, etc.). So one request both “fixes” alerts and reconciled flight state and then returns that state.
When you call POST /predict with a flight id, the server loads that flight and its flight updates (raw ETA/status/gate reports), turns them into features (schedule, delay at origin, time of day, etc.). It then runs either a trained model (if the file exists at startup) or a simple rule (“stub”) to predict arrival delay. It saves that prediction in two places: an audit table (every prediction for traceability) and the flight row (predicted_eta, delay minutes, confidence). So the “AI” is: feature building + one model (or stub) call; the rest is just reading/writing through crud.
Flights keep both raw data (status, gate, estimated_time) and reconciled values (reconciled_eta, reconciled_status, reconciled_gate) and prediction values (predicted_eta, predicted_arrival_delay_min, etc.). Flight updates are never changed; they’re the raw feed. Reconciliation runs on overview and overwrites only the reconciled_* fields. Prediction runs only when you call POST /predict and overwrites only the prediction_* fields. So: one backend, one DB, one FastAPI app; routes call services and crud; the only “AI” is in the prediction package (features + inference), and the rest is rules and data plumbing.
