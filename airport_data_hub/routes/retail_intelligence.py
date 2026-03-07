"""
Retail Intelligence API endpoints.

Handles:
- Retail opportunity windows
- Vendor opportunity feeds
- Terminal promotions
- Retail analytics
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.retail_intelligence import retail_intelligence
from ..models import RetailOpportunity

router = APIRouter(prefix="/retail-intelligence", tags=["retail-intelligence"])


@router.get("")
def get_retail_intelligence_overview(db: Session = Depends(get_db)):
    """Get retail intelligence system overview."""
    try:
        from ..models import RetailOpportunity
        # Get basic stats
        total_opportunities = db.query(RetailOpportunity).count()
        active_opportunities = db.query(RetailOpportunity).filter(
            RetailOpportunity.status == "active"
        ).count()
        recent_opportunities = db.query(RetailOpportunity).order_by(
            RetailOpportunity.created_at.desc()
        ).limit(5).all()
        
        return {
            "message": "Retail Intelligence System Active",
            "total_opportunities": total_opportunities,
            "active_opportunities": active_opportunities,
            "recent_opportunities": [
                {
                    "opportunity_id": opp.opportunity_id,
                    "passenger_reference": opp.passenger_reference,
                    "retail_category": opp.retail_category,
                    "potential_value": opp.potential_value,
                    "status": opp.status,
                    "created_at": opp.created_at.isoformat()
                } for opp in recent_opportunities
            ],
            "available_endpoints": {
                "opportunities": "/retail-intelligence/opportunities",
                "recommendations": "/retail-intelligence/recommendations",
                "analytics": "/retail-intelligence/analytics"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flights/{flight_id}/opportunities")
def compute_flight_opportunities(flight_id: int, db: Session = Depends(get_db)):
    """Compute retail opportunity windows for all passengers on a flight."""
    try:
        opportunities = retail_intelligence.compute_passenger_opportunity_windows(db, flight_id)
        return {
            "flight_id": flight_id,
            "opportunities_count": len(opportunities),
            "opportunities": [
                {
                    "passenger_reference": opp.passenger_reference,
                    "duration_minutes": opp.duration_minutes,
                    "retail_readiness_score": opp.retail_readiness_score,
                    "recommended_categories": eval(opp.recommended_categories) if opp.recommended_categories else [],
                    "stress_level": opp.stress_level,
                    "time_pressure": opp.time_pressure,
                    "terminal_zone": opp.terminal_zone
                }
                for opp in opportunities
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/opportunities/feed")
def get_retail_opportunity_feed(terminal: Optional[str] = None, db: Session = Depends(get_db)):
    """Generate retail opportunity feed for vendors."""
    try:
        feed = retail_intelligence.generate_retail_opportunity_feed(db, terminal)
        return feed
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/terminals/{terminal}/promotions")
def get_terminal_promotions(terminal: str, db: Session = Depends(get_db)):
    """Generate recommended promotions per terminal based on current opportunities."""
    try:
        promotions = retail_intelligence.get_terminal_promotions(db, terminal)
        return {
            "terminal": terminal,
            "generated_at": datetime.utcnow().isoformat(),
            "promotions": promotions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/passengers/{passenger_reference}/opportunities")
def get_passenger_opportunities(passenger_reference: str, db: Session = Depends(get_db)):
    """Get current retail opportunities for a specific passenger."""
    now = datetime.utcnow()
    opportunities = db.query(RetailOpportunity).filter(
        RetailOpportunity.passenger_reference == passenger_reference,
        RetailOpportunity.expires_at > now
    ).order_by(RetailOpportunity.retail_readiness_score.desc()).all()
    
    return {
        "passenger_reference": passenger_reference,
        "active_opportunities": [
            {
                "flight_id": opp.flight_id,
                "duration_minutes": opp.duration_minutes,
                "opportunity_start": opp.opportunity_start.isoformat(),
                "opportunity_end": opp.opportunity_end.isoformat(),
                "retail_readiness_score": opp.retail_readiness_score,
                "recommended_categories": eval(opp.recommended_categories) if opp.recommended_categories else [],
                "terminal_zone": opp.terminal_zone,
                "nearest_outlets": eval(opp.nearest_retail_outlets) if opp.nearest_retail_outlets else []
            }
            for opp in opportunities
        ]
    }


@router.get("/analytics/opportunity-summary")
def get_opportunity_summary_analytics(
    terminal: Optional[str] = None,
    minutes_ahead: int = 120,
    db: Session = Depends(get_db)
):
    """Get opportunity summary analytics for upcoming period."""
    from datetime import timedelta
    
    now = datetime.utcnow()
    future_cutoff = now + timedelta(minutes=minutes_ahead)
    
    query = db.query(RetailOpportunity).filter(
        RetailOpportunity.opportunity_start <= future_cutoff,
        RetailOpportunity.expires_at > now
    )
    
    if terminal:
        query = query.filter(RetailOpportunity.terminal_zone == terminal)
    
    opportunities = query.all()
    
    if not opportunities:
        return {
            "time_window_minutes": minutes_ahead,
            "terminal": terminal,
            "total_opportunities": 0,
            "total_opportunity_minutes": 0,
            "readiness_distribution": {},
            "category_distribution": {}
        }
    
    # Calculate analytics
    total_opportunity_minutes = sum(opp.duration_minutes for opp in opportunities)
    
    # Readiness distribution
    readiness_ranges = {"low": 0, "medium": 0, "high": 0}
    category_counts = {}
    terminal_counts = {}
    
    for opp in opportunities:
        # Readiness distribution
        if opp.retail_readiness_score < 0.4:
            readiness_ranges["low"] += 1
        elif opp.retail_readiness_score < 0.7:
            readiness_ranges["medium"] += 1
        else:
            readiness_ranges["high"] += 1
        
        # Category distribution
        categories = eval(opp.recommended_categories) if opp.recommended_categories else []
        for category in categories:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Terminal distribution
        terminal_counts[opp.terminal_zone] = terminal_counts.get(opp.terminal_zone, 0) + 1
    
    return {
        "time_window_minutes": minutes_ahead,
        "terminal": terminal,
        "total_opportunities": len(opportunities),
        "total_opportunity_minutes": total_opportunity_minutes,
        "avg_opportunity_duration": round(total_opportunity_minutes / len(opportunities), 1),
        "readiness_distribution": readiness_ranges,
        "category_distribution": category_counts,
        "terminal_distribution": terminal_counts
    }


@router.get("/analytics/retail-potential")
def get_retail_potential_analytics(
    terminal: Optional[str] = None,
    hours_back: int = 24,
    db: Session = Depends(get_db)
):
    """Get retail potential analytics for recent period."""
    from datetime import timedelta
    
    start_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    query = db.query(RetailOpportunity).filter(
        RetailOpportunity.created_at >= start_time
    )
    
    if terminal:
        query = query.filter(RetailOpportunity.terminal_zone == terminal)
    
    opportunities = query.all()
    
    if not opportunities:
        return {
            "time_window_hours": hours_back,
            "terminal": terminal,
            "total_passengers": 0,
            "potential_revenue_minutes": 0,
            "high_potential_passengers": 0,
            "conversion_potential": 0
        }
    
    # Calculate potential metrics
    total_passengers = len(set(opp.passenger_reference for opp in opportunities))
    high_potential = sum(1 for opp in opportunities if opp.retail_readiness_score > 0.7)
    total_potential_minutes = sum(opp.duration_minutes for opp in opportunities)
    
    # Estimate conversion potential (based on readiness scores)
    conversion_potential = sum(opp.retail_readiness_score for opp in opportunities)
    
    return {
        "time_window_hours": hours_back,
        "terminal": terminal,
        "total_passengers": total_passengers,
        "total_opportunities": len(opportunities),
        "potential_revenue_minutes": total_potential_minutes,
        "high_potential_passengers": high_potential,
        "conversion_potential_score": round(conversion_potential, 2),
        "avg_readiness_score": round(conversion_potential / len(opportunities), 3) if opportunities else 0
    }


@router.delete("/opportunities/cleanup")
def cleanup_expired_opportunities(db: Session = Depends(get_db)):
    """Clean up expired retail opportunities."""
    now = datetime.utcnow()
    expired_count = db.query(RetailOpportunity).filter(
        RetailOpportunity.expires_at <= now
    ).count()
    
    db.query(RetailOpportunity).filter(
        RetailOpportunity.expires_at <= now
    ).delete()
    
    db.commit()
    
    return {
        "expired_opportunities_removed": expired_count,
        "cleanup_timestamp": now.isoformat()
    }
