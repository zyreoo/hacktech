from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_retail_events
from ..schemas import RetailEventResponse

router = APIRouter(prefix="/retail", tags=["retail"])


@router.get("", response_model=list[RetailEventResponse])
def list_retail(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_retail_events(db, skip=skip, limit=limit)
