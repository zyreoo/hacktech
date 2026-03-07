from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_infrastructure_assets, get_infrastructure_asset_by_id, update_infrastructure_status
from ..schemas import InfrastructureAssetResponse, InfrastructureStatusUpdate

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


@router.get("", response_model=list[InfrastructureAssetResponse])
def list_infrastructure(db: Session = Depends(get_db)):
    return get_infrastructure_assets(db)


@router.get("/{id}", response_model=InfrastructureAssetResponse)
def get_infrastructure_asset(id: int, db: Session = Depends(get_db)):
    a = get_infrastructure_asset_by_id(db, id)
    if not a:
        raise HTTPException(status_code=404, detail="Infrastructure asset not found")
    return a


@router.patch("/{id}/status", response_model=InfrastructureAssetResponse)
def patch_infrastructure_status(id: int, payload: InfrastructureStatusUpdate, db: Session = Depends(get_db)):
    a = update_infrastructure_status(db, id, payload)
    if not a:
        raise HTTPException(status_code=404, detail="Infrastructure asset not found")
    return a
