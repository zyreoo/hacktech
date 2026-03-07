"""
Synthetic data generator for the Airport Data Hub.

Continuously mutates the SQLite hub database so that:
- passenger flow counts move in real time
- runway conditions and hazards fluctuate
- infrastructure health / tamper flags change over time

Designed for hackathon demos: runs in a lightweight background thread that
uses the same SQLAlchemy SessionLocal as the FastAPI app.
"""

from __future__ import annotations

import random
import threading
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Flight, PassengerFlow, Runway, InfrastructureAsset

_generator_thread: Optional[threading.Thread] = None
_stop_event: Optional[threading.Event] = None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _select_active_flights(db: Session) -> list[Flight]:
    """Pick flights that are close to 'now' so changes are visible."""
    now = datetime.utcnow()
    window_start = now - timedelta(hours=2)
    window_end = now + timedelta(hours=4)
    return (
        db.query(Flight)
        .filter(Flight.scheduled_time >= window_start, Flight.scheduled_time <= window_end)
        .order_by(Flight.scheduled_time)
        .all()
    )


def _tick_once(db: Session) -> None:
    """Single synthetic update tick."""
    now = datetime.utcnow()

    # 1) Move passenger flows in real time for a handful of flights
    flights = _select_active_flights(db)
    if flights:
        sample_size = min(len(flights), 5)
        for flight in random.sample(flights, sample_size):
            # Base crowds around security; occasionally spike to trigger alerts
            base_security = random.randint(20, 90)
            if random.random() < 0.25:
                base_security = random.randint(90, 140)

            pf = PassengerFlow(
                flight_id=flight.id,
                check_in_count=random.randint(30, 160),
                security_queue_count=base_security,
                boarding_count=random.randint(0, 120),
                predicted_queue_time=random.uniform(4.0, 22.0),
                terminal_zone="T5" if "BA" in flight.flight_code else "T2",
                timestamp=now,
            )
            db.add(pf)

    # 2) Slightly perturb runway grip / hazards
    runways = db.query(Runway).all()
    for r in runways:
        if r.grip_score is None:
            r.grip_score = random.uniform(0.5, 0.95)
        # Small random walk
        if random.random() < 0.6:
            r.grip_score = _clamp(r.grip_score + random.uniform(-0.06, 0.06), 0.2, 1.0)

        # Occasionally flip hazard flag on one runway
        if random.random() < 0.1:
            r.hazard_detected = not r.hazard_detected
            if r.hazard_detected:
                r.hazard_type = random.choice(
                    ["standing water", "rubber build-up", "FOD", "ice patches"]
                )
            else:
                r.hazard_type = None
        r.last_inspection_time = now

    # 3) Nudge infrastructure health and tamper flags
    assets = db.query(InfrastructureAsset).all()
    for asset in assets:
        # Random walk for network health
        if asset.network_health is None:
            asset.network_health = random.uniform(0.6, 1.0)
        if random.random() < 0.7:
            asset.network_health = _clamp(
                asset.network_health + random.uniform(-0.08, 0.08),
                0.2,
                1.0,
            )

        # Occasionally toggle tamper / degraded status
        if random.random() < 0.1:
            tamper = random.random() < 0.3
            asset.tamper_detected = tamper
            if tamper:
                asset.status = random.choice(["degraded", "offline"])
            else:
                # Allow some assets to stay degraded without tamper
                if asset.status in ("degraded", "offline") and random.random() < 0.5:
                    asset.status = "operational"

        asset.last_updated = now


def _generator_loop(stop_event: threading.Event, interval_seconds: float = 5.0) -> None:
    """Background loop that periodically mutates the DB."""
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            _tick_once(db)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        # Wait with early-exit if stop requested
        if stop_event.wait(interval_seconds):
            break


def start_synthetic_feeder() -> None:
    """Start the background synthetic data generator thread (idempotent)."""
    global _generator_thread, _stop_event
    if _generator_thread and _generator_thread.is_alive():
        return

    stop_event = threading.Event()
    thread = threading.Thread(
        target=_generator_loop,
        args=(stop_event,),
        name="synthetic-data-feeder",
        daemon=True,
    )
    _stop_event = stop_event
    _generator_thread = thread
    thread.start()


def stop_synthetic_feeder(timeout: float = 2.0) -> None:
    """Signal the background generator to stop and wait briefly."""
    global _generator_thread, _stop_event
    if not _stop_event or not _generator_thread:
        return

    _stop_event.set()
    if _generator_thread.is_alive():
        _generator_thread.join(timeout=timeout)

    _generator_thread = None
    _stop_event = None

