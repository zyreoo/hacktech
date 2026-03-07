"""
Queue State Engine.

Real-time queue state management and tracking:
- Maintain real-time queue length per checkpoint
- Track security, check-in, boarding, immigration queues
- Performance metrics and KPI tracking
- Alert threshold management
"""

import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    QueueState, QueueEvent, QueuePrediction, LaneRecommendation, Flight
)
from ..database import SessionLocal


class QueueStateEngine:
    """Real-time queue state management and tracking system."""
    
    def __init__(self):
        self.checkpoint_configs = {
            "security": {
                "max_capacity": 50,
                "alert_threshold_length": 30,
                "alert_threshold_wait": 15,
                "default_lanes": 3,
                "service_time_minutes": 2.0
            },
            "checkin": {
                "max_capacity": 30,
                "alert_threshold_length": 20,
                "alert_threshold_wait": 10,
                "default_lanes": 2,
                "service_time_minutes": 3.0
            },
            "boarding": {
                "max_capacity": 100,
                "alert_threshold_length": 50,
                "alert_threshold_wait": 20,
                "default_lanes": 2,
                "service_time_minutes": 0.5
            },
            "immigration": {
                "max_capacity": 40,
                "alert_threshold_length": 25,
                "alert_threshold_wait": 12,
                "default_lanes": 4,
                "service_time_minutes": 1.5
            }
        }
        
        self.state_cache = {}  # In-memory cache for real-time access
        self.cache_lock = threading.Lock()
    
    def update_queue_state(self, db: Session, event: QueueEvent) -> QueueState:
        """Update queue state based on new event."""
        
        checkpoint_id = event.checkpoint_id
        
        # Get existing state or create new one
        state = db.query(QueueState).filter(
            QueueState.checkpoint_id == checkpoint_id
        ).first()
        
        if not state:
            state = self._create_initial_state(db, event)
        else:
            state = self._update_existing_state(db, state, event)
        
        # Update cache
        with self.cache_lock:
            self.state_cache[checkpoint_id] = {
                "state": state,
                "last_updated": datetime.utcnow()
            }
        
        # Check for alerts
        self._check_alert_conditions(db, state)
        
        # Update predictions
        self._update_predictions(db, state)
        
        return state
    
    def get_current_state(self, db: Session, checkpoint_id: str) -> Optional[QueueState]:
        """Get current state for a checkpoint."""
        
        # Check cache first
        with self.cache_lock:
            if checkpoint_id in self.state_cache:
                cached = self.state_cache[checkpoint_id]
                # Cache is valid for 30 seconds
                if (datetime.utcnow() - cached["last_updated"]).seconds < 30:
                    return cached["state"]
        
        # Get from database
        state = db.query(QueueState).filter(
            QueueState.checkpoint_id == checkpoint_id
        ).first()
        
        # Update cache
        if state:
            with self.cache_lock:
                self.state_cache[checkpoint_id] = {
                    "state": state,
                    "last_updated": datetime.utcnow()
                }
        
        return state
    
    def get_all_states(self, db: Session, terminal: Optional[str] = None, 
                      checkpoint_type: Optional[str] = None) -> List[QueueState]:
        """Get all current queue states, optionally filtered."""
        
        query = db.query(QueueState)
        
        if terminal:
            query = query.filter(QueueState.terminal == terminal)
        
        if checkpoint_type:
            query = query.filter(QueueState.checkpoint_type == checkpoint_type)
        
        return query.order_by(QueueState.last_updated.desc()).all()
    
    def get_critical_queues(self, db: Session) -> List[QueueState]:
        """Get queues in critical state."""
        
        return db.query(QueueState).filter(
            or_(
                QueueState.current_queue_length > QueueState.alert_threshold_length,
                QueueState.current_wait_time > QueueState.alert_threshold_wait
            )
        ).order_by(QueueState.current_wait_time.desc()).all()
    
    def get_queue_metrics(self, db: Session, checkpoint_id: str, 
                         hours_back: int = 24) -> Dict:
        """Get comprehensive metrics for a checkpoint."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Get recent events
        events = db.query(QueueEvent).filter(
            QueueEvent.checkpoint_id == checkpoint_id,
            QueueEvent.event_timestamp >= cutoff_time
        ).order_by(QueueEvent.event_timestamp.desc()).all()
        
        if not events:
            return {"error": "No data available for specified period"}
        
        # Calculate metrics
        queue_lengths = [e.current_queue_length for e in events]
        wait_times = [e.average_wait_time for e in events]
        utilization_rates = [e.capacity_utilization for e in events]
        
        return {
            "checkpoint_id": checkpoint_id,
            "period_hours": hours_back,
            "total_events": len(events),
            "queue_metrics": {
                "average_length": sum(queue_lengths) / len(queue_lengths),
                "max_length": max(queue_lengths),
                "min_length": min(queue_lengths),
                "current_length": queue_lengths[0] if queue_lengths else 0
            },
            "wait_time_metrics": {
                "average_wait": sum(wait_times) / len(wait_times),
                "max_wait": max(wait_times),
                "min_wait": min(wait_times),
                "current_wait": wait_times[0] if wait_times else 0
            },
            "utilization_metrics": {
                "average_utilization": sum(utilization_rates) / len(utilization_rates),
                "max_utilization": max(utilization_rates),
                "min_utilization": min(utilization_rates),
                "current_utilization": utilization_rates[0] if utilization_rates else 0
            },
            "congestion_distribution": {
                level: len([e for e in events if e.congestion_level == level])
                for level in ["low", "medium", "high", "critical"]
            },
            "trend_analysis": {
                "increasing": len([e for e in events if e.trend_direction == "increasing"]),
                "stable": len([e for e in events if e.trend_direction == "stable"]),
                "decreasing": len([e for e in events if e.trend_direction == "decreasing"])
            }
        }
    
    def update_lane_status(self, db: Session, checkpoint_id: str, 
                        lane_updates: Dict) -> QueueState:
        """Update lane status for a checkpoint."""
        
        state = self.get_current_state(db, checkpoint_id)
        if not state:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        # Update lane status
        current_lane_status = json.loads(state.lane_status or "{}")
        current_lane_status.update(lane_updates)
        
        state.lane_status = json.dumps(current_lane_status)
        state.active_lanes = len([
            lane for lane, status in current_lane_status.items() 
            if status.get("status") == "active"
        ])
        state.last_updated = datetime.utcnow()
        
        db.commit()
        
        # Update cache
        with self.cache_lock:
            if checkpoint_id in self.state_cache:
                self.state_cache[checkpoint_id]["state"] = state
                self.state_cache[checkpoint_id]["last_updated"] = datetime.utcnow()
        
        return state
    
    def _create_initial_state(self, db: Session, event: QueueEvent) -> QueueState:
        """Create initial queue state from first event."""
        
        config = self.checkpoint_configs.get(event.checkpoint_type, self.checkpoint_configs["security"])
        
        state = QueueState(
            checkpoint_id=event.checkpoint_id,
            checkpoint_type=event.checkpoint_type,
            terminal=event.terminal,
            gate=event.gate,
            current_queue_length=event.current_queue_length,
            current_wait_time=event.average_wait_time,
            current_capacity_utilization=event.capacity_utilization,
            total_lanes=config["default_lanes"],
            active_lanes=config["default_lanes"],
            lane_status=json.dumps({
                f"lane_{i+1}": {"status": "active", "queue_length": 0}
                for i in range(config["default_lanes"])
            }),
            average_service_time=config["service_time_minutes"],
            peak_queue_length=event.current_queue_length,
            total_processed_today=0,
            alert_threshold_length=config["alert_threshold_length"],
            alert_threshold_wait=config["alert_threshold_wait"],
            last_updated=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        db.add(state)
        db.flush()
        
        return state
    
    def _update_existing_state(self, db: Session, state: QueueState, event: QueueEvent) -> QueueState:
        """Update existing state with new event data."""
        
        # Update core metrics
        state.current_queue_length = event.current_queue_length
        state.current_wait_time = event.average_wait_time
        state.current_capacity_utilization = event.capacity_utilization
        
        # Update peak values
        state.peak_queue_length = max(state.peak_queue_length, event.current_queue_length)
        
        # Update processed count
        if event.service_rate > 0:
            # Estimate passengers processed since last update
            time_diff = (event.event_timestamp - state.last_updated).total_seconds() / 60
            processed = int(event.service_rate * time_diff)
            state.total_processed_today += processed
        
        # Update lane status if provided
        if event.lane_id:
            lane_status = json.loads(state.lane_status or "{}")
            if event.lane_id in lane_status:
                lane_status[event.lane_id]["queue_length"] = event.current_queue_length
                lane_status[event.lane_id]["last_update"] = event.event_timestamp.isoformat()
            state.lane_status = json.dumps(lane_status)
        
        state.last_updated = datetime.utcnow()
        
        return state
    
    def _check_alert_conditions(self, db: Session, state: QueueState):
        """Check if alert conditions are met and create recommendations."""
        
        current_time = datetime.utcnow()
        
        # Check if we should alert (avoid alert spam)
        if state.last_alert_time:
            time_since_last_alert = (current_time - state.last_alert_time).total_seconds() / 60
            if time_since_last_alert < 10:  # Don't alert more than once every 10 minutes
                return
        
        # Check threshold conditions
        length_alert = state.current_queue_length > state.alert_threshold_length
        wait_alert = state.current_wait_time > state.alert_threshold_wait
        
        if length_alert or wait_alert:
            # Create lane recommendation
            recommendation = self._create_lane_recommendation(db, state, length_alert, wait_alert)
            db.add(recommendation)
            
            # Update last alert time
            state.last_alert_time = current_time
    
    def _update_predictions(self, db: Session, state: QueueState):
        """Update short-term predictions for the queue."""
        
        # Get recent predictions
        existing_predictions = db.query(QueuePrediction).filter(
            QueuePrediction.checkpoint_id == state.checkpoint_id,
            QueuePrediction.target_timestamp > datetime.utcnow()
        ).all()
        
        # Generate new predictions if needed
        prediction_horizons = [10, 20, 30]  # minutes
        
        for horizon in prediction_horizons:
            # Check if we already have a recent prediction for this horizon
            recent_prediction = [
                p for p in existing_predictions 
                if p.prediction_horizon == horizon and 
                (datetime.utcnow() - p.prediction_timestamp).total_seconds() < 300  # 5 minutes old
            ]
            
            if not recent_prediction:
                prediction = self._generate_prediction(db, state, horizon)
                db.add(prediction)
    
    def _create_lane_recommendation(self, db: Session, state: QueueState, 
                                length_alert: bool, wait_alert: bool) -> LaneRecommendation:
        """Create lane management recommendation."""
        
        recommendation_id = f"LR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{state.checkpoint_id[:8].upper()}"
        
        # Determine recommendation type and priority
        if length_alert and wait_alert:
            recommendation_type = "open_lane"
            priority_level = "critical"
            recommended_lanes = min(state.total_lanes, state.active_lanes + 1)
        elif length_alert:
            recommendation_type = "open_lane"
            priority_level = "high"
            recommended_lanes = min(state.total_lanes, state.active_lanes + 1)
        elif state.active_lanes > 1 and state.current_capacity_utilization < 0.3:
            recommendation_type = "close_lane"
            priority_level = "low"
            recommended_lanes = max(1, state.active_lanes - 1)
        else:
            recommendation_type = "reconfigure"
            priority_level = "medium"
            recommended_lanes = state.active_lanes
        
        # Generate recommendation details
        if recommendation_type == "open_lane":
            action = f"Open additional lane. Current: {state.active_lanes}, Recommended: {recommended_lanes}"
            impact = f"Expected reduction in wait time: {int(state.current_wait_time * 0.4)} minutes"
        elif recommendation_type == "close_lane":
            action = f"Close underutilized lane. Current: {state.active_lanes}, Recommended: {recommended_lanes}"
            impact = f"Resource savings while maintaining service level"
        else:
            action = f"Reconfigure lane assignment. Current: {state.active_lanes}, Recommended: {recommended_lanes}"
            impact = f"Optimize resource utilization"
        
        return LaneRecommendation(
            recommendation_id=recommendation_id,
            checkpoint_id=state.checkpoint_id,
            recommendation_type=recommendation_type,
            current_lanes=state.total_lanes,
            active_lanes=state.active_lanes,
            current_queue_length=state.current_queue_length,
            current_wait_time=state.current_wait_time,
            recommended_lanes=recommended_lanes,
            recommended_action=action,
            priority_level=priority_level,
            impact_assessment=impact,
            trigger_metric="queue_length" if length_alert else "wait_time",
            trigger_value=state.current_queue_length if length_alert else state.current_wait_time,
            threshold_exceeded=True,
            recommended_by="automated_system",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    def _generate_prediction(self, db: Session, state: QueueState, horizon_minutes: int) -> QueuePrediction:
        """Generate queue prediction for specified horizon."""
        
        # Get contributing flights
        future_time = datetime.utcnow() + timedelta(minutes=horizon_minutes)
        contributing_flights = db.query(Flight).filter(
            Flight.scheduled_time >= datetime.utcnow(),
            Flight.scheduled_time <= future_time,
            Flight.terminal == state.terminal
        ).all()
        
        # Simple prediction model based on current state and flight schedule
        base_prediction = state.current_queue_length
        
        # Adjust based on flight departures
        flight_impact = len(contributing_flights) * 5  # Assume 5 passengers per flight
        predicted_length = max(0, base_prediction + flight_impact)
        
        # Adjust based on historical patterns
        hour_of_day = future_time.hour
        historical_factor = self._get_historical_factor(db, state.checkpoint_id, hour_of_day)
        predicted_length *= historical_factor
        
        # Calculate predicted wait time
        config = self.checkpoint_configs.get(state.checkpoint_type, self.checkpoint_configs["security"])
        service_rate = 60 / config["service_time_minutes"]  # passengers per hour
        predicted_wait = int(predicted_length / max(service_rate / 60, 0.1))
        
        # Calculate confidence
        confidence = max(0.3, min(0.9, 1.0 - (horizon_minutes / 60)))  # Decreases with horizon
        
        return QueuePrediction(
            checkpoint_id=state.checkpoint_id,
            prediction_horizon=horizon_minutes,
            model_version="v1.0",
            current_queue_length=state.current_queue_length,
            current_wait_time=state.current_wait_time,
            flight_schedules=json.dumps([{
                "flight_id": f.id,
                "scheduled_time": f.scheduled_time.isoformat(),
                "passengers": f.passenger_count
            } for f in contributing_flights]),
            historical_patterns=json.dumps({
                "hour_of_day": hour_of_day,
                "factor": historical_factor
            }),
            predicted_queue_length=int(predicted_length),
            predicted_wait_time=predicted_wait,
            confidence_score=confidence,
            prediction_range=json.dumps({
                "min": int(predicted_length * 0.8),
                "max": int(predicted_length * 1.2),
                "std": int(predicted_length * 0.2)
            }),
            prediction_timestamp=datetime.utcnow(),
            target_timestamp=future_time,
            created_at=datetime.utcnow()
        )
    
    def _get_historical_factor(self, db: Session, checkpoint_id: str, hour_of_day: int) -> float:
        """Get historical adjustment factor for time of day."""
        
        # Get historical averages for this hour
        historical_avg = db.query(func.avg(QueueEvent.current_queue_length)).filter(
            QueueEvent.checkpoint_id == checkpoint_id,
            func.extract('hour', QueueEvent.event_timestamp) == hour_of_day
        ).scalar()
        
        if not historical_avg:
            return 1.0
        
        # Get overall average for comparison
        overall_avg = db.query(func.avg(QueueEvent.current_queue_length)).filter(
            QueueEvent.checkpoint_id == checkpoint_id
        ).scalar()
        
        if not overall_avg:
            return 1.0
        
        return historical_avg / overall_avg
    
    def get_lane_efficiency_metrics(self, db: Session, checkpoint_id: str) -> Dict:
        """Get lane efficiency metrics for a checkpoint."""
        
        state = self.get_current_state(db, checkpoint_id)
        if not state:
            return {"error": "Checkpoint not found"}
        
        lane_status = json.loads(state.lane_status or "{}")
        
        # Calculate metrics per lane
        lane_metrics = {}
        total_queue = 0
        active_lanes = 0
        
        for lane_id, lane_info in lane_status.items():
            queue_length = lane_info.get("queue_length", 0)
            status = lane_info.get("status", "inactive")
            
            total_queue += queue_length
            if status == "active":
                active_lanes += 1
            
            lane_metrics[lane_id] = {
                "queue_length": queue_length,
                "status": status,
                "utilization": queue_length / max(state.current_queue_length, 1)
            }
        
        return {
            "checkpoint_id": checkpoint_id,
            "total_lanes": state.total_lanes,
            "active_lanes": active_lanes,
            "total_queue_length": total_queue,
            "average_queue_per_lane": total_queue / max(active_lanes, 1),
            "lane_balance_score": self._calculate_lane_balance(lane_metrics),
            "lane_utilization": {
                lane_id: metrics["utilization"]
                for lane_id, metrics in lane_metrics.items()
            }
        }
    
    def _calculate_lane_balance(self, lane_metrics: Dict) -> float:
        """Calculate how balanced the queue distribution is across lanes."""
        
        if not lane_metrics:
            return 1.0
        
        utilizations = [
            metrics["utilization"] 
            for metrics in lane_metrics.values() 
            if metrics.get("status") == "active"
        ]
        
        if not utilizations:
            return 1.0
        
        # Calculate coefficient of variation (lower is more balanced)
        mean_utilization = sum(utilizations) / len(utilizations)
        variance = sum((u - mean_utilization) ** 2 for u in utilizations) / len(utilizations)
        std_deviation = variance ** 0.5
        
        # Convert to balance score (0-1, higher is better)
        cv = std_deviation / max(mean_utilization, 0.1)
        balance_score = max(0, 1 - cv)
        
        return balance_score


# Global instance
queue_state_engine = QueueStateEngine()
