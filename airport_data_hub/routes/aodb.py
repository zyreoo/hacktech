"""
AODB (Airport Operations Database) view: canonical flight state including
reconciled and predicted fields. Same data as /flights and /overview, explicit AODB entry point.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..crud import get_flights, get_flight_by_id
from ..schemas import FlightResponse, OverviewResponse
from ..services.overview import get_overview
from ..services.intelligence import run_all_intelligence
from ..services.reconciliation import run_flight_reconciliation

router = APIRouter(prefix="/aodb", tags=["aodb"])


@router.get("/flights", response_model=list[FlightResponse])
def aodb_flights(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Canonical AODB flight list: schedule + reconciled + predicted (e.g. predicted_eta, predicted_arrival_delay_min)."""
    return get_flights(db, skip=skip, limit=limit)


@router.get("/flights/{id}", response_model=FlightResponse)
def aodb_flight(id: int, db: Session = Depends(get_db)):
    """Canonical AODB flight by id."""
    flight = get_flight_by_id(db, id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.get("/overview", response_model=OverviewResponse)
def aodb_overview(db: Session = Depends(get_db)):
    """Full AODB snapshot: flights (with reconciled + predicted), queues, runways, alerts, resources, etc."""
    run_all_intelligence(db)
    run_flight_reconciliation(db)
    return get_overview(db)
