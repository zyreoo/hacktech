from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_passenger_flows, get_passenger_flow_by_flight, get_passenger_flow_issues
from ..schemas import PassengerFlowResponse, PassengerFlowIssueResponse

router = APIRouter(prefix="/passenger-flow", tags=["passenger-flow"])


@router.get("", response_model=list[PassengerFlowResponse])
def list_passenger_flow(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return get_passenger_flows(db, skip=skip, limit=limit)


@router.get("/issues", response_model=list[PassengerFlowIssueResponse])
def list_passenger_flow_issues(limit: int = 300, db: Session = Depends(get_db)):
    """Self-healing and data quality: stale flow, orphan flight, invalid counts."""
    raw = get_passenger_flow_issues(db, limit=limit)
    return [PassengerFlowIssueResponse(**x) for x in raw]


@router.get("/by-flight/{flight_id}", response_model=list[PassengerFlowResponse])
def get_flow_by_flight(flight_id: int, db: Session = Depends(get_db)):
    return get_passenger_flow_by_flight(db, flight_id)
