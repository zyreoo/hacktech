from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import get_alerts, get_alert_by_id, update_alert_resolve, get_alert_issues
from ..schemas import AlertResponse, AlertResolveUpdate, AlertIssueResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(resolved: bool | None = None, skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    alerts = get_alerts(db, resolved=resolved, skip=skip, limit=limit)
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get("/issues", response_model=list[AlertIssueResponse])
def list_alert_issues(limit: int = 300, db: Session = Depends(get_db)):
    """Self-healing and data quality: stale critical, orphan references, duplicate unresolved."""
    raw = get_alert_issues(db, limit=limit)
    return [AlertIssueResponse(**item) for item in raw]


@router.get("/{id}", response_model=AlertResponse)
def get_alert(id: int, db: Session = Depends(get_db)):
    a = get_alert_by_id(db, id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(a)


@router.patch(
    "/{id}/resolve",
    response_model=AlertResponse,
    summary="Resolve or reopen an alert",
    description="Request body optional. Default: {\"resolved\": true}. Send {\"resolved\": false} to reopen.",
)
def patch_alert_resolve(
    id: int,
    payload: Optional[AlertResolveUpdate] = Body(default=None),
    db: Session = Depends(get_db),
):
    """Resolve alert (default) or set resolved=false to reopen. Body optional: {} means resolve."""
    if payload is None:
        payload = AlertResolveUpdate(resolved=True)
    a = update_alert_resolve(db, id, payload)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(a)
