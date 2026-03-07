"""
Passenger Journey API endpoints.

Handles:
- Journey state management
- Event ingestion (scans)
- Digital token operations
- Journey timeline tracking
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..services.passenger_journey import journey_engine
from ..services.passenger_intelligence import intelligence_engine
from ..services.passenger_insights import insights_engine
from ..models import PassengerJourneyState, PassengerJourneyEvent
from ..schemas import (
    PassengerJourneyStateResponse, PassengerJourneyEventResponse,
    PassengerStressMetricResponse, PassengerInsightResponse
)

router = APIRouter(prefix="/passenger-journey", tags=["passenger-journey"])


@router.get("")
def get_passenger_journey_overview(db: Session = Depends(get_db)):
    """Get passenger journey system overview."""
    try:
        # Get basic stats
        total_states = db.query(PassengerJourneyState).count()
        active_states = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.current_state.in_(["arrival", "check_in", "security", "gate", "boarding"])
        ).count()
        recent_events = db.query(PassengerJourneyEvent).order_by(
            PassengerJourneyEvent.event_timestamp.desc()
        ).limit(10).all()
        
        return {
            "message": "Passenger Journey System Active",
            "total_passenger_states": total_states,
            "active_journeys": active_states,
            "recent_events": [
                {
                    "passenger_reference": event.passenger_reference,
                    "event_type": event.event_type,
                    "event_timestamp": event.event_timestamp.isoformat(),
                    "location": event.location
                } for event in recent_events
            ],
            "available_endpoints": {
                "timeline": "/passenger-journey/passengers/{passenger_reference}/timeline",
                "state": "/passenger-journey/passengers/{passenger_reference}/state", 
                "alerts": "/passenger-journey/alerts/timeouts",
                "flight_passengers": "/passenger-journey/flights/{flight_id}/passengers"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Pydantic models for requests
class JourneyEventRequest(BaseModel):
    passenger_reference: str
    flight_id: int
    event_type: str
    event_location: str
    token: Optional[str] = None
    scan_data: Optional[Dict] = None


class TokenGenerationRequest(BaseModel):
    passenger_reference: str
    flight_id: int
    boarding_pass_data: Dict


class TokenValidationRequest(BaseModel):
    token: str
    boarding_pass_data: Dict


@router.post("/events", response_model=PassengerJourneyEventResponse)
def ingest_journey_event(request: JourneyEventRequest, db: Session = Depends(get_db)):
    """Ingest passenger journey event (scan, interaction, etc.)."""
    try:
        event = journey_engine.process_journey_event(
            db=db,
            passenger_reference=request.passenger_reference,
            flight_id=request.flight_id,
            event_type=request.event_type,
            event_location=request.event_location,
            token=request.token,
            scan_data=request.scan_data
        )
        return PassengerJourneyEventResponse.model_validate(event)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tokens/generate")
def generate_temporary_token(request: TokenGenerationRequest, db: Session = Depends(get_db)):
    """Generate temporary digital token from boarding pass data."""
    try:
        token = journey_engine.generate_temporary_token(
            passenger_reference=request.passenger_reference,
            flight_id=request.flight_id,
            boarding_pass_data=request.boarding_pass_data
        )
        return {"token": token, "expires_in_minutes": journey_engine.token_expiry_minutes}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tokens/validate")
def validate_token(request: TokenValidationRequest, db: Session = Depends(get_db)):
    """Validate temporary digital token against boarding pass data."""
    try:
        is_valid, token_data = journey_engine.validate_token(
            token=request.token,
            boarding_pass_data=request.boarding_pass_data
        )
        return {"valid": is_valid, "token_data": token_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/passengers/{passenger_reference}/timeline")
def get_passenger_timeline(passenger_reference: str, flight_id: int, db: Session = Depends(get_db)):
    """Get complete passenger journey timeline."""
    try:
        timeline = journey_engine.get_passenger_journey_timeline(
            db=db,
            passenger_reference=passenger_reference,
            flight_id=flight_id
        )
        return {"passenger_reference": passenger_reference, "flight_id": flight_id, "timeline": timeline}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/passengers/{passenger_reference}/state")
def get_passenger_state(passenger_reference: str, flight_id: int, db: Session = Depends(get_db)):
    """Get current passenger journey state."""
    state = db.query(PassengerJourneyState).filter(
        PassengerJourneyState.passenger_reference == passenger_reference,
        PassengerJourneyState.flight_id == flight_id
    ).first()
    
    if not state:
        raise HTTPException(status_code=404, detail="Passenger journey state not found")
    
    return PassengerJourneyStateResponse.model_validate(state)


@router.get("/state/{state}/passengers")
def get_passengers_in_state(state: str, location: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all passengers currently in a specific state."""
    try:
        passengers = journey_engine.get_passengers_in_state(
            db=db,
            state=state,
            location=location
        )
        return [PassengerJourneyStateResponse.model_validate(p) for p in passengers]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/alerts/timeouts")
def get_state_timeout_alerts(db: Session = Depends(get_db)):
    """Get passengers who have been in a state too long."""
    try:
        alerts = journey_engine.get_state_timeout_alerts(db)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flights/{flight_id}/passengers")
def get_flight_passenger_journeys(flight_id: int, db: Session = Depends(get_db)):
    """Get all passenger journeys for a specific flight."""
    passengers = db.query(PassengerJourneyState).filter(
        PassengerJourneyState.flight_id == flight_id
    ).all()
    
    return [PassengerJourneyStateResponse.model_validate(p) for p in passengers]


@router.get("/flights/{flight_id}/events")
def get_flight_journey_events(flight_id: int, db: Session = Depends(get_db)):
    """Get all journey events for a specific flight."""
    events = db.query(PassengerJourneyEvent).filter(
        PassengerJourneyEvent.flight_id == flight_id
    ).order_by(PassengerJourneyEvent.event_timestamp.desc()).all()
    
    return [PassengerJourneyEventResponse.model_validate(e) for e in events]
