"""
Passenger Experience Intelligence Service.

Calculates passenger stress scores and provides insights for:
- High-stress passenger identification
- Journey experience optimization
- Alert triggering for passenger assistance
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from ..models import (
    PassengerJourneyState, PassengerStressMetric, Flight, 
    PassengerFlow, Alert,
    QueueState, QueueEvent  # Add new passenger flow models
)
from ..database import SessionLocal
from ..services.queue_state_engine import queue_state_engine  # Import queue state engine


class PassengerIntelligenceEngine:
    """Engine for calculating passenger stress and experience metrics."""
    
    def __init__(self):
        self.stress_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.9
        }
        
        # Walking distances between airport zones (in minutes)
        self.walking_times = {
            ("check_in", "security"): 10,
            ("security", "gate_a"): 15,
            ("security", "gate_b"): 12,
            ("security", "gate_c"): 18,
            ("gate_a", "gate_b"): 8,
            ("gate_b", "gate_c"): 10,
            ("retail", "gate_a"): 5,
            ("retail", "gate_b"): 4,
            ("retail", "gate_c"): 6
        }
    
    def calculate_passenger_stress(self, db: Session, passenger_reference: str, 
                                 flight_id: int) -> PassengerStressMetric:
        """Calculate comprehensive stress score for a passenger."""
        
        # Get passenger journey state
        journey_state = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.passenger_reference == passenger_reference,
            PassengerJourneyState.flight_id == flight_id
        ).first()
        
        if not journey_state:
            raise ValueError("Passenger journey state not found")
        
        # Get flight information
        flight = db.query(Flight).filter(Flight.id == flight_id).first()
        if not flight:
            raise ValueError("Flight not found")
        
        # Calculate stress factors
        queue_factor = self._calculate_queue_stress(db, journey_state)
        time_pressure_factor = self._calculate_time_pressure(journey_state, flight)
        walking_distance_factor = self._calculate_walking_distance_stress(journey_state)
        flight_delay_factor = self._calculate_flight_delay_stress(flight)
        
        # Calculate overall stress score (weighted average)
        weights = {
            "queue": 0.3,
            "time_pressure": 0.4,
            "walking": 0.15,
            "flight_delay": 0.15
        }
        
        overall_stress = (
            queue_factor * weights["queue"] +
            time_pressure_factor * weights["time_pressure"] +
            walking_distance_factor * weights["walking"] +
            flight_delay_factor * weights["flight_delay"]
        )
        
        # Determine stress level
        stress_level = self._get_stress_level(overall_stress)
        
        # Calculate time to boarding
        time_to_boarding = self._calculate_time_to_boarding(journey_state, flight)
        
        # Create stress metric record
        stress_metric = PassengerStressMetric(
            passenger_reference=passenger_reference,
            flight_id=flight_id,
            stress_score=overall_stress,
            stress_level=stress_level,
            queue_length_factor=queue_factor,
            time_pressure_factor=time_pressure_factor,
            walking_distance_factor=walking_distance_factor,
            flight_delay_factor=flight_delay_factor,
            current_location=journey_state.current_location,
            time_to_boarding=time_to_boarding,
            calculated_at=datetime.utcnow()
        )
        
        db.add(stress_metric)
        return stress_metric
    
    def _calculate_queue_stress(self, db: Session, journey_state: PassengerJourneyState) -> float:
        """Calculate stress based on queue lengths."""
        
        # Get current passenger flow data for the relevant area
        if journey_state.current_location and "security" in journey_state.current_location.lower():
            # Get security queue data
            flows = db.query(PassengerFlow).filter(
                PassengerFlow.terminal_zone == journey_state.current_location.split("_")[0]
            ).all()
            
            if flows:
                avg_security_queue = sum(f.security_queue_count for f in flows) / len(flows)
                # Normalize to 0-1 scale (0 people = 0 stress, 200+ people = 1 stress)
                queue_stress = min(avg_security_queue / 200.0, 1.0)
                return queue_stress
        
        elif journey_state.current_state == "check_in":
            # Get check-in queue data
            flows = db.query(PassengerFlow).all()
            if flows:
                avg_checkin_queue = sum(f.check_in_count for f in flows) / len(flows)
                queue_stress = min(avg_checkin_queue / 300.0, 1.0)
                return queue_stress
        
        return 0.2  # Base queue stress
    
    def _calculate_time_pressure(self, journey_state: PassengerJourneyState, flight: Flight) -> float:
        """Calculate stress based on time pressure to boarding."""
        
        if not flight.scheduled_time:
            return 0.3  # Default time pressure
        
        now = datetime.utcnow()
        departure_time = flight.scheduled_time
        
        # Calculate time remaining until departure
        time_until_departure = (departure_time - now).total_seconds() / 60  # minutes
        
        # Different time pressure based on current state
        if journey_state.current_state == "arrival":
            # High pressure if less than 2 hours until departure
            if time_until_departure < 120:
                return min((120 - time_until_departure) / 120.0, 1.0)
        
        elif journey_state.current_state == "check_in":
            # High pressure if less than 90 minutes until departure
            if time_until_departure < 90:
                return min((90 - time_until_departure) / 90.0, 1.0)
        
        elif journey_state.current_state == "security":
            # Very high pressure if less than 60 minutes until departure
            if time_until_departure < 60:
                return min((60 - time_until_departure) / 60.0, 1.0)
        
        elif journey_state.current_state == "post_security":
            # High pressure if less than 45 minutes until departure
            if time_until_departure < 45:
                return min((45 - time_until_departure) / 45.0, 1.0)
        
        elif journey_state.current_state == "gate":
            # Critical pressure if boarding soon
            if journey_state.estimated_boarding_time:
                time_to_boarding = (journey_state.estimated_boarding_time - now).total_seconds() / 60
                if time_to_boarding < 30:
                    return min((30 - time_to_boarding) / 30.0, 1.0)
        
        return 0.1  # Low time pressure
    
    def _calculate_walking_distance_stress(self, journey_state: PassengerJourneyState) -> float:
        """Calculate stress based on walking distance and time."""
        
        # Base stress on current state and typical walking times
        state_walking_stress = {
            "arrival": 0.1,
            "check_in": 0.2,
            "security": 0.4,  # Security can be stressful due to process
            "post_security": 0.3,
            "gate": 0.2,
            "boarding": 0.1
        }
        
        base_stress = state_walking_stress.get(journey_state.current_state, 0.2)
        
        # Add stress if passenger has been in current state too long
        if journey_state.dwell_time_minutes:
            # More stress if stuck in one place too long
            dwell_stress = min(journey_state.dwell_time_minutes / 60.0, 0.3)
            base_stress += dwell_stress
        
        return min(base_stress, 1.0)
    
    def _calculate_flight_delay_stress(self, flight: Flight) -> float:
        """Calculate stress based on flight delays."""
        
        if not flight.scheduled_time:
            return 0.1  # Minimal stress if no schedule info
        
        now = datetime.utcnow()
        
        # Check if flight is delayed
        if flight.status == "delayed":
            if flight.predicted_arrival_delay_min:
                # Stress based on delay magnitude
                delay_stress = min(flight.predicted_arrival_delay_min / 120.0, 1.0)  # 2+ hours = max stress
                return delay_stress
            else:
                return 0.6  # Generic delay stress
        
        # Check if estimated time is later than scheduled
        if flight.estimated_time and flight.estimated_time > flight.scheduled_time:
            delay_minutes = (flight.estimated_time - flight.scheduled_time).total_seconds() / 60
            delay_stress = min(delay_minutes / 60.0, 1.0)  # 1+ hour delay = max stress
            return delay_stress
        
        return 0.1  # Minimal stress for on-time flights
    
    def _get_stress_level(self, stress_score: float) -> str:
        """Determine stress level category from score."""
        if stress_score >= self.stress_thresholds["critical"]:
            return "critical"
        elif stress_score >= self.stress_thresholds["high"]:
            return "high"
        elif stress_score >= self.stress_thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    def _calculate_time_to_boarding(self, journey_state: PassengerJourneyState, flight: Flight) -> Optional[int]:
        """Calculate minutes until boarding."""
        
        if journey_state.estimated_boarding_time:
            now = datetime.utcnow()
            time_to_boarding = (journey_state.estimated_boarding_time - now).total_seconds() / 60
            return max(0, int(time_to_boarding))
        
        return None
    
    def get_high_stress_passengers(self, db: Session, flight_id: Optional[int] = None, 
                                 stress_threshold: float = 0.7) -> List[PassengerStressMetric]:
        """Get passengers with high stress scores."""
        
        query = db.query(PassengerStressMetric).filter(
            PassengerStressMetric.stress_score >= stress_threshold
        ).order_by(PassengerStressMetric.stress_score.desc())
        
        if flight_id:
            query = query.filter(PassengerStressMetric.flight_id == flight_id)
        
        # Get only recent stress metrics (last 30 minutes)
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
        query = query.filter(PassengerStressMetric.calculated_at >= thirty_minutes_ago)
        
        return query.all()
    
    def generate_stress_alerts(self, db: Session) -> List[Alert]:
        """Generate alerts for high-stress passengers."""
        
        alerts = []
        high_stress_passengers = self.get_high_stress_passengers(db, stress_threshold=0.8)
        
        for stress_metric in high_stress_passengers:
            # Create alert for critical stress passengers
            alert = Alert(
                alert_type="passenger_stress",
                severity="critical" if stress_metric.stress_score >= 0.9 else "warning",
                source_module="passenger_intelligence",
                message=f"High stress detected for passenger {stress_metric.passenger_reference} "
                        f"(score: {stress_metric.stress_score:.2f}) at {stress_metric.current_location}",
                related_entity_type="passenger",
                related_entity_id=stress_metric.passenger_reference,
                created_at=datetime.utcnow(),
                uniqueness_key=f"passenger_stress:{stress_metric.passenger_reference}:{stress_metric.flight_id}"
            )
            alerts.append(alert)
        
        return alerts
    
    def get_flight_stress_summary(self, db: Session, flight_id: int) -> Dict:
        """Get stress summary for a specific flight."""
        
        # Get recent stress metrics for this flight
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
        stress_metrics = db.query(PassengerStressMetric).filter(
            PassengerStressMetric.flight_id == flight_id,
            PassengerStressMetric.calculated_at >= thirty_minutes_ago
        ).all()
        
        if not stress_metrics:
            return {
                "total_passengers": 0,
                "avg_stress_score": 0,
                "stress_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                "high_stress_count": 0
            }
        
        # Calculate summary statistics
        total_passengers = len(stress_metrics)
        avg_stress_score = sum(m.stress_score for m in stress_metrics) / total_passengers
        high_stress_count = sum(1 for m in stress_metrics if m.stress_score >= 0.7)
        
        # Stress distribution
        stress_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for metric in stress_metrics:
            stress_distribution[metric.stress_level] += 1
        
        return {
            "total_passengers": total_passengers,
            "avg_stress_score": round(avg_stress_score, 3),
            "stress_distribution": stress_distribution,
            "high_stress_count": high_stress_count,
            "high_stress_percentage": round((high_stress_count / total_passengers) * 100, 1)
        }
    
    def recommend_stress_reduction(self, db: Session, passenger_reference: str, 
                                 flight_id: int) -> List[Dict]:
        """Recommend actions to reduce passenger stress."""
        
        stress_metric = db.query(PassengerStressMetric).filter(
            PassengerStressMetric.passenger_reference == passenger_reference,
            PassengerStressMetric.flight_id == flight_id
        ).order_by(PassengerStressMetric.calculated_at.desc()).first()
        
        if not stress_metric:
            return []
        
        recommendations = []
        
        # Queue stress recommendations
        if stress_metric.queue_length_factor > 0.7:
            recommendations.append({
                "type": "queue_management",
                "priority": "high",
                "action": "Offer fast-track security access",
                "reason": "High queue length stress detected"
            })
        
        # Time pressure recommendations
        if stress_metric.time_pressure_factor > 0.7:
            recommendations.append({
                "type": "time_assistance",
                "priority": "critical",
                "action": "Provide expedited processing and directions",
                "reason": "High time pressure - boarding imminent"
            })
        
        # Walking distance recommendations
        if stress_metric.walking_distance_factor > 0.6:
            recommendations.append({
                "type": "mobility_assistance",
                "priority": "medium",
                "action": "Offer electric cart or shuttle service",
                "reason": "Long walking distance detected"
            })
        
        # Flight delay recommendations
        if stress_metric.flight_delay_factor > 0.5:
            recommendations.append({
                "type": "delay_support",
                "priority": "medium",
                "action": "Provide lounge access and refreshment vouchers",
                "reason": "Flight delay causing stress"
            })
        
        return recommendations


# Global instance
intelligence_engine = PassengerIntelligenceEngine()
