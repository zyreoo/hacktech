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
    """Pick flights in a wide window so seeded/demo data (e.g. 06:00) is always included."""
    now = datetime.utcnow()
    window_start = now - timedelta(hours=24)
    window_end = now + timedelta(hours=48)
    flights = (
        db.query(Flight)
        .filter(Flight.scheduled_time >= window_start, Flight.scheduled_time <= window_end)
        .order_by(Flight.scheduled_time)
        .all()
    )
    # If no flights in window (e.g. wrong TZ), use any flights so synthetic still produces flow data
    if not flights:
        flights = db.query(Flight).order_by(Flight.scheduled_time.desc()).limit(20).all()
    return flights


def _tick_once(db: Session) -> None:
    """Single synthetic update tick."""
    now = datetime.utcnow()

    # 1) Move passenger flows in real time for more flights with dramatic changes
    flights = _select_active_flights(db)
    if flights:
        sample_size = min(len(flights), 8)  # Increased from 5 to 8
        for flight in random.sample(flights, sample_size):
            # More dramatic passenger count variations
            base_security = random.randint(10, 250)  # Even wider range for more visibility
            # More frequent spikes to trigger alerts (50% chance vs 25%)
            if random.random() < 0.5:
                base_security = random.randint(200, 350)  # Much higher spikes

            pf = PassengerFlow(
                flight_id=flight.id,
                check_in_count=random.randint(10, 400),  # Much wider range
                security_queue_count=base_security,
                boarding_count=random.randint(0, 300),  # Higher max
                predicted_queue_time=random.uniform(1.0, 45.0),  # Wider time range
                terminal_zone=random.choice(["T1", "T2", "T3", "T4", "T5"]),  # More variety
                timestamp=now,
            )
            db.add(pf)

    # 1.5) Also update some existing passenger flows to make immediate changes visible
    existing_flows = db.query(PassengerFlow).order_by(PassengerFlow.timestamp.desc()).limit(20).all()
    if existing_flows:
        flows_to_update = random.sample(existing_flows, min(5, len(existing_flows)))
        for flow in flows_to_update:
            # Dramatically change existing values for immediate visibility
            flow.security_queue_count = random.randint(50, 300)
            flow.check_in_count = random.randint(100, 500)
            flow.boarding_count = random.randint(50, 250)
            flow.predicted_queue_time = random.uniform(5.0, 40.0)
            flow.timestamp = now  # Update timestamp to bring to top

    # 2) More dramatic runway changes
    runways = db.query(Runway).all()
    for r in runways:
        if r.grip_score is None:
            r.grip_score = random.uniform(0.4, 0.95)
        # Larger random walk changes
        if random.random() < 0.8:  # Increased from 0.6
            r.grip_score = _clamp(r.grip_score + random.uniform(-0.12, 0.12), 0.1, 1.0)

        # More frequent hazard changes (20% chance vs 10%)
        if random.random() < 0.2:
            r.hazard_detected = not r.hazard_detected
            if r.hazard_detected:
                r.hazard_type = random.choice([
                    "standing water", "rubber build-up", "FOD", "ice patches", 
                    "debris", "wildlife", "maintenance vehicle"
                ])
            else:
                r.hazard_type = None
        r.last_inspection_time = now

    # 3) More dynamic infrastructure changes
    assets = db.query(InfrastructureAsset).all()
    for asset in assets:
        # More dramatic network health changes
        if asset.network_health is None:
            asset.network_health = random.uniform(0.5, 1.0)
        if random.random() < 0.85:  # Increased from 0.7
            asset.network_health = _clamp(
                asset.network_health + random.uniform(-0.15, 0.15),
                0.1,
                1.0,
            )

        # More frequent status changes (20% chance vs 10%)
        if random.random() < 0.2:
            tamper = random.random() < 0.4  # Slightly higher tamper chance
            asset.tamper_detected = tamper
            if tamper:
                asset.status = random.choice(["degraded", "offline", "maintenance"])
            else:
                # More dynamic status recovery
                if asset.status in ("degraded", "offline", "maintenance") and random.random() < 0.7:
                    asset.status = "operational"

        asset.last_updated = now

    # 4) NEW: Add flight status changes for more visibility
    if flights and random.random() < 0.3:  # 30% chance to update flight statuses
        sample_flights = random.sample(flights, min(3, len(flights)))
        for flight in sample_flights:
            # Randomly update flight status
            if random.random() < 0.5:
                old_status = flight.status
                flight.status = random.choice([
                    "scheduled", "boarding", "departed", "in_air", 
                    "landed", "taxiing", "at_gate", "delayed"
                ])
                # Create a flight update for status change
                from ..models import FlightUpdate
                update = FlightUpdate(
                    flight_id=flight.id,
                    reported_status=flight.status,
                    reported_at=now,
                    source_name="synthetic_generator",
                )
                db.add(update)

    # 5) NEW: Add gate changes for more dynamic feel
    if flights and random.random() < 0.2:  # 20% chance for gate changes
        sample_flights = random.sample(flights, min(2, len(flights)))
        for flight in sample_flights:
            if random.random() < 0.6:
                old_gate = flight.gate
                flight.gate = random.choice(["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "D1"])
                # Create flight update for gate change
                from ..models import FlightUpdate
                update = FlightUpdate(
                    flight_id=flight.id,
                    reported_gate=flight.gate,
                    reported_at=now,
                    source_name="synthetic_generator",
                )
                db.add(update)


# Slower interval so demo self-healing and conflicts stay visible (DB doesn’t change too fast).
DEMO_INTERVAL_SECONDS = 8.0


def _generator_loop(stop_event: threading.Event, interval_seconds: float = None) -> None:
    """Background loop that periodically mutates the DB."""
    if interval_seconds is None:
        interval_seconds = DEMO_INTERVAL_SECONDS
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
        args=(stop_event, DEMO_INTERVAL_SECONDS),
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

