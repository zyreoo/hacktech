"""
Queue Prediction Models.

Advanced queue prediction system:
- Short-term queue prediction (10, 20, 30 minutes)
- Flight schedule integration
- Historical pattern analysis
- Machine learning prediction models
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    QueueState, QueueEvent, QueuePrediction, Flight
)
from ..database import SessionLocal


class QueuePredictionEngine:
    """Advanced queue prediction and forecasting system."""
    
    def __init__(self):
        self.prediction_models = {
            "linear_trend": self._linear_trend_prediction,
            "historical_average": self._historical_average_prediction,
            "flight_based": self._flight_based_prediction,
            "ml_ensemble": self._ml_ensemble_prediction
        }
        
        self.horizon_weights = {
            10: 0.9,   # High confidence for short-term
            20: 0.7,   # Medium confidence
            30: 0.5    # Lower confidence for longer-term
        }
        
        self.seasonal_patterns = {
            "morning_peak": {"start": 6, "end": 9, "multiplier": 1.5},
            "midday_peak": {"start": 11, "end": 14, "multiplier": 1.3},
            "evening_peak": {"start": 17, "end": 20, "multiplier": 1.4},
            "night_low": {"start": 22, "end": 5, "multiplier": 0.6}
        }
    
    def predict_queue_state(self, db: Session, checkpoint_id: str, 
                        horizons: List[int] = [10, 20, 30]) -> List[QueuePrediction]:
        """Generate queue predictions for specified time horizons."""
        
        # Get current state
        current_state = db.query(QueueState).filter(
            QueueState.checkpoint_id == checkpoint_id
        ).first()
        
        if not current_state:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        predictions = []
        
        for horizon in horizons:
            # Generate prediction using ensemble of models
            prediction = self._generate_ensemble_prediction(db, current_state, horizon)
            predictions.append(prediction)
        
        return predictions
    
    def predict_congestion_windows(self, db: Session, checkpoint_id: str, 
                                hours_ahead: int = 4) -> List[Dict]:
        """Predict future congestion windows for a checkpoint."""
        
        # Get current state
        current_state = db.query(QueueState).filter(
            QueueState.checkpoint_id == checkpoint_id
        ).first()
        
        if not current_state:
            return []
        
        # Get flight schedule for next few hours
        future_time = datetime.utcnow() + timedelta(hours=hours_ahead)
        contributing_flights = db.query(Flight).filter(
            Flight.scheduled_time >= datetime.utcnow(),
            Flight.scheduled_time <= future_time,
            Flight.terminal == current_state.terminal
        ).order_by(Flight.scheduled_time).all()
        
        # Analyze flight clustering
        congestion_windows = []
        current_window = []
        
        for flight in contributing_flights:
            flight_time = flight.scheduled_time
            
            # Check if this flight starts a new window
            if not current_window or (flight_time - current_window[-1]["time"]).total_seconds() > 1800:  # 30 minutes
                if current_window:
                    # Analyze completed window
                    window_analysis = self._analyze_congestion_window(current_window, current_state)
                    congestion_windows.append(window_analysis)
                
                # Start new window
                current_window = [{"flight": flight, "time": flight_time, "passengers": flight.passenger_count}]
            else:
                current_window.append({"flight": flight, "time": flight_time, "passengers": flight.passenger_count})
        
        # Don't forget the last window
        if current_window:
            window_analysis = self._analyze_congestion_window(current_window, current_state)
            congestion_windows.append(window_analysis)
        
        return congestion_windows
    
    def get_prediction_accuracy(self, db: Session, checkpoint_id: str, 
                           hours_back: int = 24) -> Dict:
        """Calculate prediction accuracy metrics."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Get evaluated predictions
        predictions = db.query(QueuePrediction).filter(
            QueuePrediction.checkpoint_id == checkpoint_id,
            QueuePrediction.evaluated_at.isnot(None),
            QueuePrediction.prediction_timestamp >= cutoff_time
        ).all()
        
        if not predictions:
            return {"error": "No evaluated predictions found"}
        
        # Calculate accuracy metrics
        total_predictions = len(predictions)
        accurate_predictions = 0
        total_error = 0
        horizon_accuracy = {10: [], 20: [], 30: []}
        
        for pred in predictions:
            if pred.actual_queue_length is not None:
                # Calculate absolute error
                error = abs(pred.predicted_queue_length - pred.actual_queue_length)
                total_error += error
                
                # Check if within acceptable range (±20%)
                acceptable_range = pred.predicted_queue_length * 0.2
                if error <= acceptable_range:
                    accurate_predictions += 1
                
                # Track by horizon
                if pred.prediction_horizon in horizon_accuracy:
                    horizon_accuracy[pred.prediction_horizon].append(error)
        
        # Calculate metrics
        overall_accuracy = (accurate_predictions / total_predictions) * 100 if total_predictions > 0 else 0
        mae = total_error / total_predictions if total_predictions > 0 else 0  # Mean Absolute Error
        
        horizon_stats = {}
        for horizon, errors in horizon_accuracy.items():
            horizon_stats[horizon] = {
                "mae": sum(errors) / len(errors) if errors else 0,
                "accuracy": len([e for e in errors if e <= 10]) / len(errors) * 100 if errors else 0
            }
        
        return {
            "checkpoint_id": checkpoint_id,
            "period_hours": hours_back,
            "total_predictions": total_predictions,
            "accurate_predictions": accurate_predictions,
            "overall_accuracy": round(overall_accuracy, 1),
            "mean_absolute_error": round(mae, 1),
            "horizon_accuracy": horizon_stats
        }
    
    def update_prediction_accuracy(self, db: Session, checkpoint_id: str, 
                              actual_queue_length: int, actual_wait_time: int):
        """Update predictions with actual values for accuracy tracking."""
        
        # Get pending predictions for this checkpoint
        pending_predictions = db.query(QueuePrediction).filter(
            QueuePrediction.checkpoint_id == checkpoint_id,
            QueuePrediction.target_timestamp <= datetime.utcnow(),
            QueuePrediction.evaluated_at.is_(None)
        ).all()
        
        for prediction in pending_predictions:
            # Update with actual values
            prediction.actual_queue_length = actual_queue_length
            prediction.actual_wait_time = actual_wait_time
            prediction.prediction_error = abs(prediction.predicted_queue_length - actual_queue_length)
            prediction.evaluated_at = datetime.utcnow()
        
        db.commit()
    
    def _generate_ensemble_prediction(self, db: Session, state: QueueState, horizon_minutes: int) -> QueuePrediction:
        """Generate ensemble prediction using multiple models."""
        
        # Get predictions from all models
        model_predictions = {}
        
        for model_name, model_func in self.prediction_models.items():
            try:
                prediction = model_func(db, state, horizon_minutes)
                model_predictions[model_name] = prediction
            except Exception as e:
                print(f"Model {model_name} failed: {e}")
                continue
        
        # Weight ensemble based on historical performance
        # For now, use simple averaging
        if not model_predictions:
            # Fallback to simple trend prediction
            prediction = self._linear_trend_prediction(db, state, horizon_minutes)
        else:
            # Ensemble averaging
            total_weight = 0
            weighted_prediction = 0
            weighted_confidence = 0
            
            for model_name, pred in model_predictions.items():
                weight = self.horizon_weights.get(horizon_minutes, 0.5)
                weighted_prediction += pred["predicted_length"] * weight
                weighted_confidence += pred["confidence"] * weight
                total_weight += weight
            
            if total_weight > 0:
                weighted_prediction /= total_weight
                weighted_confidence /= total_weight
            
            prediction = {
                "predicted_length": int(weighted_prediction),
                "predicted_wait": int(weighted_prediction / max(state.average_service_time or 2.0, 0.1)),
                "confidence": weighted_confidence
            }
        
        # Create prediction record
        future_time = datetime.utcnow() + timedelta(minutes=horizon_minutes)
        
        return QueuePrediction(
            checkpoint_id=state.checkpoint_id,
            prediction_horizon=horizon_minutes,
            model_version="ensemble_v1.0",
            current_queue_length=state.current_queue_length,
            current_wait_time=state.current_wait_time,
            flight_schedules=json.dumps(self._get_flight_schedule(db, state, horizon_minutes)),
            historical_patterns=json.dumps(self._get_historical_patterns(db, state, horizon_minutes)),
            predicted_queue_length=prediction["predicted_length"],
            predicted_wait_time=prediction["predicted_wait"],
            confidence_score=prediction["confidence"],
            prediction_range=json.dumps({
                "min": int(prediction["predicted_length"] * 0.8),
                "max": int(prediction["predicted_length"] * 1.2),
                "std": int(prediction["predicted_length"] * 0.15)
            }),
            prediction_timestamp=datetime.utcnow(),
            target_timestamp=future_time,
            created_at=datetime.utcnow()
        )
    
    def _linear_trend_prediction(self, db: Session, state: QueueState, horizon_minutes: int) -> Dict:
        """Simple linear trend-based prediction."""
        
        # Get recent events to calculate trend
        recent_events = db.query(QueueEvent).filter(
            QueueEvent.checkpoint_id == state.checkpoint_id,
            QueueEvent.event_timestamp >= datetime.utcnow() - timedelta(minutes=30)
        ).order_by(QueueEvent.event_timestamp.desc()).limit(5).all()
        
        if len(recent_events) < 2:
            # No trend data, use current state
            return {
                "predicted_length": state.current_queue_length,
                "predicted_wait": state.current_wait_time,
                "confidence": 0.5
            }
        
        # Calculate trend
        lengths = [e.current_queue_length for e in recent_events]
        times = [(datetime.utcnow() - e.event_timestamp).total_seconds() / 60 for e in recent_events]
        
        # Simple linear regression
        n = len(lengths)
        sum_x = sum(times)
        sum_y = sum(lengths)
        sum_xy = sum(x * y for x, y in zip(times, lengths))
        sum_x2 = sum(x * x for x in times)
        
        # Calculate slope (trend)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        
        # Predict future value
        predicted_length = max(0, state.current_queue_length + slope * horizon_minutes)
        predicted_wait = int(predicted_length / max(state.average_service_time or 2.0, 0.1))
        
        # Confidence based on trend consistency
        confidence = max(0.3, min(0.8, 1.0 - abs(slope) * 0.1))
        
        return {
            "predicted_length": int(predicted_length),
            "predicted_wait": predicted_wait,
            "confidence": confidence
        }
    
    def _historical_average_prediction(self, db: Session, state: QueueState, horizon_minutes: int) -> Dict:
        """Historical average-based prediction."""
        
        future_time = datetime.utcnow() + timedelta(minutes=horizon_minutes)
        hour_of_day = future_time.hour
        day_of_week = future_time.weekday()
        
        # Get historical averages for this time
        historical_avg = db.query(func.avg(QueueEvent.current_queue_length)).filter(
            QueueEvent.checkpoint_id == state.checkpoint_id,
            func.extract('hour', QueueEvent.event_timestamp) == hour_of_day,
            func.extract('dow', QueueEvent.event_timestamp) == day_of_week
        ).scalar()
        
        if not historical_avg:
            historical_avg = state.current_queue_length
        
        # Apply seasonal adjustment
        seasonal_factor = self._get_seasonal_factor(hour_of_day)
        predicted_length = historical_avg * seasonal_factor
        
        # Add current trend
        trend_adjustment = self._get_current_trend(db, state.checkpoint_id)
        predicted_length += trend_adjustment * horizon_minutes
        
        predicted_wait = int(predicted_length / max(state.average_service_time or 2.0, 0.1))
        
        return {
            "predicted_length": int(predicted_length),
            "predicted_wait": predicted_wait,
            "confidence": 0.7
        }
    
    def _flight_based_prediction(self, db: Session, state: QueueState, horizon_minutes: int) -> Dict:
        """Flight schedule-based prediction."""
        
        future_time = datetime.utcnow() + timedelta(minutes=horizon_minutes)
        
        # Get flights departing in the prediction window
        contributing_flights = db.query(Flight).filter(
            Flight.scheduled_time >= datetime.utcnow(),
            Flight.scheduled_time <= future_time,
            Flight.terminal == state.terminal
        ).all()
        
        # Calculate passenger impact
        total_passengers = sum(flight.passenger_count for flight in contributing_flights)
        
        # Base prediction on current state plus flight impact
        base_decay = max(0, state.current_queue_length - (horizon_minutes * 0.5))  # Assume natural decay
        flight_impact = total_passengers * 0.3  # Assume 30% of passengers affect queue
        
        predicted_length = base_decay + flight_impact
        predicted_wait = int(predicted_length / max(state.average_service_time or 2.0, 0.1))
        
        # Confidence based on flight schedule reliability
        confidence = min(0.9, 0.6 + len(contributing_flights) * 0.1)
        
        return {
            "predicted_length": int(predicted_length),
            "predicted_wait": predicted_wait,
            "confidence": confidence
        }
    
    def _ml_ensemble_prediction(self, db: Session, state: QueueState, horizon_minutes: int) -> Dict:
        """Machine learning ensemble prediction (simplified for demo)."""
        
        # For demo purposes, use a weighted combination of other models
        # In production, this would use trained ML models
        
        linear_pred = self._linear_trend_prediction(db, state, horizon_minutes)
        historical_pred = self._historical_average_prediction(db, state, horizon_minutes)
        flight_pred = self._flight_based_prediction(db, state, horizon_minutes)
        
        # Weight based on horizon
        if horizon_minutes <= 10:
            # Short term: favor trend and flight data
            weights = {"linear": 0.4, "historical": 0.2, "flight": 0.4}
        elif horizon_minutes <= 20:
            # Medium term: balanced approach
            weights = {"linear": 0.3, "historical": 0.4, "flight": 0.3}
        else:
            # Long term: favor historical patterns
            weights = {"linear": 0.2, "historical": 0.5, "flight": 0.3}
        
        # Calculate weighted prediction
        weighted_length = (
            linear_pred["predicted_length"] * weights["linear"] +
            historical_pred["predicted_length"] * weights["historical"] +
            flight_pred["predicted_length"] * weights["flight"]
        )
        
        weighted_wait = (
            linear_pred["predicted_wait"] * weights["linear"] +
            historical_pred["predicted_wait"] * weights["historical"] +
            flight_pred["predicted_wait"] * weights["flight"]
        )
        
        weighted_confidence = (
            linear_pred["confidence"] * weights["linear"] +
            historical_pred["confidence"] * weights["historical"] +
            flight_pred["confidence"] * weights["flight"]
        )
        
        return {
            "predicted_length": int(weighted_length),
            "predicted_wait": int(weighted_wait),
            "confidence": weighted_confidence
        }
    
    def _get_flight_schedule(self, db: Session, state: QueueState, horizon_minutes: int) -> List[Dict]:
        """Get flight schedule for prediction window."""
        
        future_time = datetime.utcnow() + timedelta(minutes=horizon_minutes)
        
        flights = db.query(Flight).filter(
            Flight.scheduled_time >= datetime.utcnow(),
            Flight.scheduled_time <= future_time,
            Flight.terminal == state.terminal
        ).order_by(Flight.scheduled_time).limit(10).all()
        
        return [{
            "flight_id": flight.id,
            "flight_number": flight.flight_number,
            "scheduled_time": flight.scheduled_time.isoformat(),
            "passenger_count": flight.passenger_count,
            "gate": flight.gate,
            "destination": flight.destination
        } for flight in flights]
    
    def _get_historical_patterns(self, db: Session, state: QueueState, horizon_minutes: int) -> Dict:
        """Get historical patterns for prediction."""
        
        future_time = datetime.utcnow() + timedelta(minutes=horizon_minutes)
        hour_of_day = future_time.hour
        day_of_week = future_time.weekday()
        
        # Get historical statistics
        historical_stats = db.query(
            func.avg(QueueEvent.current_queue_length).label('avg_length'),
            func.min(QueueEvent.current_queue_length).label('min_length'),
            func.max(QueueEvent.current_queue_length).label('max_length'),
            func.count(QueueEvent.id).label('sample_count')
        ).filter(
            QueueEvent.checkpoint_id == state.checkpoint_id,
            func.extract('hour', QueueEvent.event_timestamp) == hour_of_day,
            func.extract('dow', QueueEvent.event_timestamp) == day_of_week
        ).first()
        
        if not historical_stats:
            return {"hour": hour_of_day, "day": day_of_week, "sample_count": 0}
        
        return {
            "hour": hour_of_day,
            "day": day_of_week,
            "avg_length": round(historical_stats.avg_length or 0, 1),
            "min_length": historical_stats.min_length or 0,
            "max_length": historical_stats.max_length or 0,
            "sample_count": historical_stats.sample_count,
            "seasonal_factor": self._get_seasonal_factor(hour_of_day)
        }
    
    def _get_seasonal_factor(self, hour_of_day: int) -> float:
        """Get seasonal adjustment factor for hour of day."""
        
        for pattern_name, pattern in self.seasonal_patterns.items():
            if pattern["start"] <= hour_of_day <= pattern["end"]:
                return pattern["multiplier"]
        
        # Handle overnight wrap-around
        if hour_of_day >= 22 or hour_of_day <= 5:
            return self.seasonal_patterns["night_low"]["multiplier"]
        
        return 1.0  # Default no adjustment
    
    def _get_current_trend(self, db: Session, checkpoint_id: str) -> float:
        """Get current trend direction and magnitude."""
        
        recent_events = db.query(QueueEvent).filter(
            QueueEvent.checkpoint_id == checkpoint_id,
            QueueEvent.event_timestamp >= datetime.utcnow() - timedelta(minutes=15)
        ).order_by(QueueEvent.event_timestamp.desc()).limit(3).all()
        
        if len(recent_events) < 2:
            return 0.0
        
        # Calculate simple trend
        current = recent_events[0].current_queue_length
        previous = recent_events[1].current_queue_length
        
        trend = (current - previous) / max(previous, 1)
        return trend
    
    def _analyze_congestion_window(self, window_flights: List[Dict], current_state: QueueState) -> Dict:
        """Analyze a congestion window created by clustered flights."""
        
        if not window_flights:
            return {}
        
        start_time = window_flights[0]["time"]
        end_time = window_flights[-1]["time"]
        total_passengers = sum(f["passengers"] for f in window_flights)
        
        # Calculate peak impact
        peak_passengers_per_minute = total_passengers / max((end_time - start_time).total_seconds() / 60, 1)
        
        # Estimate peak queue length
        checkpoint_config = {
            "security": 2.0, "checkin": 3.0, "boarding": 0.5, "immigration": 1.5
        }.get(current_state.checkpoint_type, 2.0)
        
        estimated_peak_length = peak_passengers_per_minute * checkpoint_config
        
        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_minutes": int((end_time - start_time).total_seconds() / 60),
            "flight_count": len(window_flights),
            "total_passengers": total_passengers,
            "peak_flow_rate": peak_passengers_per_minute,
            "estimated_peak_queue": int(estimated_peak_length),
            "flights": [f["flight"].flight_number for f in window_flights]
        }


# Global instance
queue_prediction = QueuePredictionEngine()
