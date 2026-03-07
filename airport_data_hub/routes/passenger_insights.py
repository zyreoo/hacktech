"""
Passenger Insights API endpoints.

Handles:
- Flight insights calculations
- Passenger flow analytics
- Gate arrival predictions
- Retail system insights
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.passenger_insights import insights_engine
from ..models import PassengerInsight

router = APIRouter(prefix="/passenger-insights", tags=["passenger-insights"])


@router.get("")
def get_passenger_insights_overview(db: Session = Depends(get_db)):
    """Get passenger insights system overview."""
    try:
        from ..models import PassengerInsight
        # Get basic stats
        total_insights = db.query(PassengerInsight).count()
        recent_insights = db.query(PassengerInsight).order_by(
            PassengerInsight.created_at.desc()
        ).limit(5).all()
        
        return {
            "message": "Passenger Insights System Active",
            "total_insights": total_insights,
            "recent_insights": [
                {
                    "insight_id": insight.insight_id,
                    "insight_type": insight.insight_type,
                    "passenger_reference": insight.passenger_reference,
                    "flight_id": insight.flight_id,
                    "created_at": insight.created_at.isoformat()
                } for insight in recent_insights
            ],
            "available_endpoints": {
                "insights": "/passenger-insights/insights",
                "analytics": "/passenger-insights/analytics",
                "trends": "/passenger-insights/trends"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flights/{flight_id}/insights")
def calculate_flight_insights(flight_id: int, db: Session = Depends(get_db)):
    """Calculate comprehensive insights for a specific flight."""
    try:
        insights = insights_engine.calculate_flight_insights(db, flight_id)
        return {
            "flight_id": flight_id,
            "insights": {
                "total_passengers": insights.total_passengers,
                "avg_stress_score": insights.avg_stress_score,
                "high_stress_count": insights.high_stress_count,
                "avg_check_in_to_security": insights.avg_check_in_to_security,
                "avg_security_to_gate": insights.avg_security_to_gate,
                "avg_dwell_time_post_security": insights.avg_dwell_time_post_security,
                "on_time_gate_arrival_rate": insights.on_time_gate_arrival_rate,
                "late_gate_arrival_count": insights.late_gate_arrival_count,
                "total_retail_opportunity_minutes": insights.total_retail_opportunity_minutes,
                "retail_ready_passengers": insights.retail_ready_passengers,
                "calculated_at": insights.calculated_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flights/{flight_id}/insights")
def get_flight_insights(flight_id: int, db: Session = Depends(get_db)):
    """Get existing insights for a flight."""
    insights = db.query(PassengerInsight).filter(
        PassengerInsight.flight_id == flight_id
    ).order_by(PassengerInsight.calculated_at.desc()).first()
    
    if not insights:
        raise HTTPException(status_code=404, detail="Insights not found for this flight")
    
    return {
        "flight_id": flight_id,
        "insights": {
            "total_passengers": insights.total_passengers,
            "avg_stress_score": insights.avg_stress_score,
            "high_stress_count": insights.high_stress_count,
            "avg_check_in_to_security": insights.avg_check_in_to_security,
            "avg_security_to_gate": insights.avg_security_to_gate,
            "avg_dwell_time_post_security": insights.avg_dwell_time_post_security,
            "on_time_gate_arrival_rate": insights.on_time_gate_arrival_rate,
            "late_gate_arrival_count": insights.late_gate_arrival_count,
            "total_retail_opportunity_minutes": insights.total_retail_opportunity_minutes,
            "retail_ready_passengers": insights.retail_ready_passengers,
            "calculated_at": insights.calculated_at.isoformat()
        }
    }


@router.get("/analytics/passenger-flow")
def get_passenger_flow_analytics(time_window_hours: int = 24, db: Session = Depends(get_db)):
    """Get overall passenger flow analytics for the airport."""
    try:
        analytics = insights_engine.get_passenger_flow_analytics(db, time_window_hours)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flights/{flight_id}/gate-arrival-predictions")
def predict_gate_arrival_times(flight_id: int, db: Session = Depends(get_db)):
    """Predict gate arrival times for passengers on a flight."""
    try:
        predictions = insights_engine.predict_gate_arrival_times(db, flight_id)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/retail-insights")
def get_retail_system_insights(terminal: Optional[str] = None, db: Session = Depends(get_db)):
    """Provide insights for retail systems and passenger flow management."""
    try:
        insights = insights_engine.get_retail_system_insights(db, terminal)
        return insights
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/journey-performance")
def get_journey_performance_analytics(
    terminal: Optional[str] = None,
    hours_back: int = 24,
    db: Session = Depends(get_db)
):
    """Get journey performance analytics for airport or terminal."""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    # Get insights for recent flights
    query = db.query(PassengerInsight).filter(
        PassengerInsight.calculated_at >= start_time
    )
    
    insights_list = query.all()
    
    if not insights_list:
        return {
            "time_window_hours": hours_back,
            "terminal": terminal,
            "total_flights": 0,
            "performance_metrics": {}
        }
    
    # Calculate aggregate performance metrics
    total_flights = len(insights_list)
    total_passengers = sum(ins.total_passengers for ins in insights_list)
    avg_stress = sum(ins.avg_stress_score or 0 for ins in insights_list) / total_flights
    avg_on_time_rate = sum(ins.on_time_gate_arrival_rate or 0 for ins in insights_list) / total_flights
    
    # Journey timing averages
    avg_check_in_security = sum(ins.avg_check_in_to_security or 0 for ins in insights_list) / total_flights
    avg_security_gate = sum(ins.avg_security_to_gate or 0 for ins in insights_list) / total_flights
    avg_dwell_post_security = sum(ins.avg_dwell_time_post_security or 0 for ins in insights_list) / total_flights
    
    # Retail potential
    total_retail_minutes = sum(ins.total_retail_opportunity_minutes or 0 for ins in insights_list)
    total_retail_ready = sum(ins.retail_ready_passengers or 0 for ins in insights_list)
    
    performance_metrics = {
        "passenger_metrics": {
            "total_passengers": total_passengers,
            "avg_passengers_per_flight": round(total_passengers / total_flights, 1),
            "avg_stress_score": round(avg_stress, 3),
            "high_stress_rate": round(sum(ins.high_stress_count or 0 for ins in insights_list) / total_passengers * 100, 1)
        },
        "timing_metrics": {
            "avg_check_in_to_security_minutes": round(avg_check_in_security, 1),
            "avg_security_to_gate_minutes": round(avg_security_gate, 1),
            "avg_dwell_post_security_minutes": round(avg_dwell_post_security, 1),
            "avg_on_time_gate_arrival_rate": round(avg_on_time_rate, 1)
        },
        "retail_metrics": {
            "total_retail_opportunity_minutes": total_retail_minutes,
            "avg_retail_opportunity_per_flight": round(total_retail_minutes / total_flights, 1),
            "total_retail_ready_passengers": total_retail_ready,
            "retail_readiness_rate": round(total_retail_ready / total_passengers * 100, 1) if total_passengers > 0 else 0
        }
    }
    
    return {
        "time_window_hours": hours_back,
        "terminal": terminal,
        "total_flights": total_flights,
        "performance_metrics": performance_metrics
    }


@router.get("/analytics/terminal-comparison")
def get_terminal_performance_comparison(hours_back: int = 24, db: Session = Depends(get_db)):
    """Compare performance across terminals."""
    from datetime import timedelta
    
    start_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    # Get insights for recent flights
    insights_list = db.query(PassengerInsight).filter(
        PassengerInsight.calculated_at >= start_time
    ).all()
    
    if not insights_list:
        return {
            "time_window_hours": hours_back,
            "terminal_comparison": {},
            "summary": "No data available for the specified time period"
        }
    
    # Group by terminal (need to extract from flight data)
    terminal_data = {}
    
    for insight in insights_list:
        # This would need to be enhanced to properly group by terminal
        # For now, we'll create a simple summary
        terminal_key = "all_terminals"
        
        if terminal_key not in terminal_data:
            terminal_data[terminal_key] = {
                "flights": 0,
                "total_passengers": 0,
                "avg_stress_score": 0,
                "on_time_gate_arrival_rate": 0,
                "retail_opportunity_minutes": 0
            }
        
        data = terminal_data[terminal_key]
        data["flights"] += 1
        data["total_passengers"] += insight.total_passengers
        data["avg_stress_score"] += insight.avg_stress_score or 0
        data["on_time_gate_arrival_rate"] += insight.on_time_gate_arrival_rate or 0
        data["retail_opportunity_minutes"] += insight.total_retail_opportunity_minutes or 0
    
    # Calculate averages
    for terminal, data in terminal_data.items():
        flights = data["flights"]
        data["avg_stress_score"] = round(data["avg_stress_score"] / flights, 3)
        data["on_time_gate_arrival_rate"] = round(data["on_time_gate_arrival_rate"] / flights, 1)
        data["avg_passengers_per_flight"] = round(data["total_passengers"] / flights, 1)
        data["avg_retail_opportunity_per_flight"] = round(data["retail_opportunity_minutes"] / flights, 1)
    
    return {
        "time_window_hours": hours_back,
        "terminal_comparison": terminal_data
    }


@router.get("/insights/recent")
def get_recent_insights(
    flight_id: Optional[int] = None,
    hours_back: int = 6,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get recent flight insights."""
    from datetime import timedelta
    
    start_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    query = db.query(PassengerInsight).filter(
        PassengerInsight.calculated_at >= start_time
    )
    
    if flight_id:
        query = query.filter(PassengerInsight.flight_id == flight_id)
    
    insights = query.order_by(PassengerInsight.calculated_at.desc()).limit(limit).all()
    
    return {
        "insights": [
            {
                "flight_id": insight.flight_id,
                "flight_date": insight.flight_date.isoformat(),
                "total_passengers": insight.total_passengers,
                "avg_stress_score": insight.avg_stress_score,
                "on_time_gate_arrival_rate": insight.on_time_gate_arrival_rate,
                "total_retail_opportunity_minutes": insight.total_retail_opportunity_minutes,
                "calculated_at": insight.calculated_at.isoformat()
            }
            for insight in insights
        ]
    }
