from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..crud import create_flight_update, list_flight_updates, get_flight_by_id
from ..schemas import FlightUpdateCreate, FlightUpdateRead

router = APIRouter(prefix="/flight-updates", tags=["flight-updates"])


@router.get("", response_model=list[FlightUpdateRead])
def list_updates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return list_flight_updates(db, skip=skip, limit=limit)


@router.post("", response_model=FlightUpdateRead)
def post_flight_update(payload: FlightUpdateCreate, db: Session = Depends(get_db)):
    if get_flight_by_id(db, payload.flight_id) is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    return create_flight_update(db, payload)
