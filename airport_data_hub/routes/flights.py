from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_flights, get_flight_by_id, update_flight_status, update_flight_prediction, update_flight_reassign, get_flight_updates_for_flight, get_flight_issues
from ..schemas import FlightResponse, FlightStatusUpdate, FlightPredictionUpdate, FlightReassignUpdate, FlightUpdateRead, FlightIssueResponse

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("", response_model=list[FlightResponse])
def list_flights(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_flights(db, skip=skip, limit=limit)


@router.get("/issues", response_model=list[FlightIssueResponse])
def list_flight_issues(limit: int = 500, db: Session = Depends(get_db)):
    """Self-healing and conflicts: runway unavailable, gate conflict."""
    raw = get_flight_issues(db, limit=limit)
    return [FlightIssueResponse(**item) for item in raw]


@router.get("/{id}", response_model=FlightResponse)
def get_flight(id: int, db: Session = Depends(get_db)):
    flight = get_flight_by_id(db, id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.get("/{id}/updates", response_model=list[FlightUpdateRead])
def get_flight_updates(id: int, db: Session = Depends(get_db)):
    flight = get_flight_by_id(db, id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return get_flight_updates_for_flight(db, id)


@router.patch("/{id}/status", response_model=FlightResponse)
def patch_flight_status(id: int, payload: FlightStatusUpdate, db: Session = Depends(get_db)):
    flight = update_flight_status(db, id, payload)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.patch("/{id}/prediction", response_model=FlightResponse)
def patch_flight_prediction(id: int, payload: FlightPredictionUpdate, db: Session = Depends(get_db)):
    """Accept prediction results from arrival delay prediction service (AODB write-back)."""
    flight = update_flight_prediction(db, id, payload)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.patch("/{id}/reassign", response_model=FlightResponse)
def patch_flight_reassign(id: int, payload: FlightReassignUpdate, db: Session = Depends(get_db)):
    """Reassign flight to another runway or gate (self-healing fix)."""
    flight = update_flight_reassign(db, id, payload)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight
