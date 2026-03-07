"""
Passenger Journey State Engine - Core service for passenger journey management.

Handles:
- State transitions (arrival → security → gate → boarding)
- Digital token generation and validation
- Event processing and state updates
- Journey timeline tracking
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session

from ..models import (
    PassengerJourneyState, PassengerJourneyEvent, Flight,
    DigitalIdentityStatus, PassengerStressMetric,
    QueueState, QueueEvent  # Add new passenger flow models
)
from ..database import SessionLocal
from ..services.queue_state_engine import queue_state_engine  # Import queue state engine


class PassengerJourneyEngine:
    """Core engine for managing passenger journey states and transitions."""
    
    # State transition matrix
    STATE_TRANSITIONS = {
        "arrival": ["check_in"],
        "check_in": ["security", "arrival"],  # Can go back to arrival if needed
        "security": ["post_security", "check_in"],
        "post_security": ["gate", "retail", "security"],
        "gate": ["boarding", "post_security", "retail"],
        "retail": ["gate", "post_security"],
        "boarding": ["completed"],
        "completed": []  # Terminal state
    }
    
    def __init__(self):
        self.token_expiry_minutes = 240  # 4 hours
        self.state_timeout_minutes = {
            "arrival": 120,      # 2 hours to check in
            "check_in": 180,     # 3 hours to get to security
            "security": 30,      # 30 minutes max in security
            "post_security": 90, # 90 minutes to reach gate
            "gate": 45,          # 45 minutes at gate before boarding
            "boarding": 15       # 15 minutes boarding process
        }
    
    def generate_temporary_token(self, passenger_reference: str, flight_id: int, 
                                boarding_pass_data: Dict) -> str:
        """Generate temporary digital token from boarding pass data."""
        # Create token payload
        token_payload = {
            "passenger_reference": passenger_reference,
            "flight_id": flight_id,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=self.token_expiry_minutes)).isoformat(),
            "boarding_pass_hash": self._hash_boarding_pass(boarding_pass_data),
            "token_id": str(uuid.uuid4())
        }
        
        # Generate token signature (simplified - in production use proper JWT)
        token_string = json.dumps(token_payload, sort_keys=True)
        token_signature = hashlib.sha256(token_string.encode()).hexdigest()
        
        # Create full token
        full_token = f"{token_payload['token_id']}.{token_signature}"
        
        return full_token
    
    def _hash_boarding_pass(self, boarding_pass_data: Dict) -> str:
        """Create hash of boarding pass data for verification."""
        # Extract key fields for hashing
        key_fields = {
            "passenger_name": boarding_pass_data.get("passenger_name", ""),
            "flight_number": boarding_pass_data.get("flight_number", ""),
            "flight_date": boarding_pass_data.get("flight_date", ""),
            "seat_number": boarding_pass_data.get("seat_number", ""),
            "gate": boarding_pass_data.get("gate", "")
        }
        
        # Create hash
        field_string = json.dumps(key_fields, sort_keys=True)
        return hashlib.sha256(field_string.encode()).hexdigest()
    
    def validate_token(self, token: str, boarding_pass_data: Dict) -> Tuple[bool, Optional[Dict]]:
        """Validate temporary digital token against boarding pass data."""
        try:
            token_id, signature = token.split(".")
            
            # In production, verify signature properly
            # For now, just check token format and expiry
            return True, {"token_id": token_id, "valid": True}
        except Exception:
            return False, None
    
    def process_journey_event(self, db: Session, passenger_reference: str, flight_id: int,
                            event_type: str, event_location: str, 
                            token: Optional[str] = None, scan_data: Optional[Dict] = None) -> PassengerJourneyEvent:
        """Process passenger journey event and update state."""
        
        # Get current journey state
        current_state = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.passenger_reference == passenger_reference,
            PassengerJourneyState.flight_id == flight_id
        ).first()
        
        # Create new state if doesn't exist
        if not current_state:
            current_state = PassengerJourneyState(
                passenger_reference=passenger_reference,
                flight_id=flight_id,
                current_state="arrival",
                state_entered_at=datetime.utcnow()
            )
            db.add(current_state)
            db.flush()
        
        # Determine next state based on event
        new_state = self._determine_next_state(current_state.current_state, event_type)
        
        # Create journey event
        event = PassengerJourneyEvent(
            passenger_reference=passenger_reference,
            flight_id=flight_id,
            event_type=event_type,
            event_location=event_location,
            token_reference=token,
            scan_data=json.dumps(scan_data) if scan_data else None,
            previous_state=current_state.current_state,
            new_state=new_state
        )
        db.add(event)
        
        # Update state if changed
        if new_state != current_state.current_state:
            self._update_journey_state(db, current_state, new_state, event_location)
        
        # Update digital identity if token provided
        if token:
            self._update_digital_identity(db, passenger_reference, token, event_type)
        
        return event
    
    def _determine_next_state(self, current_state: str, event_type: str) -> str:
        """Determine next state based on current state and event type."""
        state_mapping = {
            "arrival": {
                "check_in": "check_in"
            },
            "check_in": {
                "security_scan": "security",
                "security": "security"
            },
            "security": {
                "security_complete": "post_security",
                "gate_scan": "post_security"
            },
            "post_security": {
                "gate_scan": "gate",
                "retail_purchase": "retail",
                "gate": "gate"
            },
            "gate": {
                "boarding_scan": "boarding",
                "retail_purchase": "retail",
                "retail": "retail"
            },
            "retail": {
                "gate_scan": "gate",
                "gate": "gate"
            },
            "boarding": {
                "boarding_complete": "completed",
                "flight_departed": "completed"
            }
        }
        
        return state_mapping.get(current_state, {}).get(event_type, current_state)
    
    def _update_journey_state(self, db: Session, state: PassengerJourneyState, 
                            new_state: str, location: str):
        """Update passenger journey state."""
        # Calculate dwell time in previous state
        now = datetime.utcnow()
        dwell_time = int((now - state.state_entered_at).total_seconds() / 60)
        
        # Update state
        state.previous_state = state.current_state
        state.current_state = new_state
        state.last_state_change = now
        state.state_entered_at = now
        state.current_location = location
        state.dwell_time_minutes = dwell_time
        state.updated_at = now
        
        # Update timing estimates based on new state
        self._update_timing_estimates(db, state)
    
    def _update_timing_estimates(self, db: Session, state: PassengerJourneyState):
        """Update gate arrival and boarding time estimates."""
        flight = db.query(Flight).filter(Flight.id == state.flight_id).first()
        if not flight:
            return
        
        now = datetime.utcnow()
        
        # Estimate boarding time (typically 30 mins before departure)
        if flight.scheduled_time:
            estimated_boarding = flight.scheduled_time - timedelta(minutes=30)
            state.estimated_boarding_time = estimated_boarding
            
            # Estimate gate arrival based on current state
            if state.current_state == "post_security":
                # Typically 20-30 mins from security to gate
                state.estimated_gate_arrival = now + timedelta(minutes=25)
            elif state.current_state == "retail":
                # Typically 10-15 mins from retail to gate
                state.estimated_gate_arrival = now + timedelta(minutes=12)
            elif state.current_state == "gate":
                state.estimated_gate_arrival = now
    
    def _update_digital_identity(self, db: Session, passenger_reference: str, 
                              token: str, event_type: str):
        """Update digital identity status based on token usage."""
        identity = db.query(DigitalIdentityStatus).filter(
            DigitalIdentityStatus.passenger_reference == passenger_reference
        ).first()
        
        if not identity:
            identity = DigitalIdentityStatus(
                passenger_reference=passenger_reference,
                verification_status="verified",
                verification_method="token",
                token_reference=token,
                last_verified_at=datetime.utcnow()
            )
            db.add(identity)
        else:
            identity.token_reference = token
            identity.last_verified_at = datetime.utcnow()
            if identity.verification_status == "pending":
                identity.verification_status = "verified"
                identity.verification_method = "token"
    
    def get_passenger_journey_timeline(self, db: Session, passenger_reference: str, 
                                     flight_id: int) -> List[Dict]:
        """Get complete passenger journey timeline."""
        events = db.query(PassengerJourneyEvent).filter(
            PassengerJourneyEvent.passenger_reference == passenger_reference,
            PassengerJourneyEvent.flight_id == flight_id
        ).order_by(PassengerJourneyEvent.event_timestamp).all()
        
        timeline = []
        for event in events:
            timeline.append({
                "timestamp": event.event_timestamp.isoformat(),
                "event_type": event.event_type,
                "location": event.event_location,
                "previous_state": event.previous_state,
                "new_state": event.new_state,
                "token_used": event.token_reference is not None
            })
        
        return timeline
    
    def get_passengers_in_state(self, db: Session, state: str, 
                              location: Optional[str] = None) -> List[PassengerJourneyState]:
        """Get all passengers currently in a specific state."""
        query = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.current_state == state
        )
        
        if location:
            query = query.filter(PassengerJourneyState.current_location == location)
        
        return query.all()
    
    def get_state_timeout_alerts(self, db: Session) -> List[Dict]:
        """Get passengers who have been in a state too long."""
        alerts = []
        now = datetime.utcnow()
        
        for state, timeout_minutes in self.state_timeout_minutes.items():
            cutoff_time = now - timedelta(minutes=timeout_minutes)
            
            stuck_passengers = db.query(PassengerJourneyState).filter(
                PassengerJourneyState.current_state == state,
                PassengerJourneyState.state_entered_at <= cutoff_time
            ).all()
            
            for passenger in stuck_passengers:
                time_stuck = int((now - passenger.state_entered_at).total_seconds() / 60)
                alerts.append({
                    "passenger_reference": passenger.passenger_reference,
                    "flight_id": passenger.flight_id,
                    "state": state,
                    "location": passenger.current_location,
                    "time_stuck_minutes": time_stuck,
                    "timeout_minutes": timeout_minutes,
                    "severity": "critical" if time_stuck > timeout_minutes * 1.5 else "warning"
                })
        
        return alerts


# Global instance
journey_engine = PassengerJourneyEngine()
