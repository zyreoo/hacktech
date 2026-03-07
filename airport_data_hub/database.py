"""
Airport Data Hub - Database layer.
Single SQLite DB as the operational backbone for all modules.
TODO: For production scale, consider PostgreSQL and connection pooling; migrations via Alembic.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use a dedicated hub DB so existing airport.db and other modules stay independent.
# Absolute path so background thread and request handlers resolve the same file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.environ.get("AIRPORT_HUB_DB", os.path.join(BASE_DIR, "airport_hub.db")))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 15,  # Wait up to 15s for lock (synthetic thread + overview can write concurrently)
    },
    echo=False,  # set True for SQL logging during dev
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and closes it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_flights_prediction_columns():
    """Add AODB prediction columns to flights if missing (e.g. after pull)."""
    from sqlalchemy import text
    cols = [
        ("predicted_arrival_delay_min", "REAL"),
        ("prediction_confidence", "REAL"),
        ("prediction_model_version", "VARCHAR(50)"),
        ("last_prediction_at", "DATETIME"),
    ]
    with engine.connect() as conn:
        for name, typ in cols:
            try:
                conn.execute(text(f"ALTER TABLE flights ADD COLUMN {name} {typ}"))
                conn.commit()
            except Exception:
                conn.rollback()
                pass


def _migrate_prediction_audit_columns():
    """Add hardening columns to prediction_audit if missing (outcome, quality, operational codes)."""
    from sqlalchemy import text
    cols = [
        ("prediction_outcome", "VARCHAR(32)"),
        ("input_quality_score", "REAL"),
        ("missing_features", "TEXT"),
        ("stale_data_warnings", "TEXT"),
        ("operational_reason_codes", "TEXT"),
    ]
    with engine.connect() as conn:
        for name, typ in cols:
            try:
                conn.execute(text(f"ALTER TABLE prediction_audit ADD COLUMN {name} {typ}"))
                conn.commit()
            except Exception:
                conn.rollback()
                pass


def _migrate_alerts_uniqueness_key():
    """Add uniqueness_key to alerts for deduplication."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE alerts ADD COLUMN uniqueness_key VARCHAR(128)"))
            conn.commit()
    except Exception:
        pass


def _backfill_alerts_uniqueness_key():
    """
    Backfill uniqueness_key for existing unresolved alerts where it is null (legacy rows).
    Key format: alert_type:related_entity_type:related_entity_id (or id if entity id null).
    After this, duplicate checks by key or by (type, entity_type, entity_id) prevent logical duplicates.
    """
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                UPDATE alerts
                SET uniqueness_key = alert_type || ':' || COALESCE(related_entity_type, 'unknown') || ':' || COALESCE(related_entity_id, CAST(id AS TEXT))
                WHERE resolved = 0 AND (uniqueness_key IS NULL OR uniqueness_key = '')
                """)
            )
            conn.commit()
    except Exception:
        pass


def _migrate_flights_reconciled_eta():
    """Add reconciled_eta to flights for reconciliation."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE flights ADD COLUMN reconciled_eta DATETIME"))
            conn.commit()
    except Exception:
        pass


def _migrate_queue_alert_messages():
    """
    One-time: update existing queue alerts so message shows flight code instead of flight_id.
    e.g. '... (flight_id=4)' -> '... for BA301'
    """
    import re
    from .models import Alert
    from .crud import get_flight_by_id

    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(
            Alert.alert_type == "queue",
            Alert.message.like("%flight_id=%"),
        ).all()
        for a in alerts:
            match = re.search(r"\(flight_id=(\d+)\)", a.message)
            if not match:
                continue
            flight_id = int(match.group(1))
            flight = get_flight_by_id(db, flight_id)
            if flight:
                a.message = re.sub(r"\(flight_id=\d+\)", f"for {flight.flight_code}", a.message)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def init_db():
    """Create all tables. Called at app startup or via seed."""
    Base.metadata.create_all(bind=engine)
    _migrate_flights_prediction_columns()
    _migrate_prediction_audit_columns()
    _migrate_alerts_uniqueness_key()
    _backfill_alerts_uniqueness_key()
    _migrate_flights_reconciled_eta()
    _migrate_queue_alert_messages()
