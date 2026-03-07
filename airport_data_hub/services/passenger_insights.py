"""
Passenger Journey Insights Service.

Provides analytics and insights for:
- Passenger dwell time analytics
- Gate arrival timing predictions
- Journey performance metrics
- Retail potential analysis
"""

import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import (
    PassengerInsight, PassengerJourneyState, PassengerJourneyEvent,
    PassengerStressMetric, RetailOpportunity, Flight,
    QueueState, QueueEvent  # Add new passenger flow models
)
from ..database import SessionLocal
from ..services.queue_state_engine import queue_state_engine  # Import queue state engine


class PassengerInsightsEngine:
    """Engine for passenger journey analytics and insights."""
    
    def __init__(self):
        self.insight_cache_minutes = 30  # Cache insights for 30 minutes
    
    def calculate_flight_insights(self, db: Session, flight_id: int) -> PassengerInsight:
        """Calculate comprehensive insights for a specific flight."""
        
        # Check if recent insights already exist
        flight = db.query(Flight).filter(Flight.id == flight_id).first()
        if not flight:
            raise ValueError("Flight not found")
        
        # Check for existing recent insights
        recent_insight = db.query(PassengerInsight).filter(
            PassengerInsight.flight_id == flight_id,
            PassengerInsight.flight_date >= flight.scheduled_time.date()
        ).order_by(PassengerInsight.calculated_at.desc()).first()
        
        if recent_insight and (datetime.utcnow() - recent_insight.calculated_at).total_seconds() < self.insight_cache_minutes * 60:
            return recent_insight
        
        # Calculate fresh insights
        insights = self._compute_flight_insights(db, flight_id, flight)
        
        # Save or update insights
        if recent_insight:
            # Update existing
            recent_insight.total_passengers = insights["total_passengers"]
            recent_insight.avg_stress_score = insights["avg_stress_score"]
            recent_insight.high_stress_count = insights["high_stress_count"]
            recent_insight.avg_check_in_to_security = insights["avg_check_in_to_security"]
            recent_insight.avg_security_to_gate = insights["avg_security_to_gate"]
            recent_insight.avg_dwell_time_post_security = insights["avg_dwell_time_post_security"]
            recent_insight.on_time_gate_arrival_rate = insights["on_time_gate_arrival_rate"]
            recent_insight.late_gate_arrival_count = insights["late_gate_arrival_count"]
            recent_insight.total_retail_opportunity_minutes = insights["total_retail_opportunity_minutes"]
            recent_insight.retail_ready_passengers = insights["retail_ready_passengers"]
            recent_insight.calculated_at = datetime.utcnow()
            insight_record = recent_insight
        else:
            # Create new
            insight_record = PassengerInsight(
                flight_id=flight_id,
                flight_date=flight.scheduled_time.date(),
                calculated_at=datetime.utcnow(),
                **insights
            )
            db.add(insight_record)
        
        db.flush()
        return insight_record
    
    def _compute_flight_insights(self, db: Session, flight_id: int, flight: Flight) -> Dict:
        """Compute all insights for a flight."""
        
        insights = {
            "total_passengers": 0,
            "avg_stress_score": 0,
            "high_stress_count": 0,
            "avg_check_in_to_security": 0,
            "avg_security_to_gate": 0,
            "avg_dwell_time_post_security": 0,
            "on_time_gate_arrival_rate": 0,
            "late_gate_arrival_count": 0,
            "total_retail_opportunity_minutes": 0,
            "retail_ready_passengers": 0
        }
        
        # Get total passengers (journey states)
        total_passengers = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.flight_id == flight_id
        ).count()
        insights["total_passengers"] = total_passengers
        
        if total_passengers == 0:
            return insights
        
        # Calculate stress metrics
        stress_metrics = self._get_flight_stress_metrics(db, flight_id)
        if stress_metrics:
            insights["avg_stress_score"] = statistics.mean([m.stress_score for m in stress_metrics])
            insights["high_stress_count"] = sum(1 for m in stress_metrics if m.stress_score >= 0.7)
        
        # Calculate journey timing analytics
        timing_analytics = self._calculate_journey_timing(db, flight_id)
        insights.update(timing_analytics)
        
        # Calculate gate arrival predictions
        gate_analytics = self._calculate_gate_arrival_analytics(db, flight_id, flight)
        insights.update(gate_analytics)
        
        # Calculate retail potential
        retail_analytics = self._calculate_retail_potential(db, flight_id)
        insights.update(retail_analytics)
        
        return insights
    
    def _get_flight_stress_metrics(self, db: Session, flight_id: int) -> List[PassengerStressMetric]:
        """Get recent stress metrics for flight."""
        
        # Get stress metrics from last 2 hours
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        return db.query(PassengerStressMetric).filter(
            PassengerStressMetric.flight_id == flight_id,
            PassengerStressMetric.calculated_at >= two_hours_ago
        ).all()
    
    def _calculate_journey_timing(self, db: Session, flight_id: int) -> Dict:
        """Calculate journey timing analytics."""
        
        timing = {
            "avg_check_in_to_security": 0,
            "avg_security_to_gate": 0,
            "avg_dwell_time_post_security": 0
        }
        
        # Get journey events for timing calculation
        events = db.query(PassengerJourneyEvent).filter(
            PassengerJourneyEvent.flight_id == flight_id
        ).order_by(PassengerJourneyEvent.passenger_reference, PassengerJourneyEvent.event_timestamp).all()
        
        # Group events by passenger
        passenger_events = {}
        for event in events:
            if event.passenger_reference not in passenger_events:
                passenger_events[event.passenger_reference] = []
            passenger_events[event.passenger_reference].append(event)
        
        # Calculate timing for each passenger
        check_in_to_security_times = []
        security_to_gate_times = []
        post_security_dwell_times = []
        
        for passenger_ref, passenger_event_list in passenger_events.items():
            # Find check-in to security time
            check_in_time = None
            security_time = None
            gate_time = None
            
            for event in passenger_event_list:
                if event.event_type == "check_in" and check_in_time is None:
                    check_in_time = event.event_timestamp
                elif event.event_type == "security_scan" and security_time is None:
                    security_time = event.event_timestamp
                elif event.event_type == "gate_scan" and gate_time is None:
                    gate_time = event.event_timestamp
            
            # Calculate durations
            if check_in_time and security_time:
                duration = (security_time - check_in_time).total_seconds() / 60
                if 0 < duration < 180:  # Reasonable range (0-3 hours)
                    check_in_to_security_times.append(duration)
            
            if security_time and gate_time:
                duration = (gate_time - security_time).total_seconds() / 60
                if 0 < duration < 120:  # Reasonable range (0-2 hours)
                    security_to_gate_times.append(duration)
            
            # Calculate post-security dwell time from journey states
            journey_states = db.query(PassengerJourneyState).filter(
                PassengerJourneyState.passenger_reference == passenger_ref,
                PassengerJourneyState.flight_id == flight_id,
                PassengerJourneyState.current_state == "post_security"
            ).first()
            
            if journey_states and journey_states.dwell_time_minutes:
                if 0 < journey_states.dwell_time_minutes < 180:
                    post_security_dwell_times.append(journey_states.dwell_time_minutes)
        
        # Calculate averages
        if check_in_to_security_times:
            timing["avg_check_in_to_security"] = int(statistics.mean(check_in_to_security_times))
        
        if security_to_gate_times:
            timing["avg_security_to_gate"] = int(statistics.mean(security_to_gate_times))
        
        if post_security_dwell_times:
            timing["avg_dwell_time_post_security"] = int(statistics.mean(post_security_dwell_times))
        
        return timing
    
    def _calculate_gate_arrival_analytics(self, db: Session, flight_id: int, flight: Flight) -> Dict:
        """Calculate gate arrival predictions and analytics."""
        
        analytics = {
            "on_time_gate_arrival_rate": 0,
            "late_gate_arrival_count": 0
        }
        
        if not flight.scheduled_time:
            return analytics
        
        # Get passengers who have reached gate
        gate_passengers = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.flight_id == flight_id,
            PassengerJourneyState.current_state.in_(["gate", "boarding", "completed"])
        ).all()
        
        if not gate_passengers:
            return analytics
        
        # Define "on time" as arriving at gate 20+ minutes before departure
        on_time_threshold = flight.scheduled_time - timedelta(minutes=20)
        
        on_time_count = 0
        late_count = 0
        
        for passenger in gate_passengers:
            # Use estimated gate arrival or state entry time
            arrival_time = passenger.estimated_gate_arrival or passenger.state_entered_at
            
            if arrival_time and arrival_time <= on_time_threshold:
                on_time_count += 1
            else:
                late_count += 1
        
        total_arrived = on_time_count + late_count
        if total_arrived > 0:
            analytics["on_time_gate_arrival_rate"] = round((on_time_count / total_arrived) * 100, 1)
            analytics["late_gate_arrival_count"] = late_count
        
        return analytics
    
    def _calculate_retail_potential(self, db: Session, flight_id: int) -> Dict:
        """Calculate retail potential for flight."""
        
        retail = {
            "total_retail_opportunity_minutes": 0,
            "retail_ready_passengers": 0
        }
        
        # Get retail opportunities for this flight
        opportunities = db.query(RetailOpportunity).filter(
            RetailOpportunity.flight_id == flight_id,
            RetailOpportunity.expires_at > datetime.utcnow()
        ).all()
        
        if not opportunities:
            return retail
        
        # Calculate total opportunity minutes
        total_minutes = sum(opp.duration_minutes for opp in opportunities)
        retail["total_retail_opportunity_minutes"] = total_minutes
        
        # Count retail-ready passengers (readiness score > 0.6)
        retail_ready = sum(1 for opp in opportunities if opp.retail_readiness_score > 0.6)
        retail["retail_ready_passengers"] = retail_ready
        
        return retail
    
    def get_passenger_flow_analytics(self, db: Session, time_window_hours: int = 24) -> Dict:
        """Get overall passenger flow analytics for the airport."""
        
        # Get journey states from last N hours
        time_window_start = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        states = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.created_at >= time_window_start
        ).all()
        
        if not states:
            return {
                "total_passengers": 0,
                "state_distribution": {},
                "avg_stress_score": 0,
                "peak_hours": [],
                "terminal_distribution": {}
            }
        
        # State distribution
        state_counts = {}
        terminal_counts = {}
        stress_scores = []
        hourly_counts = {}
        
        for state in states:
            # Count states
            state_name = state.current_state
            state_counts[state_name] = state_counts.get(state_name, 0) + 1
            
            # Count terminals
            terminal = self._extract_terminal_from_location(state.current_location)
            terminal_counts[terminal] = terminal_counts.get(terminal, 0) + 1
            
            # Get stress score
            stress_metric = db.query(PassengerStressMetric).filter(
                PassengerStressMetric.passenger_reference == state.passenger_reference,
                PassengerStressMetric.flight_id == state.flight_id
            ).order_by(PassengerStressMetric.calculated_at.desc()).first()
            
            if stress_metric:
                stress_scores.append(stress_metric.stress_score)
            
            # Hourly distribution
            hour = state.created_at.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        # Find peak hours
        peak_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [{"hour": hour, "count": count} for hour, count in peak_hours]
        
        # Calculate average stress
        avg_stress = statistics.mean(stress_scores) if stress_scores else 0
        
        return {
            "total_passengers": len(states),
            "state_distribution": state_counts,
            "avg_stress_score": round(avg_stress, 3),
            "peak_hours": peak_hours,
            "terminal_distribution": terminal_counts,
            "time_window_hours": time_window_hours
        }
    
    def _extract_terminal_from_location(self, location: Optional[str]) -> str:
        """Extract terminal from location string."""
        if not location:
            return "Unknown"
        
        for terminal in ["T1", "T2", "T3", "T4", "T5"]:
            if terminal in location:
                return terminal
        
        return "Unknown"
    
    def predict_gate_arrival_times(self, db: Session, flight_id: int) -> Dict:
        """Predict gate arrival times for passengers on a flight."""
        
        flight = db.query(Flight).filter(Flight.id == flight_id).first()
        if not flight:
            raise ValueError("Flight not found")
        
        # Get passengers not yet at gate
        passengers = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.flight_id == flight_id,
            PassengerJourneyState.current_state.in_(["arrival", "check_in", "security", "post_security", "retail"])
        ).all()
        
        predictions = []
        
        for passenger in passengers:
            prediction = self._predict_individual_gate_arrival(passenger, flight)
            if prediction:
                predictions.append(prediction)
        
        return {
            "flight_id": flight_id,
            "flight_code": flight.flight_code,
            "scheduled_departure": flight.scheduled_time.isoformat(),
            "predictions": predictions,
            "total_passengers_predicted": len(predictions)
        }
    
    def _predict_individual_gate_arrival(self, passenger: PassengerJourneyState, flight: Flight) -> Optional[Dict]:
        """Predict gate arrival time for individual passenger."""
        
        now = datetime.utcnow()
        
        # Base prediction on current state
        if passenger.current_state == "post_security":
            # Already past security - predict based on typical dwell time
            typical_dwell = 25  # minutes
            predicted_arrival = now + timedelta(minutes=typical_dwell)
            confidence = 0.7
            
        elif passenger.current_state == "security":
            # In security - predict based on typical processing time
            typical_security_time = 15  # minutes
            typical_dwell_after = 20  # minutes
            predicted_arrival = now + timedelta(minutes=typical_security_time + typical_dwell_after)
            confidence = 0.6
            
        elif passenger.current_state == "check_in":
            # At check-in - predict full journey time
            typical_check_in_to_gate = 45  # minutes
            predicted_arrival = now + timedelta(minutes=typical_check_in_to_gate)
            confidence = 0.5
            
        elif passenger.current_state == "retail":
            # Already shopping - predict soon
            typical_remaining_time = 10  # minutes
            predicted_arrival = now + timedelta(minutes=typical_remaining_time)
            confidence = 0.8
        
        else:
            return None
        
        # Check if prediction is after scheduled departure
        if predicted_arrival > flight.scheduled_time:
            predicted_arrival = flight.scheduled_time - timedelta(minutes=5)  # Assume they'll make it
            confidence *= 0.5  # Lower confidence for late predictions
        
        return {
            "passenger_reference": passenger.passenger_reference,
            "current_state": passenger.current_state,
            "current_location": passenger.current_location,
            "predicted_gate_arrival": predicted_arrival.isoformat(),
            "confidence_score": round(confidence, 2),
            "minutes_to_arrival": int((predicted_arrival - now).total_seconds() / 60),
            "on_time_probability": self._calculate_on_time_probability(predicted_arrival, flight.scheduled_time)
        }
    
    def _calculate_on_time_probability(self, arrival_time: datetime, departure_time: datetime) -> float:
        """Calculate probability of on-time gate arrival."""
        
        on_time_threshold = departure_time - timedelta(minutes=20)
        
        if arrival_time <= on_time_threshold:
            return 1.0
        elif arrival_time <= departure_time:
            # Late but before departure - decreasing probability
            minutes_late = (arrival_time - on_time_threshold).total_seconds() / 60
            return max(0.0, 1.0 - (minutes_late / 20.0))
        else:
            # After departure - very low probability
            return 0.1
    
    def get_retail_system_insights(self, db: Session, terminal: Optional[str] = None) -> Dict:
        """Provide insights for retail systems and passenger flow management."""
        
        # Get current passenger states
        now = datetime.utcnow()
        query = db.query(PassengerJourneyState).filter(
            PassengerJourneyState.current_state.in_(["post_security", "gate", "retail"])
        )
        
        if terminal:
            query = query.filter(PassengerJourneyState.current_location.like(f"{terminal}%"))
        
        current_passengers = query.all()
        
        # Get retail opportunities
        opp_query = db.query(RetailOpportunity).filter(
            RetailOpportunity.expires_at > now
        )
        
        if terminal:
            opp_query = opp_query.filter(RetailOpportunity.terminal_zone == terminal)
        
        opportunities = opp_query.all()
        
        # Analyze patterns
        insights = {
            "terminal": terminal or "all",
            "timestamp": now.isoformat(),
            "current_passenger_count": len(current_passengers),
            "active_opportunities": len(opportunities),
            "state_distribution": {},
            "retail_readiness_distribution": {},
            "time_pressure_distribution": {},
            "recommendations": []
        }
        
        # State distribution
        for passenger in current_passengers:
            state = passenger.current_state
            insights["state_distribution"][state] = insights["state_distribution"].get(state, 0) + 1
        
        # Retail readiness distribution
        readiness_ranges = {"low": 0, "medium": 0, "high": 0}
        for opp in opportunities:
            if opp.retail_readiness_score < 0.4:
                readiness_ranges["low"] += 1
            elif opp.retail_readiness_score < 0.7:
                readiness_ranges["medium"] += 1
            else:
                readiness_ranges["high"] += 1
        
        insights["retail_readiness_distribution"] = readiness_ranges
        
        # Time pressure distribution
        pressure_ranges = {"low": 0, "medium": 0, "high": 0}
        for opp in opportunities:
            pressure_ranges[opp.time_pressure] = pressure_ranges.get(opp.time_pressure, 0) + 1
        
        insights["time_pressure_distribution"] = pressure_ranges
        
        # Generate recommendations
        insights["recommendations"] = self._generate_retail_recommendations(insights)
        
        return insights
    
    def _generate_retail_recommendations(self, insights: Dict) -> List[str]:
        """Generate recommendations based on insights."""
        
        recommendations = []
        
        # High opportunity volume
        if insights["active_opportunities"] > 50:
            recommendations.append("High retail opportunity volume - ensure adequate staffing")
        
        # High readiness passengers
        total_readiness = insights["retail_readiness_distribution"]
        if total_readiness.get("high", 0) > total_readiness.get("low", 0):
            recommendations.append("High retail readiness detected - promote premium offerings")
        
        # Time pressure analysis
        pressure_dist = insights["time_pressure_distribution"]
        if pressure_dist.get("high", 0) / max(insights["active_opportunities"], 1) > 0.5:
            recommendations.append("High time pressure - emphasize grab-and-go options")
        
        # State-based recommendations
        state_dist = insights["state_distribution"]
        if state_dist.get("post_security", 0) > state_dist.get("gate", 0) * 2:
            recommendations.append("Many passengers in post-security - good time for engagement")
        
        return recommendations


# Global instance
insights_engine = PassengerInsightsEngine()
