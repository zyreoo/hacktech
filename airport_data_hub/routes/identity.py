from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_digital_identity_statuses
from ..schemas import DigitalIdentityStatusResponse

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("", response_model=list[DigitalIdentityStatusResponse])
def list_identity(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_digital_identity_statuses(db, skip=skip, limit=limit)
