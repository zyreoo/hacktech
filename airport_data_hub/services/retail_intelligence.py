"""
Retail Intelligence Service.

Computes passenger free-time windows, identifies retail opportunities,
and generates recommendations for airport vendors.
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from ..models import (
    RetailOpportunity, PassengerJourneyState, Flight, 
    PassengerFlow, PassengerStressMetric,
    QueueState, QueueEvent  # Add new passenger flow models
)
from ..database import SessionLocal
from ..services.queue_state_engine import queue_state_engine  # Import queue state engine


class RetailIntelligenceEngine:
    """Engine for retail intelligence and opportunity identification."""
    
    def __init__(self):
        # Retail outlet locations by terminal
        self.retail_outlets = {
            "T1": {
                "food": [{"id": "T1_F1", "name": "Starbucks", "location": "post_security", "avg_purchase_time": 5},
                        {"id": "T1_F2", "name": "McDonald's", "location": "post_security", "avg_purchase_time": 8},
                        {"id": "T1_F3", "name": "Prezzo", "location": "gate_area", "avg_purchase_time": 25}],
                "duty_free": [{"id": "T1_DF1", "name": "World Duty Free", "location": "post_security", "avg_purchase_time": 15}],
                "retail": [{"id": "T1_R1", "name": "WHSmith", "location": "post_security", "avg_purchase_time": 10},
                          {"id": "T1_R2", "name": "Boots", "location": "post_security", "avg_purchase_time": 12}],
                "lounge": [{"id": "T1_L1", "name": "Aspire Lounge", "location": "gate_area", "avg_purchase_time": 120}]
            },
            "T2": {
                "food": [{"id": "T2_F1", "name": "Caffe Nero", "location": "post_security", "avg_purchase_time": 6},
                        {"id": "T2_F2", "name": "Wetherspoons", "location": "gate_area", "avg_purchase_time": 30}],
                "duty_free": [{"id": "T2_DF1", "name": "JD Wetherspoon", "location": "post_security", "avg_purchase_time": 20}],
                "retail": [{"id": "T2_R1", "name": "Superdrug", "location": "post_security", "avg_purchase_time": 8}],
                "lounge": [{"id": "T2_L1", "name": "Escape Lounge", "location": "gate_area", "avg_purchase_time": 90}]
            },
            "T3": {
                "food": [{"id": "T3_F1", "name": "Pret A Manger", "location": "post_security", "avg_purchase_time": 7},
                        {"id": "T3_F2", "name": "Giraffe", "location": "gate_area", "avg_purchase_time": 35}],
                "duty_free": [{"id": "T3_DF1", "name": "Tax Free", "location": "post_security", "avg_purchase_time": 18}],
                "retail": [{"id": "T3_R1", "name": "Accessorize", "location": "post_security", "avg_purchase_time": 15}],
                "lounge": [{"id": "T3_L1", "name": "No1 Lounge", "location": "gate_area", "avg_purchase_time": 100}]
            },
            "T4": {
                "food": [{"id": "T4_F1", "name": "Costa Coffee", "location": "post_security", "avg_purchase_time": 6},
                        {"id": "T4_F2", "name": "Wagamama", "location": "gate_area", "avg_purchase_time": 40}],
                "duty_free": [{"id": "T4_DF1", "name": "Duty Free", "location": "post_security", "avg_purchase_time": 16}],
                "retail": [{"id": "T4_R1", "name": "Clarks", "location": "post_security", "avg_purchase_time": 20}],
                "lounge": [{"id": "T4_L1", "name": "Clubrooms", "location": "gate_area", "avg_purchase_time": 110}]
            },
            "T5": {
                "food": [{"id": "T5_F1", "name": "Eat", "location": "post_security", "avg_purchase_time": 8},
                        {"id": "T5_F2", "name": "Carluccio's", "location": "gate_area", "avg_purchase_time": 32}],
                "duty_free": [{"id": "T5_DF1", "name": "Luxury Duty Free", "location": "post_security", "avg_purchase_time": 25}],
                "retail": [{"id": "T5_R1", "name": "Harrods", "location": "post_security", "avg_purchase_time": 22},
                          {"id": "T5_R2", "name": "Tiffany", "location": "gate_area", "avg_purchase_time": 30}],
                "lounge": [{"id": "T5_L1", "name": "Concorde Room", "location": "gate_area", "avg_purchase_time": 150}]
            }
        }
        
        # Walking times to retail areas (in minutes)
        self.walking_times_to_retail = {
            "security_to_retail": 5,
            "gate_to_retail": 3,
            "retail_to_gate": 5
        }
        
        # Minimum time needed for retail activities
        self.min_retail_time = {
            "food": 10,
            "duty_free": 15,
            "retail": 8,
            "lounge": 60
        }
    
    def compute_passenger_opportunity_windows(self, db: Session, flight_id: int) -> List[RetailOpportunity]:
        """Compute retail opportunity windows for all passengers on a flight."""
        
        # Get all passengers in relevant states for this flight
        passengers = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.flight_id == flight_id,
            PassengerJourneyState.current_state.in_(["post_security", "gate", "retail"])
        ).all()
        
        opportunities = []
        
        for passenger in passengers:
            opportunity = self._calculate_individual_opportunity(db, passenger)
            if opportunity:
                opportunities.append(opportunity)
        
        return opportunities
    
    def _calculate_individual_opportunity(self, db: Session, passenger: PassengerJourneyState) -> Optional[RetailOpportunity]:
        """Calculate retail opportunity window for individual passenger."""
        
        # Get flight information
        flight = db.query(Flight).filter(Flight.id == passenger.flight_id).first()
        if not flight or not flight.scheduled_time:
            return None
        
        now = datetime.utcnow()
        
        # Determine opportunity window based on passenger state
        if passenger.current_state == "post_security":
            return self._calculate_post_security_opportunity(passenger, flight, now)
        elif passenger.current_state == "gate":
            return self._calculate_gate_opportunity(passenger, flight, now)
        elif passenger.current_state == "retail":
            return self._calculate_retail_opportunity(passenger, flight, now)
        
        return None
    
    def _calculate_post_security_opportunity(self, passenger: PassengerJourneyState, 
                                           flight: Flight, now: datetime) -> RetailOpportunity:
        """Calculate opportunity for passenger in post-security area."""
        
        # Time until boarding
        if not passenger.estimated_boarding_time:
            return None
        
        time_to_boarding = (passenger.estimated_boarding_time - now).total_seconds() / 60
        
        # Need at least 15 minutes for meaningful retail activity
        if time_to_boarding < 15:
            return None
        
        # Opportunity window: now until 10 minutes before boarding
        opportunity_start = now
        opportunity_end = passenger.estimated_boarding_time - timedelta(minutes=10)
        duration = int((opportunity_end - opportunity_start).total_seconds() / 60)
        
        # Get passenger stress level
        stress_level = self._get_passenger_stress_level(passenger.passenger_reference, passenger.flight_id)
        time_pressure = "high" if time_to_boarding < 45 else "medium" if time_to_boarding < 90 else "low"
        
        # Calculate retail readiness score
        retail_readiness = self._calculate_retail_readiness(
            duration, stress_level, time_pressure, passenger.current_state
        )
        
        # Get terminal zone
        terminal_zone = self._extract_terminal_zone(passenger.current_location)
        
        # Get nearest retail outlets
        nearest_outlets = self._get_nearest_outlets(terminal_zone, "post_security")
        
        # Recommend categories based on time available and stress
        recommended_categories = self._recommend_categories(duration, stress_level, time_pressure)
        
        return RetailOpportunity(
            passenger_reference=passenger.passenger_reference,
            flight_id=passenger.flight_id,
            opportunity_start=opportunity_start,
            opportunity_end=opportunity_end,
            duration_minutes=duration,
            terminal_zone=terminal_zone,
            current_location=passenger.current_location,
            nearest_retail_outlets=json.dumps(nearest_outlets),
            stress_level=stress_level,
            time_pressure=time_pressure,
            retail_readiness_score=retail_readiness,
            recommended_categories=json.dumps(recommended_categories),
            created_at=now,
            expires_at=opportunity_end
        )
    
    def _calculate_gate_opportunity(self, passenger: PassengerJourneyState, 
                                 flight: Flight, now: datetime) -> Optional[RetailOpportunity]:
        """Calculate opportunity for passenger at gate area."""
        
        # Time until boarding
        if not passenger.estimated_boarding_time:
            return None
        
        time_to_boarding = (passenger.estimated_boarding_time - now).total_seconds() / 60
        
        # Limited opportunities at gate - only if boarding is more than 20 minutes away
        if time_to_boarding < 20:
            return None
        
        # Small opportunity window for quick purchases
        opportunity_start = now
        opportunity_end = passenger.estimated_boarding_time - timedelta(minutes=15)
        duration = int((opportunity_end - opportunity_start).total_seconds() / 60)
        
        # Get passenger stress level
        stress_level = self._get_passenger_stress_level(passenger.passenger_reference, passenger.flight_id)
        time_pressure = "high" if time_to_boarding < 30 else "medium"
        
        # Lower retail readiness at gate due to time pressure
        retail_readiness = self._calculate_retail_readiness(
            duration, stress_level, time_pressure, passenger.current_state
        ) * 0.7  # Reduce readiness at gate
        
        # Get terminal zone
        terminal_zone = self._extract_terminal_zone(passenger.current_location)
        
        # Get nearest retail outlets (gate area)
        nearest_outlets = self._get_nearest_outlets(terminal_zone, "gate_area")
        
        # Recommend quick categories only
        recommended_categories = self._recommend_categories(duration, stress_level, time_pressure)
        # Filter to quick items only
        recommended_categories = [cat for cat in recommended_categories if cat in ["retail", "food"]]
        
        return RetailOpportunity(
            passenger_reference=passenger.passenger_reference,
            flight_id=passenger.flight_id,
            opportunity_start=opportunity_start,
            opportunity_end=opportunity_end,
            duration_minutes=duration,
            terminal_zone=terminal_zone,
            current_location=passenger.current_location,
            nearest_retail_outlets=json.dumps(nearest_outlets),
            stress_level=stress_level,
            time_pressure=time_pressure,
            retail_readiness_score=retail_readiness,
            recommended_categories=json.dumps(recommended_categories),
            created_at=now,
            expires_at=opportunity_end
        )
    
    def _calculate_retail_opportunity(self, passenger: PassengerJourneyState, 
                                    flight: Flight, now: datetime) -> Optional[RetailOpportunity]:
        """Calculate opportunity for passenger already in retail area."""
        
        # Time until boarding
        if not passenger.estimated_boarding_time:
            return None
        
        time_to_boarding = (passenger.estimated_boarding_time - now).total_seconds() / 60
        
        # Already in retail - calculate remaining time
        if time_to_boarding < 10:
            return None  # Not enough time
        
        opportunity_start = now
        opportunity_end = passenger.estimated_boarding_time - timedelta(minutes=10)
        duration = int((opportunity_end - opportunity_start).total_seconds() / 60)
        
        # Get passenger stress level
        stress_level = self._get_passenger_stress_level(passenger.passenger_reference, passenger.flight_id)
        time_pressure = "high" if time_to_boarding < 30 else "medium"
        
        # High retail readiness - already engaged
        retail_readiness = self._calculate_retail_readiness(
            duration, stress_level, time_pressure, passenger.current_state
        ) * 1.2  # Boost for already engaged passengers
        
        # Get terminal zone
        terminal_zone = self._extract_terminal_zone(passenger.current_location)
        
        # Get nearest retail outlets
        nearest_outlets = self._get_nearest_outlets(terminal_zone, "gate_area")
        
        # All categories available
        recommended_categories = self._recommend_categories(duration, stress_level, time_pressure)
        
        return RetailOpportunity(
            passenger_reference=passenger.passenger_reference,
            flight_id=passenger.flight_id,
            opportunity_start=opportunity_start,
            opportunity_end=opportunity_end,
            duration_minutes=duration,
            terminal_zone=terminal_zone,
            current_location=passenger.current_location,
            nearest_retail_outlets=json.dumps(nearest_outlets),
            stress_level=stress_level,
            time_pressure=time_pressure,
            retail_readiness_score=retail_readiness,
            recommended_categories=json.dumps(recommended_categories),
            created_at=now,
            expires_at=opportunity_end
        )
    
    def _get_passenger_stress_level(self, passenger_reference: str, flight_id: int) -> str:
        """Get current stress level for passenger."""
        # This would typically query the stress metrics
        # For now, return a reasonable default
        return "medium"
    
    def _extract_terminal_zone(self, location: Optional[str]) -> str:
        """Extract terminal zone from location string."""
        if not location:
            return "T1"
        
        # Extract terminal from location strings like "T1_security", "T2_gate_A12"
        for terminal in ["T1", "T2", "T3", "T4", "T5"]:
            if terminal in location:
                return terminal
        
        return "T1"  # Default
    
    def _get_nearest_outlets(self, terminal: str, area: str) -> List[Dict]:
        """Get nearest retail outlets for terminal and area."""
        outlets = []
        
        if terminal in self.retail_outlets:
            for category, stores in self.retail_outlets[terminal].items():
                for store in stores:
                    if store["location"] == area or area == "post_security":
                        outlets.append({
                            "id": store["id"],
                            "name": store["name"],
                            "category": category,
                            "avg_purchase_time": store["avg_purchase_time"],
                            "walking_distance": self._calculate_walking_distance(area, store["location"])
                        })
        
        # Sort by walking distance + purchase time
        outlets.sort(key=lambda x: x["walking_distance"] + x["avg_purchase_time"])
        return outlets[:5]  # Return top 5 nearest
    
    def _calculate_walking_distance(self, from_area: str, to_area: str) -> int:
        """Calculate walking distance between areas in minutes."""
        if from_area == to_area:
            return 0
        
        # Simplified walking time matrix
        walking_matrix = {
            ("post_security", "post_security"): 0,
            ("post_security", "gate_area"): 8,
            ("gate_area", "post_security"): 8,
            ("gate_area", "gate_area"): 0
        }
        
        return walking_matrix.get((from_area, to_area), 5)
    
    def _recommend_categories(self, duration: int, stress_level: str, time_pressure: str) -> List[str]:
        """Recommend retail categories based on passenger context."""
        categories = []
        
        # Base recommendations on time available
        if duration >= 60:
            categories.extend(["lounge", "duty_free", "food", "retail"])
        elif duration >= 30:
            categories.extend(["duty_free", "food", "retail"])
        elif duration >= 15:
            categories.extend(["food", "retail"])
        elif duration >= 8:
            categories.extend(["retail"])
        
        # Adjust based on stress level
        if stress_level == "high":
            # Stressed passengers prefer quick, familiar options
            if "food" in categories:
                categories = ["food"] + [c for c in categories if c != "food"]
            if "lounge" in categories:
                categories.remove("lounge")  # Too stressed for lounge
        
        elif stress_level == "low" and time_pressure == "low":
            # Relaxed passengers with time can enjoy premium options
            if "lounge" not in categories and duration >= 45:
                categories.append("lounge")
        
        return categories
    
    def _calculate_retail_readiness(self, duration: int, stress_level: str, 
                                 time_pressure: str, current_state: str) -> float:
        """Calculate retail readiness score (0-1)."""
        
        # Base score from time available
        time_score = min(duration / 60.0, 1.0)  # 60+ minutes = 1.0
        
        # Adjust for stress level
        stress_multiplier = {
            "low": 1.2,
            "medium": 1.0,
            "high": 0.6,
            "critical": 0.3
        }
        
        # Adjust for time pressure
        pressure_multiplier = {
            "low": 1.1,
            "medium": 1.0,
            "high": 0.7
        }
        
        # Adjust for current state
        state_multiplier = {
            "post_security": 1.0,
            "gate": 0.7,
            "retail": 1.3
        }
        
        readiness = (time_score * 
                   stress_multiplier.get(stress_level, 1.0) *
                   pressure_multiplier.get(time_pressure, 1.0) *
                   state_multiplier.get(current_state, 1.0))
        
        return min(readiness, 1.0)
    
    def generate_retail_opportunity_feed(self, db: Session, terminal: Optional[str] = None) -> Dict:
        """Generate retail opportunity feed for vendors."""
        
        # Get active opportunities
        now = datetime.utcnow()
        query = db.query(RetailOpportunity).filter(
            RetailOpportunity.expires_at > now
        )
        
        if terminal:
            query = query.filter(RetailOpportunity.terminal_zone == terminal)
        
        opportunities = query.order_by(RetailOpportunity.retail_readiness_score.desc()).all()
        
        # Aggregate by terminal and category
        feed = {
            "generated_at": now.isoformat(),
            "total_opportunities": len(opportunities),
            "terminals": {},
            "high_value_opportunities": [],
            "category_breakdown": {}
        }
        
        for opp in opportunities:
            terminal = opp.terminal_zone
            if terminal not in feed["terminals"]:
                feed["terminals"][terminal] = {
                    "opportunity_count": 0,
                    "total_readiness_score": 0,
                    "categories": {},
                    "avg_duration_minutes": 0
                }
            
            # Update terminal stats
            term_data = feed["terminals"][terminal]
            term_data["opportunity_count"] += 1
            term_data["total_readiness_score"] += opp.retail_readiness_score
            term_data["avg_duration_minutes"] += opp.duration_minutes
            
            # Process recommended categories
            categories = json.loads(opp.recommended_categories) if opp.recommended_categories else []
            for category in categories:
                if category not in term_data["categories"]:
                    term_data["categories"][category] = 0
                term_data["categories"][category] += 1
                
                if category not in feed["category_breakdown"]:
                    feed["category_breakdown"][category] = 0
                feed["category_breakdown"][category] += 1
            
            # High value opportunities (readiness > 0.8 and duration > 20 mins)
            if opp.retail_readiness_score > 0.8 and opp.duration_minutes > 20:
                feed["high_value_opportunities"].append({
                    "passenger_reference": opp.passenger_reference,
                    "terminal": terminal,
                    "duration_minutes": opp.duration_minutes,
                    "readiness_score": opp.retail_readiness_score,
                    "recommended_categories": categories,
                    "stress_level": opp.stress_level,
                    "time_pressure": opp.time_pressure
                })
        
        # Calculate averages
        for term_data in feed["terminals"].values():
            if term_data["opportunity_count"] > 0:
                term_data["avg_readiness_score"] = term_data["total_readiness_score"] / term_data["opportunity_count"]
                term_data["avg_duration_minutes"] = term_data["avg_duration_minutes"] / term_data["opportunity_count"]
        
        return feed
    
    def get_terminal_promotions(self, db: Session, terminal: str) -> List[Dict]:
        """Generate recommended promotions per terminal based on current opportunities."""
        
        # Get current opportunities for this terminal
        now = datetime.utcnow()
        opportunities = db.query(RetailOpportunity).filter(
            RetailOpportunity.terminal_zone == terminal,
            RetailOpportunity.expires_at > now
        ).all()
        
        if not opportunities:
            return []
        
        # Analyze opportunity patterns
        category_counts = {}
        stress_levels = {"low": 0, "medium": 0, "high": 0}
        time_pressures = {"low": 0, "medium": 0, "high": 0}
        
        for opp in opportunities:
            categories = json.loads(opp.recommended_categories) if opp.recommended_categories else []
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
            
            stress_levels[opp.stress_level] = stress_levels.get(opp.stress_level, 0) + 1
            time_pressures[opp.time_pressure] = time_pressures.get(opp.time_pressure, 0) + 1
        
        # Generate promotions based on patterns
        promotions = []
        
        # High-demand categories
        total_opportunities = len(opportunities)
        for category, count in category_counts.items():
            if count / total_opportunities > 0.4:  # >40% demand
                promotions.append({
                    "category": category,
                    "type": "high_demand",
                    "recommendation": f"Increase {category} staffing and inventory",
                    "demand_percentage": round((count / total_opportunities) * 100, 1)
                })
        
        # Stress-based promotions
        if stress_levels["high"] / total_opportunities > 0.3:  # >30% high stress
            promotions.append({
                "category": "stress_relief",
                "type": "customer_experience",
                "recommendation": "Offer express checkout and priority service options",
                "affected_passengers": round((stress_levels["high"] / total_opportunities) * 100, 1)
            })
        
        # Time-based promotions
        if time_pressures["high"] / total_opportunities > 0.4:  # >40% high time pressure
            promotions.append({
                "category": "quick_service",
                "type": "operational",
                "recommendation": "Promote grab-and-go items and mobile ordering",
                "affected_passengers": round((time_pressures["high"] / total_opportunities) * 100, 1)
            })
        
        return promotions


# Global instance
retail_intelligence = RetailIntelligenceEngine()
