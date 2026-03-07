from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_resources, get_resource_by_id, update_resource_status
from ..schemas import ResourceResponse, ResourceStatusUpdate

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=list[ResourceResponse])
def list_resources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_resources(db, skip=skip, limit=limit)


@router.get("/{id}", response_model=ResourceResponse)
def get_resource(id: int, db: Session = Depends(get_db)):
    r = get_resource_by_id(db, id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    return r


@router.patch("/{id}/status", response_model=ResourceResponse)
def patch_resource_status(id: int, payload: ResourceStatusUpdate, db: Session = Depends(get_db)):
    r = update_resource_status(db, id, payload)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    return r
