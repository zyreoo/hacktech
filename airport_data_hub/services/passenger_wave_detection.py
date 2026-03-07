"""
Passenger Wave Detection System.

Advanced passenger arrival wave detection and analysis:
- Detect passenger arrival waves
- Cluster flights by arrival time
- Predict peak congestion windows
- Analyze wave patterns and impacts
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    PassengerWave, QueueEvent, QueueState, Flight
)
from ..database import SessionLocal


class PassengerWaveDetectionEngine:
    """Advanced passenger wave detection and analysis system."""
    
    def __init__(self):
        self.wave_detection_params = {
            "clustering_window_minutes": 60,    # Time window to cluster flights
            "min_flights_per_wave": 2,       # Minimum flights to form a wave
            "max_flights_per_wave": 8,       # Maximum flights per wave
            "wave_separation_minutes": 90,       # Minimum separation between waves
            "passenger_threshold_per_wave": 200, # Minimum passengers for wave detection
            "peak_flow_threshold": 10,          # Passengers per minute for peak detection
            "congestion_threshold": 0.7        # Queue utilization for congestion
        }
        
        self.wave_types = {
            "departure_wave": {
                "time_window": 120,  # 2 hours before departure
                "description": "Multiple flights departing close together"
            },
            "arrival_wave": {
                "time_window": 90,   # 1.5 hours after arrival
                "description": "Multiple flights arriving close together"
            },
            "transfer_wave": {
                "time_window": 60,   # 1 hour for connections
                "description": "Connecting passengers creating congestion"
            }
        }
    
    def detect_passenger_waves(self, db: Session, terminal: Optional[str] = None, 
                            hours_ahead: int = 4, hours_back: int = 2) -> List[PassengerWave]:
        """Detect passenger waves based on flight schedules."""
        
        # Get flight window
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        end_time = datetime.utcnow() + timedelta(hours=hours_ahead)
        
        # Get flights in the analysis window
        flights_query = db.query(Flight).filter(
            Flight.scheduled_time >= start_time,
            Flight.scheduled_time <= end_time
        )
        
        if terminal:
            flights_query = flights_query.filter(Flight.terminal == terminal)
        
        flights = flights_query.order_by(Flight.scheduled_time).all()
        
        if not flights:
            return []
        
        # Cluster flights into waves
        waves = self._cluster_flights_into_waves(flights)
        
        # Analyze each wave
        detected_waves = []
        for wave_data in waves:
            wave = self._analyze_wave(db, wave_data)
            detected_waves.append(wave)
        
        return detected_waves
    
    def predict_congestion_windows(self, db: Session, terminal: Optional[str] = None, 
                                hours_ahead: int = 6) -> List[Dict]:
        """Predict future congestion windows based on wave patterns."""
        
        # Get future flights
        future_time = datetime.utcnow() + timedelta(hours=hours_ahead)
        future_flights = db.query(Flight).filter(
            Flight.scheduled_time >= datetime.utcnow(),
            Flight.scheduled_time <= future_time
        )
        
        if terminal:
            future_flights = future_flights.filter(Flight.terminal == terminal)
        
        future_flights = future_flights.order_by(Flight.scheduled_time).all()
        
        # Predict waves from future flights
        predicted_waves = self._cluster_flights_into_waves(future_flights)
        
        # Analyze congestion impact
        congestion_windows = []
        for wave_data in predicted_waves:
            congestion_impact = self._predict_congestion_impact(db, wave_data)
            congestion_windows.append(congestion_impact)
        
        return congestion_windows
    
    def analyze_wave_patterns(self, db: Session, days_back: int = 30) -> Dict:
        """Analyze historical wave patterns."""
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)
        
        # Get historical waves
        historical_waves = db.query(PassengerWave).filter(
            PassengerWave.detected_at >= cutoff_time
        ).all()
        
        if not historical_waves:
            return {"error": "No historical wave data available"}
        
        # Analyze patterns
        pattern_analysis = {
            "total_waves": len(historical_waves),
            "wave_types": {},
            "time_distribution": {},
            "terminal_distribution": {},
            "peak_flows": [],
            "average_duration": 0,
            "average_passengers": 0
        }
        
        # Group by wave type
        for wave in historical_waves:
            wave_type = wave.wave_type
            if wave_type not in pattern_analysis["wave_types"]:
                pattern_analysis["wave_types"][wave_type] = {
                    "count": 0,
                    "total_passengers": 0,
                    "average_duration": 0,
                    "peak_flows": []
                }
            
            pattern_analysis["wave_types"][wave_type]["count"] += 1
            pattern_analysis["wave_types"][wave_type]["total_passengers"] += wave.total_passengers
            pattern_analysis["wave_types"][wave_type]["average_duration"] += wave.duration_minutes
            pattern_analysis["wave_types"][wave_type]["peak_flows"].append(wave.peak_flow_rate)
        
        # Calculate averages
        for wave_type, data in pattern_analysis["wave_types"].items():
            if data["count"] > 0:
                data["average_duration"] = data["average_duration"] / data["count"]
                data["average_peak_flow"] = sum(data["peak_flows"]) / len(data["peak_flows"])
                data["average_passengers_per_wave"] = data["total_passengers"] / data["count"]
        
        # Time distribution analysis
        for wave in historical_waves:
            hour = wave.start_time.hour
            if hour not in pattern_analysis["time_distribution"]:
                pattern_analysis["time_distribution"][hour] = {
                    "count": 0,
                    "passengers": 0
                }
            
            pattern_analysis["time_distribution"][hour]["count"] += 1
            pattern_analysis["time_distribution"][hour]["passengers"] += wave.total_passengers
        
        # Terminal distribution
        for wave in historical_waves:
            terminal_name = wave.terminal
            if terminal_name not in pattern_analysis["terminal_distribution"]:
                pattern_analysis["terminal_distribution"][terminal_name] = {
                    "count": 0,
                    "passengers": 0
                }
            
            pattern_analysis["terminal_distribution"][terminal_name]["count"] += 1
            pattern_analysis["terminal_distribution"][terminal_name]["passengers"] += wave.total_passengers
        
        # Overall averages
        if historical_waves:
            pattern_analysis["average_duration"] = sum(w.duration_minutes for w in historical_waves) / len(historical_waves)
            pattern_analysis["average_passengers"] = sum(w.total_passengers for w in historical_waves) / len(historical_waves)
            pattern_analysis["peak_flows"] = [w.peak_flow_rate for w in historical_waves]
        
        return pattern_analysis
    
    def get_active_waves(self, db: Session, terminal: Optional[str] = None) -> List[PassengerWave]:
        """Get currently active passenger waves."""
        
        # Active waves are those detected in last 2 hours and not ended
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        
        query = db.query(PassengerWave).filter(
            PassengerWave.detected_at >= cutoff_time,
            or_(
                PassengerWave.end_time.is_(None),
                PassengerWave.end_time > datetime.utcnow()
            )
        )
        
        if terminal:
            query = query.filter(PassengerWave.terminal == terminal)
        
        return query.order_by(PassengerWave.detected_at.desc()).all()
    
    def update_wave_status(self, db: Session, wave_id: str, 
                        current_flow_rate: float, current_queue_lengths: Dict) -> PassengerWave:
        """Update wave status with current metrics."""
        
        wave = db.query(PassengerWave).filter(
            PassengerWave.wave_id == wave_id
        ).first()
        
        if not wave:
            raise ValueError(f"Wave {wave_id} not found")
        
        # Update current metrics
        wave.current_flow_rate = current_flow_rate
        wave.peak_flow_rate = max(wave.peak_flow_rate, current_flow_rate)
        
        # Update peak queue lengths
        peak_lengths = json.loads(wave.peak_queue_lengths or "{}")
        for checkpoint, length in current_queue_lengths.items():
            if checkpoint not in peak_lengths or length > peak_lengths.get(checkpoint, 0):
                peak_lengths[checkpoint] = length
        
        wave.peak_queue_lengths = json.dumps(peak_lengths)
        wave.updated_at = datetime.utcnow()
        
        # Check if wave should end
        if current_flow_rate < self.wave_detection_params["peak_flow_threshold"] * 0.3:
            wave.end_time = datetime.utcnow()
            wave.duration_minutes = int((wave.end_time - wave.start_time).total_seconds() / 60)
        
        db.commit()
        return wave
    
    def _cluster_flights_into_waves(self, flights: List[Flight]) -> List[Dict]:
        """Cluster flights into passenger waves based on time proximity."""
        
        if not flights:
            return []
        
        waves = []
        current_wave = []
        
        for i, flight in enumerate(flights):
            if not current_wave:
                # Start new wave
                current_wave = [flight]
            else:
                # Check if this flight belongs to current wave
                time_diff = (flight.scheduled_time - current_wave[0].scheduled_time).total_seconds() / 60
                
                if time_diff <= self.wave_detection_params["clustering_window_minutes"]:
                    # Add to current wave
                    current_wave.append(flight)
                else:
                    # Current wave is complete, start new one
                    if len(current_wave) >= self.wave_detection_params["min_flights_per_wave"]:
                        waves.append(self._create_wave_data(current_wave))
                    
                    current_wave = [flight]
        
        # Don't forget the last wave
        if len(current_wave) >= self.wave_detection_params["min_flights_per_wave"]:
            waves.append(self._create_wave_data(current_wave))
        
        return waves
    
    def _create_wave_data(self, flights: List[Flight]) -> Dict:
        """Create wave data structure from clustered flights."""
        
        if not flights:
            return {}
        
        # Sort flights by time
        flights.sort(key=lambda f: f.scheduled_time)
        
        # Calculate wave characteristics
        start_time = flights[0].scheduled_time
        end_time = flights[-1].scheduled_time
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        total_passengers = sum(flight.passenger_count for flight in flights)
        peak_flow_rate = total_passengers / max(duration_minutes, 1)
        
        # Determine wave type based on flight context
        wave_type = self._determine_wave_type(flights)
        
        return {
            "flights": flights,
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": duration_minutes,
            "total_passengers": total_passengers,
            "peak_flow_rate": peak_flow_rate,
            "wave_type": wave_type,
            "terminal": flights[0].terminal,
            "flight_count": len(flights)
        }
    
    def _determine_wave_type(self, flights: List[Flight]) -> str:
        """Determine the type of passenger wave."""
        
        if not flights:
            return "unknown"
        
        # Check if flights are arrivals or departures
        current_time = datetime.utcnow()
        
        arrivals = sum(1 for f in flights if f.scheduled_time < current_time)
        departures = sum(1 for f in flights if f.scheduled_time > current_time)
        
        if departures > arrivals:
            return "departure_wave"
        elif arrivals > departures:
            return "arrival_wave"
        else:
            # Check for connecting flights (transfers)
            # This would need more sophisticated logic with flight connections
            # For now, assume mixed
            return "transfer_wave"
    
    def _analyze_wave(self, db: Session, wave_data: Dict) -> PassengerWave:
        """Analyze a wave and create database record."""
        
        # Generate unique wave ID
        wave_id = f"WV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Get affected checkpoints
        affected_checkpoints = self._get_affected_checkpoints(db, wave_data["flights"])
        
        # Estimate peak queue lengths
        peak_queue_lengths = {}
        for checkpoint in affected_checkpoints:
            # Simple estimation based on passenger count and checkpoint capacity
            estimated_peak = min(wave_data["total_passengers"], 50)  # Cap at 50
            peak_queue_lengths[checkpoint] = estimated_peak
        
        # Calculate congestion duration
        congestion_duration = self._estimate_congestion_duration(wave_data)
        
        # Predict if we could have detected this wave in advance
        prediction_confidence = self._calculate_prediction_confidence(wave_data)
        predicted_start = wave_data["start_time"] - timedelta(minutes=30) if prediction_confidence > 0.7 else None
        predicted_peak_flow = wave_data["peak_flow_rate"] * 1.1 if prediction_confidence > 0.6 else None
        
        return PassengerWave(
            wave_id=wave_id,
            wave_type=wave_data["wave_type"],
            terminal=wave_data["terminal"],
            start_time=wave_data["start_time"],
            peak_time=wave_data["start_time"] + timedelta(minutes=wave_data["duration_minutes"] // 2),
            end_time=wave_data["end_time"],
            duration_minutes=wave_data["duration_minutes"],
            clustered_flights=json.dumps([{
                "flight_id": flight.id,
                "flight_number": flight.flight_number,
                "scheduled_time": flight.scheduled_time.isoformat(),
                "passenger_count": flight.passenger_count,
                "gate": flight.gate
            } for flight in wave_data["flights"]]),
            total_passengers=wave_data["total_passengers"],
            peak_flow_rate=wave_data["peak_flow_rate"],
            average_flow_rate=wave_data["peak_flow_rate"],
            affected_checkpoints=json.dumps(affected_checkpoints),
            peak_queue_lengths=json.dumps(peak_queue_lengths),
            congestion_duration=congestion_duration,
            predicted_start_time=predicted_start,
            predicted_peak_flow=predicted_peak_flow,
            prediction_confidence=prediction_confidence,
            detected_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _predict_congestion_impact(self, db: Session, wave_data: Dict) -> Dict:
        """Predict the congestion impact of a wave."""
        
        # Get checkpoint capacities
        checkpoint_types = ["security", "checkin", "boarding", "immigration"]
        checkpoint_capacities = {
            "security": 50, "checkin": 30, "boarding": 100, "immigration": 40
        }
        
        # Calculate impact on each checkpoint type
        impact_by_checkpoint = {}
        total_impact = 0
        
        for checkpoint_type in checkpoint_types:
            # Estimate impact based on wave type and passenger count
            base_impact = wave_data["total_passengers"] * 0.6  # 60% of passengers affect each checkpoint
            
            # Adjust based on wave type
            if wave_data["wave_type"] == "departure_wave":
                if checkpoint_type == "checkin":
                    base_impact *= 1.2  # Higher impact on check-in
                elif checkpoint_type == "security":
                    base_impact *= 1.1  # Moderate impact on security
                elif checkpoint_type == "boarding":
                    base_impact *= 1.3  # High impact on boarding
            elif wave_data["wave_type"] == "arrival_wave":
                if checkpoint_type == "immigration":
                    base_impact *= 1.2  # Higher impact on immigration
                elif checkpoint_type == "security":
                    base_impact *= 0.8  # Lower impact on security (already cleared)
            
            capacity = checkpoint_capacities[checkpoint_type]
            utilization = min(base_impact / capacity, 1.0)
            
            impact_by_checkpoint[checkpoint_type] = {
                "estimated_queue_length": int(base_impact),
                "utilization": utilization,
                "congestion_level": "high" if utilization > 0.7 else "medium" if utilization > 0.4 else "low"
            }
            
            total_impact += utilization
        
        return {
            "wave_id": f"prediction-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "wave_type": wave_data["wave_type"],
            "start_time": wave_data["start_time"].isoformat(),
            "duration_minutes": wave_data["duration_minutes"],
            "total_passengers": wave_data["total_passengers"],
            "peak_flow_rate": wave_data["peak_flow_rate"],
            "impact_by_checkpoint": impact_by_checkpoint,
            "overall_impact_score": total_impact / len(checkpoint_types),
            "congestion_duration": wave_data["duration_minutes"] * 0.8  # 80% of wave duration
        }
    
    def _get_affected_checkpoints(self, db: Session, flights: List[Flight]) -> List[str]:
        """Get checkpoints affected by a wave of flights."""
        
        if not flights:
            return []
        
        # Get unique terminals from flights
        terminals = list(set(flight.terminal for flight in flights))
        
        # For each terminal, get relevant checkpoints
        affected_checkpoints = set()
        
        for terminal in terminals:
            # Get queue states for this terminal
            checkpoints = db.query(QueueState.checkpoint_id).filter(
                QueueState.terminal == terminal
            ).all()
            
            for checkpoint in checkpoints:
                affected_checkpoints.add(checkpoint.checkpoint_id)
        
        return list(affected_checkpoints)
    
    def _estimate_congestion_duration(self, wave_data: Dict) -> int:
        """Estimate how long congestion will last."""
        
        # Base duration on wave duration
        base_duration = wave_data["duration_minutes"]
        
        # Adjust based on passenger volume
        volume_factor = min(wave_data["total_passengers"] / 200, 2.0)  # Normalize to 200 passengers
        
        # Adjust based on peak flow rate
        flow_factor = min(wave_data["peak_flow_rate"] / 10, 1.5)  # Normalize to 10 pax/min
        
        estimated_duration = int(base_duration * volume_factor * flow_factor)
        
        return max(15, min(estimated_duration, 180))  # Between 15 min and 3 hours
    
    def _calculate_prediction_confidence(self, wave_data: Dict) -> float:
        """Calculate confidence in wave prediction."""
        
        confidence = 0.5  # Base confidence
        
        # Higher confidence for larger waves
        if wave_data["total_passengers"] > 300:
            confidence += 0.2
        
        # Higher confidence for longer duration
        if wave_data["duration_minutes"] > 45:
            confidence += 0.1
        
        # Higher confidence for departure waves (more predictable)
        if wave_data["wave_type"] == "departure_wave":
            confidence += 0.1
        
        return min(confidence, 0.9)
    
    def get_wave_impact_summary(self, db: Session, hours_back: int = 24) -> Dict:
        """Get summary of wave impacts for recent period."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Get recent waves
        recent_waves = db.query(PassengerWave).filter(
            PassengerWave.detected_at >= cutoff_time
        ).all()
        
        if not recent_waves:
            return {"error": "No wave data available for specified period"}
        
        # Calculate impact summary
        total_waves = len(recent_waves)
        total_passengers = sum(w.total_passengers for w in recent_waves)
        total_congestion_minutes = sum(w.congestion_duration or 0 for w in recent_waves)
        
        # Group by wave type
        impact_by_type = {}
        for wave in recent_waves:
            wave_type = wave.wave_type
            if wave_type not in impact_by_type:
                impact_by_type[wave_type] = {
                    "count": 0,
                    "passengers": 0,
                    "congestion_minutes": 0,
                    "peak_flows": []
                }
            
            impact_by_type[wave_type]["count"] += 1
            impact_by_type[wave_type]["passengers"] += wave.total_passengers
            impact_by_type[wave_type]["congestion_minutes"] += wave.congestion_duration or 0
            impact_by_type[wave_type]["peak_flows"].append(wave.peak_flow_rate)
        
        # Calculate averages
        for wave_type, data in impact_by_type.items():
            if data["count"] > 0:
                data["average_passengers"] = data["passengers"] / data["count"]
                data["average_congestion"] = data["congestion_minutes"] / data["count"]
                data["average_peak_flow"] = sum(data["peak_flows"]) / len(data["peak_flows"])
        
        return {
            "period_hours": hours_back,
            "total_waves": total_waves,
            "total_passengers": total_passengers,
            "total_congestion_minutes": total_congestion_minutes,
            "impact_by_type": impact_by_type,
            "average_wave_duration": total_congestion_minutes / max(total_waves, 1),
            "peak_congestion_duration": max([w.congestion_duration or 0 for w in recent_waves])
        }


# Global instance
passenger_wave_detection = PassengerWaveDetectionEngine()
