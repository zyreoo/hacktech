"""
Seed airport_hub.db with realistic simulated data for demos and hackathon.
Run from repo root: python -m airport_data_hub.seed
"""
from datetime import datetime, timedelta
import random
import sys

from .database import SessionLocal, init_db
from .models import (
    Flight,
    FlightUpdate,
    PassengerFlow,
    Runway,
    Resource,
    Alert,
    InfrastructureAsset,
    PassengerService,
    DigitalIdentityStatus,
    RetailEvent,
)


def seed():
    init_db()
    db = SessionLocal()
    try:
        # Avoid re-seeding if already populated
        if db.query(Flight).first():
            print("DB already seeded. Skip or delete airport_hub.db to re-seed.")
            return

        now = datetime.utcnow()
        base = now.replace(hour=6, minute=0, second=0, microsecond=0)

        # ----- Runways (2) -----
        r1 = Runway(
            runway_code="09L/27R",
            status="active",
            surface_condition="dry",
            contamination_level=0.0,
            grip_score=0.92,
            hazard_detected=False,
            last_inspection_time=now - timedelta(hours=2),
        )
        r2 = Runway(
            runway_code="09R/27L",
            status="active",
            surface_condition="wet",
            contamination_level=0.15,
            grip_score=0.65,
            hazard_detected=False,
            last_inspection_time=now - timedelta(hours=1),
        )
        db.add_all([r1, r2])
        db.commit()
        db.refresh(r1)
        db.refresh(r2)

        # ----- Flights (8–10) -----
        flights_data = [
            ("BA301", "British Airways", "LHR", "CDG", 0, "boarding", "A12", "A12", r1.id),
            ("AF1042", "Air France", "CDG", "LHR", 30, "scheduled", "B7", "B7", r1.id),
            ("LH902", "Lufthansa", "FRA", "LHR", 60, "scheduled", "A8", "A8", r1.id),
            ("KL1008", "KLM", "AMS", "LHR", 90, "delayed", "B22", "B22", r1.id),
            ("IB3166", "Iberia", "MAD", "BCN", 120, "scheduled", "D4", "D4", r2.id),
            ("AZ104", "ITA Airways", "FCO", "CDG", 150, "scheduled", "A3", "A3", r1.id),
            ("EI164", "Aer Lingus", "DUB", "LHR", -30, "departed", "B3", "B3", r1.id),
            ("LX362", "Swiss", "ZRH", "LHR", 180, "scheduled", "A18", "A18", r1.id),
            ("BA178", "British Airways", "LHR", "JFK", 210, "scheduled", "A1", "A1", r1.id),
        ]
        flights = []
        for i, (code, airline, orig, dest, min_offset, status, gate, stand, rwy_id) in enumerate(flights_data):
            st = base + timedelta(minutes=min_offset)
            et = st + timedelta(hours=1, minutes=30) if "LHR" in (orig, dest) else st + timedelta(hours=2)
            f = Flight(
                flight_code=code,
                airline=airline,
                origin=orig,
                destination=dest,
                scheduled_time=st,
                estimated_time=et,
                status=status,
                gate=gate,
                stand=stand,
                runway_id=rwy_id,
            )
            db.add(f)
            flights.append(f)
        db.commit()
        for f in flights:
            db.refresh(f)

        # ----- PassengerFlow -----
        for f in flights[:6]:
            for mins_ago in [60, 45, 30, 15]:
                pf = PassengerFlow(
                    flight_id=f.id,
                    check_in_count=min(120, 80 + (mins_ago // 15) * 10),
                    security_queue_count=40 + (f.id % 5) * 15,
                    boarding_count=0 if mins_ago > 20 else 50,
                    predicted_queue_time=5.0 + (f.id % 4),
                    terminal_zone="T5" if "BA" in f.flight_code else "T2",
                    timestamp=now - timedelta(minutes=mins_ago),
                )
                db.add(pf)
        # One high-queue snapshot to trigger queue alert
        pf_high = PassengerFlow(
            flight_id=flights[0].id,
            check_in_count=180,
            security_queue_count=95,
            boarding_count=20,
            predicted_queue_time=18.0,
            terminal_zone="T5",
            timestamp=now,
        )
        db.add(pf_high)
        db.commit()

        # ----- FlightUpdate (AODB: multi-source conflicting inputs for 3 flights) -----
        t0 = now
        # Flight 1 (BA301): airline vs radar vs airport_ops — different ETA, gate, status
        for flight_idx, f in enumerate(flights[:3]):
            base_eta = f.estimated_time or f.scheduled_time + timedelta(hours=1)
            if flight_idx == 0:  # BA301
                updates = [
                    ("airline", base_eta, "boarding", "A12", t0 - timedelta(minutes=20), 0.95),
                    ("radar", base_eta + timedelta(minutes=15), "delayed", "A12", t0 - timedelta(minutes=10), 0.88),
                    ("airport_ops", base_eta + timedelta(minutes=5), "boarding", "A14", t0 - timedelta(minutes=5), 0.75),
                ]
            elif flight_idx == 1:  # AF1042
                updates = [
                    ("airline", base_eta, "scheduled", "B7", t0 - timedelta(minutes=25), 0.9),
                    ("radar", base_eta - timedelta(minutes=10), "approach", "B7", t0 - timedelta(minutes=8), 0.92),
                    ("airport_ops", base_eta + timedelta(minutes=5), "scheduled", "B9", t0 - timedelta(minutes=2), 0.7),
                ]
            else:  # LH902
                updates = [
                    ("airline", base_eta, "scheduled", "A8", t0 - timedelta(minutes=30), 0.85),
                    ("radar", base_eta + timedelta(minutes=20), "delayed", None, t0 - timedelta(minutes=12), 0.8),
                    ("airport_ops", base_eta + timedelta(minutes=10), "delayed", "A8", t0 - timedelta(minutes=3), 0.78),
                ]
            for source_name, r_eta, r_status, r_gate, r_at, conf in updates:
                db.add(FlightUpdate(
                    flight_id=f.id,
                    source_name=source_name,
                    reported_eta=r_eta,
                    reported_status=r_status,
                    reported_gate=r_gate,
                    reported_at=r_at,
                    confidence_score=conf,
                ))
        db.commit()

        # ----- Resources (gates, stands, desks) -----
        resources_data = [
            ("A1", "gate", "assigned", "BA178", "T5 North"),
            ("A3", "gate", "assigned", "AZ104", "T5 North"),
            ("A8", "gate", "assigned", "LH902", "T1"),
            ("A12", "gate", "assigned", "BA301", "T5 North"),
            ("A18", "gate", "assigned", "LX362", "T1"),
            ("B3", "gate", "available", None, "T2"),
            ("B7", "gate", "assigned", "AF1042", "T2"),
            ("B22", "gate", "assigned", "KL1008", "T2"),
            ("D4", "gate", "assigned", "IB3166", "T4"),
            ("Check-in Zone A", "desk", "available", None, "T5"),
            ("Security Lane 1", "desk", "available", None, "T5"),
        ]
        for name, rtype, status, assigned, loc in resources_data:
            db.add(Resource(resource_name=name, resource_type=rtype, status=status, assigned_to=assigned, location=loc))
        db.commit()

        # ----- Alerts -----
        alerts_data = [
            ("queue", "warning", "data_hub", "T5 security queue above 15 min", "passenger_flow", None),
            ("runway_hazard", "info", "data_hub", "Runway 09R wet - grip reduced", "runway", str(r2.id)),
            ("grip", "warning", "data_hub", "Runway 09R grip score 0.65", "runway", str(r2.id)),
        ]
        for atype, sev, src, msg, rel_type, rel_id in alerts_data:
            db.add(Alert(alert_type=atype, severity=sev, source_module=src, message=msg, related_entity_type=rel_type, related_entity_id=rel_id, resolved=False))
        db.commit()

        # ----- InfrastructureAssets -----
        assets_data = [
            ("Jet Bridge A12", "jet_bridge", "operational", 0.98, False, "T5 A12", "T5", "A12"),
            ("Baggage Belt B", "baggage_belt", "operational", 0.92, False, "T5 Baggage", "T5", None),
            ("Camera Runway 09L", "camera", "operational", 1.0, False, "Runway 09L", None, None),
            ("Sensor Gate A1", "sensor", "degraded", 0.65, True, "T5 A1", "T5", "A1"),
        ]
        for name, atype, status, health, tamper, loc, terminal, gate in assets_data:
            db.add(InfrastructureAsset(
                asset_name=name, 
                asset_type=atype, 
                status=status, 
                network_health=health, 
                tamper_detected=tamper, 
                location=loc,
                terminal=terminal,
                gate=gate,
                health_score=health,
                last_heartbeat=now,
                uptime_percentage=99.5,
                error_count_24h=0,
                usage_cycles=random.randint(100, 1000),
                total_usage_time=random.uniform(500, 5000),
                maintenance_priority="normal",
                created_at=now - timedelta(days=random.randint(30, 365)),
                updated_at=now,
                last_updated_by="seed"
            ))
        db.commit()

        # ----- PassengerServices -----
        for i, (pref, stype, status, req_mins) in enumerate([
            ("PAX-001", "assistance", "in_progress", 30),
            ("PAX-002", "lounge", "completed", 120),
            ("PAX-003", "transfer", "pending", 15),
            ("PAX-004", "info", "completed", 45),
        ]):
            req = now - timedelta(minutes=req_mins)
            comp = req + timedelta(minutes=20) if status == "completed" else None
            db.add(PassengerService(passenger_reference=pref, service_type=stype, status=status, request_time=req, completion_time=comp, location="T5"))
        db.commit()

        # ----- DigitalIdentityStatus -----
        for i, (pref, vstatus, method) in enumerate([
            ("PAX-001", "verified", "biometric"),
            ("PAX-002", "verified", "document"),
            ("PAX-003", "pending", None),
            ("PAX-004", "verified", "token"),
            ("PAX-005", "failed", "document"),
        ]):
            db.add(DigitalIdentityStatus(passenger_reference=pref, verification_status=vstatus, verification_method=method, last_verified_at=now - timedelta(hours=1) if vstatus == "verified" else None, token_reference=f"tok-{i}" if "token" in str(method) else None))
        db.commit()

        # ----- RetailEvents -----
        for i, (pref, offer, order_st, gate) in enumerate([
            ("PAX-001", "duty_free", "picked_up", "A12"),
            ("PAX-002", "food", "placed", None),
            ("PAX-003", "lounge", "prepared", "A8"),
        ]):
            db.add(RetailEvent(passenger_reference=pref, offer_type=offer, order_status=order_st, pickup_gate=gate, created_at=now - timedelta(minutes=30 + i * 10)))
        db.commit()

        print("Seed complete: flights, flight_updates, runways, passenger_flow, resources, alerts, infrastructure, services, identity, retail.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
