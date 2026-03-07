# Alert Deduplication & Flight Reconciliation

## A. Deduplication design

- **Stable uniqueness key**: Each logical alert has a deterministic key so we can detect duplicates. Format: `{alert_type}:{related_entity_type}:{entity_id}`. Examples:
  - `queue:passenger_flow:42`
  - `runway_hazard:runway:1`
  - `grip:runway:1`
  - `security:infrastructure:3`
  - `gate_conflict:flight:5_7` (two flight IDs for the pair)
- **Only create if no equivalent unresolved**: Before inserting, look up an unresolved alert with the same `uniqueness_key`. If one exists, do not create a new one (return existing or skip).
- **Re-create only after resolve or material change**: Once an alert is resolved, the same condition can produce a new alert with the same key. We do not auto-resolve; operators resolve. "Material change" is handled by key design: if the key includes the entity id only, the same entity having the same problem again after resolve creates a new alert.
- **Backward compatibility**: `uniqueness_key` is optional. If not provided, create_alert behaves as before (no dedup). Intelligence layer always passes the key.

## B. Reconciliation design

- **Raw vs reconciled**: Raw source data remains in `Flight` (status, gate, estimated_time) and in `FlightUpdate` (reported_eta, reported_status, reported_gate). Reconciled values live in `Flight.reconciled_status`, `reconciled_gate`, `reconciled_eta`, with `reconciliation_reason`, `reconciliation_confidence`, `last_reconciled_at`.
- **Fields reconciled**: (1) **ETA**: reconciled_eta = latest FlightUpdate.reported_eta (by reported_at) if any, else predicted_eta, else estimated_time, else scheduled_time. (2) **Status**: latest reported_status or Flight.status. (3) **Gate**: latest reported_gate or Flight.gate.
- **Every reconciliation includes**: reconciled value, confidence (0–1), reason (short string), timestamp (last_reconciled_at). Single reason/confidence for the whole record for simplicity; TODO: per-field reason in production.
- **When to run**: On each overview or after intelligence (e.g. run_flight_reconciliation(db) called from the same flow that runs run_all_intelligence).

## C. Updated data model

- **Alert**: add `uniqueness_key` (String(128), nullable, index). Enables lookup by key for dedup.
- **Flight**: add `reconciled_eta` (DateTime, nullable). Existing: reconciled_status, reconciled_gate, reconciliation_reason, reconciliation_confidence, last_reconciled_at.

## D. File-by-file code changes

| File | Change |
|------|--------|
| models.py | Alert.uniqueness_key; Flight.reconciled_eta |
| database.py | Migrations for alerts (uniqueness_key), flights (reconciled_eta) |
| crud.py | get_unresolved_alert_by_uniqueness_key; create_alert(uniqueness_key=..., skip if exists); update_flight_reconciliation |
| schemas.py | AlertResponse + uniqueness_key; FlightResponse + reconciled_eta if not already |
| services/intelligence.py | Build and pass uniqueness_key for every create_alert; use create_alert_only_if_new (or create_alert with key) |
| services/reconciliation.py | New: run_flight_reconciliation(db) |
| services/overview or routes | Call run_flight_reconciliation before or with get_overview (e.g. from overview route or from intelligence) |

## E. Code patches (implemented)

- **models.py**: Alert.uniqueness_key (String(128), index); Flight.reconciled_eta (DateTime).
- **database.py**: _migrate_alerts_uniqueness_key(), _backfill_alerts_uniqueness_key(), _migrate_flights_reconciled_eta(); all in init_db().
- **crud.py**: get_unresolved_alert_by_uniqueness_key(); get_unresolved_alert_by_entity() (fallback for legacy); create_alert() checks key then entity, returns None when duplicate; update_flight_reconciliation().
- **schemas.py**: FlightResponse.reconciled_eta; AlertResponse.uniqueness_key.
- **services/intelligence.py**: Every create_alert passes uniqueness_key; created += 1 only when create_alert returns non-None.
- **services/reconciliation.py**: run_flight_reconciliation(db).
- **routes/overview.py**, **routes/aodb.py**: run_flight_reconciliation after run_all_intelligence.
- **routes/alerts.py**: PATCH /alerts/{id}/resolve body optional; default resolved=true.

### Alert dedup follow-up (legacy + fallback)

- **Root cause**: Legacy unresolved alerts had uniqueness_key = null, so create_alert only checked by key and kept creating new rows for the same logical alert.
- **Fix**: (1) Backfill: _backfill_alerts_uniqueness_key() sets uniqueness_key = alert_type:related_entity_type:related_entity_id for unresolved rows where key is null. (2) Fallback in create_alert: if no match by key, also check unresolved by (alert_type, related_entity_type, related_entity_id); if found, return None. (3) PATCH /alerts/{id}/resolve: body optional, default {"resolved": true}.
