"""
GET /overview: unified airport operations snapshot.
Runs rules-based intelligence (with alert dedup) and flight reconciliation before building the snapshot.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import OverviewResponse
from ..services.overview import get_overview
from ..services.intelligence import run_all_intelligence
from ..services.reconciliation import run_flight_reconciliation

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db)):
    run_all_intelligence(db)
    run_flight_reconciliation(db)
    return get_overview(db)
