from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_runways, get_runway_by_id, update_runway_hazard
from ..schemas import RunwayResponse, RunwayHazardUpdate

router = APIRouter(prefix="/runways", tags=["runways"])


@router.get("", response_model=list[RunwayResponse])
def list_runways(db: Session = Depends(get_db)):
    return get_runways(db)


@router.get("/{id}", response_model=RunwayResponse)
def get_runway(id: int, db: Session = Depends(get_db)):
    r = get_runway_by_id(db, id)
    if not r:
        raise HTTPException(status_code=404, detail="Runway not found")
    return r


@router.patch("/{id}/hazard", response_model=RunwayResponse)
def patch_runway_hazard(id: int, payload: RunwayHazardUpdate, db: Session = Depends(get_db)):
    r = update_runway_hazard(db, id, payload)
    if not r:
        raise HTTPException(status_code=404, detail="Runway not found")
    return r
