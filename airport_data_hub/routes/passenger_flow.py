from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_passenger_flows, get_passenger_flow_by_flight
from ..schemas import PassengerFlowResponse

router = APIRouter(prefix="/passenger-flow", tags=["passenger-flow"])


@router.get("", response_model=list[PassengerFlowResponse])
def list_passenger_flow(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return get_passenger_flows(db, skip=skip, limit=limit)


@router.get("/by-flight/{flight_id}", response_model=list[PassengerFlowResponse])
def get_flow_by_flight(flight_id: int, db: Session = Depends(get_db)):
    return get_passenger_flow_by_flight(db, flight_id)
