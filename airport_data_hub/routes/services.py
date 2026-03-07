from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_passenger_services
from ..schemas import PassengerServiceResponse

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[PassengerServiceResponse])
def list_services(status: str | None = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_passenger_services(db, status=status, skip=skip, limit=limit)
