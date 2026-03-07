"""
Passenger Intelligence API endpoints.

Handles:
- Stress score calculations
- High-stress passenger identification
- Stress reduction recommendations
- Flight stress summaries
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..services.passenger_intelligence import intelligence_engine
from ..models import PassengerStressMetric, Alert, PassengerJourneyState
from ..schemas import PassengerStressMetricResponse

router = APIRouter(prefix="/passenger-intelligence", tags=["passenger-intelligence"])


@router.get("")
def get_passenger_intelligence_overview(db: Session = Depends(get_db)):
    """Get passenger intelligence system overview."""
    try:
        from ..models import PassengerStressMetric
        # Get basic stats
        total_metrics = db.query(PassengerStressMetric).count()
        high_stress_count = db.query(PassengerStressMetric).filter(
            PassengerStressMetric.stress_level == "high"
        ).count()
        recent_metrics = db.query(PassengerStressMetric).order_by(
            PassengerStressMetric.created_at.desc()
        ).limit(5).all()
        
        return {
            "message": "Passenger Intelligence System Active",
            "total_stress_metrics": total_metrics,
            "high_stress_passengers": high_stress_count,
            "recent_metrics": [
                {
                    "passenger_reference": metric.passenger_reference,
                    "stress_level": metric.stress_level,
                    "stress_score": metric.stress_score,
                    "created_at": metric.created_at.isoformat()
                } for metric in recent_metrics
            ],
            "available_endpoints": {
                "stress_metrics": "/passenger-intelligence/stress-metrics",
                "high_stress": "/passenger-intelligence/high-stress-passengers",
                "recommendations": "/passenger-intelligence/recommendations"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/passengers/{passenger_reference}/stress/{flight_id}", response_model=PassengerStressMetricResponse)
def calculate_passenger_stress(passenger_reference: str, flight_id: int, db: Session = Depends(get_db)):
    """Calculate comprehensive stress score for a passenger."""
    try:
        stress_metric = intelligence_engine.calculate_passenger_stress(
            db=db,
            passenger_reference=passenger_reference,
            flight_id=flight_id
        )
        return PassengerStressMetricResponse.model_validate(stress_metric)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/passengers/high-stress")
def get_high_stress_passengers(
    flight_id: Optional[int] = None, 
    stress_threshold: float = 0.7,
    db: Session = Depends(get_db)
):
    """Get passengers with high stress scores."""
    try:
        passengers = intelligence_engine.get_high_stress_passengers(
            db=db,
            flight_id=flight_id,
            stress_threshold=stress_threshold
        )
        return [PassengerStressMetricResponse.model_validate(p) for p in passengers]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/alerts/stress")
def generate_stress_alerts(db: Session = Depends(get_db)):
    """Generate alerts for high-stress passengers."""
    try:
        alerts = intelligence_engine.generate_stress_alerts(db)
        # Create actual alert records
        created_alerts = []
        for alert_data in alerts:
            alert = Alert(
                alert_type=alert_data["alert_type"],
                severity=alert_data["severity"],
                source_module=alert_data["source_module"],
                message=alert_data["message"],
                related_entity_type=alert_data["related_entity_type"],
                related_entity_id=alert_data["related_entity_id"],
                created_at=alert_data["created_at"],
                uniqueness_key=alert_data["uniqueness_key"]
            )
            db.add(alert)
            created_alerts.append(alert)
        
        if created_alerts:
            db.commit()
        
        return {"alerts_created": len(created_alerts), "alert_data": alerts}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flights/{flight_id}/stress-summary")
def get_flight_stress_summary(flight_id: int, db: Session = Depends(get_db)):
    """Get stress summary for a specific flight."""
    try:
        summary = intelligence_engine.get_flight_stress_summary(db, flight_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/passengers/{passenger_reference}/recommendations/{flight_id}")
def recommend_stress_reduction(passenger_reference: str, flight_id: int, db: Session = Depends(get_db)):
    """Recommend actions to reduce passenger stress."""
    try:
        recommendations = intelligence_engine.recommend_stress_reduction(
            db=db,
            passenger_reference=passenger_reference,
            flight_id=flight_id
        )
        return {
            "passenger_reference": passenger_reference,
            "flight_id": flight_id,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stress-metrics")
def get_recent_stress_metrics(
    flight_id: Optional[int] = None,
    minutes_back: int = 60,
    db: Session = Depends(get_db)
):
    """Get recent stress metrics for analysis."""
    from datetime import timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_back)
    query = db.query(PassengerStressMetric).filter(
        PassengerStressMetric.calculated_at >= cutoff_time
    )
    
    if flight_id:
        query = query.filter(PassengerStressMetric.flight_id == flight_id)
    
    metrics = query.order_by(PassengerStressMetric.calculated_at.desc()).all()
    return [PassengerStressMetricResponse.model_validate(m) for m in metrics]


@router.get("/analytics/stress-distribution")
def get_stress_distribution_analytics(
    terminal: Optional[str] = None,
    minutes_back: int = 120,
    db: Session = Depends(get_db)
):
    """Get stress distribution analytics for airport or terminal."""
    from datetime import timedelta
    from sqlalchemy import func
    
    cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_back)
    
    # Join with journey states to get location info
    query = db.query(
        PassengerStressMetric.stress_level,
        func.count(PassengerStressMetric.id).label('count')
    ).join(PassengerJourneyState, 
           PassengerStressMetric.passenger_reference == PassengerJourneyState.passenger_reference).filter(
        PassengerStressMetric.calculated_at >= cutoff_time
    )
    
    if terminal:
        query = query.filter(PassengerJourneyState.current_location.like(f"{terminal}%"))
    
    results = query.group_by(PassengerStressMetric.stress_level).all()
    
    distribution = {level: 0 for level in ["low", "medium", "high", "critical"]}
    total_count = 0
    
    for stress_level, count in results:
        distribution[stress_level] = count
        total_count += count
    
    # Calculate percentages
    percentages = {}
    if total_count > 0:
        for level, count in distribution.items():
            percentages[level] = round((count / total_count) * 100, 1)
    
    return {
        "time_window_minutes": minutes_back,
        "terminal": terminal,
        "total_passengers": total_count,
        "stress_counts": distribution,
        "stress_percentages": percentages
    }
