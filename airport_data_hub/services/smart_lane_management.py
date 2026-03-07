"""
Smart Lane Management System.

Intelligent lane recommendation and management:
- Lane opening/closing recommendations
- Threshold-based triggers
- Impact assessment and optimization
- Real-time lane configuration
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    QueueState, LaneRecommendation, QueueEvent, Flight
)
from ..database import SessionLocal


class SmartLaneManagementEngine:
    """Intelligent lane management and recommendation system."""
    
    def __init__(self):
        self.lane_configurations = {
            "security": {
                "min_lanes": 1,
                "max_lanes": 6,
                "optimal_capacity_per_lane": 15,
                "opening_cost_per_hour": 50,
                "closing_savings_per_hour": 30,
                "switch_time_minutes": 5
            },
            "checkin": {
                "min_lanes": 1,
                "max_lanes": 4,
                "optimal_capacity_per_lane": 10,
                "opening_cost_per_hour": 40,
                "closing_savings_per_hour": 25,
                "switch_time_minutes": 3
            },
            "boarding": {
                "min_lanes": 1,
                "max_lanes": 3,
                "optimal_capacity_per_lane": 50,
                "opening_cost_per_hour": 35,
                "closing_savings_per_hour": 20,
                "switch_time_minutes": 2
            },
            "immigration": {
                "min_lanes": 2,
                "max_lanes": 8,
                "optimal_capacity_per_lane": 12,
                "opening_cost_per_hour": 60,
                "closing_savings_per_hour": 40,
                "switch_time_minutes": 7
            }
        }
        
        self.threshold_rules = {
            "queue_length": {
                "critical": 0.9,
                "high": 0.7,
                "medium": 0.5,
                "low": 0.3
            },
            "wait_time": {
                "critical": 20,
                "high": 15,
                "medium": 10,
                "low": 5
            },
            "utilization": {
                "critical": 0.85,
                "high": 0.7,
                "medium": 0.5,
                "low": 0.3
            }
        }
    
    def analyze_lane_requirements(self, db: Session, checkpoint_id: str) -> Dict:
        """Analyze current lane requirements and generate recommendations."""
        
        # Get current state
        state = db.query(QueueState).filter(
            QueueState.checkpoint_id == checkpoint_id
        ).first()
        
        if not state:
            return {"error": "Checkpoint not found"}
        
        # Get configuration for checkpoint type
        config = self.lane_configurations.get(state.checkpoint_type, self.lane_configurations["security"])
        
        # Calculate current performance metrics
        current_metrics = self._calculate_performance_metrics(state, config)
        
        # Generate recommendations
        recommendations = []
        
        # Check for lane opening recommendations
        open_recommendation = self._evaluate_lane_opening(state, config, current_metrics)
        if open_recommendation:
            recommendations.append(open_recommendation)
        
        # Check for lane closing recommendations
        close_recommendation = self._evaluate_lane_closing(state, config, current_metrics)
        if close_recommendation:
            recommendations.append(close_recommendation)
        
        # Check for lane reconfiguration
        reconfig_recommendation = self._evaluate_lane_reconfiguration(state, config, current_metrics)
        if reconfig_recommendation:
            recommendations.append(reconfig_recommendation)
        
        return {
            "checkpoint_id": checkpoint_id,
            "checkpoint_type": state.checkpoint_type,
            "terminal": state.terminal,
            "current_state": {
                "total_lanes": state.total_lanes,
                "active_lanes": state.active_lanes,
                "current_queue_length": state.current_queue_length,
                "current_wait_time": state.current_wait_time,
                "utilization": state.current_capacity_utilization
            },
            "performance_metrics": current_metrics,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_lane_recommendation(self, db: Session, checkpoint_id: str, 
                                 recommendation_type: str, priority: str = "medium") -> LaneRecommendation:
        """Generate specific lane recommendation."""
        
        state = db.query(QueueState).filter(
            QueueState.checkpoint_id == checkpoint_id
        ).first()
        
        if not state:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        config = self.lane_configurations.get(state.checkpoint_type, self.lane_configurations["security"])
        
        recommendation_id = f"LR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
        
        if recommendation_type == "open_lane":
            recommendation = self._create_open_lane_recommendation(state, config, recommendation_id, priority)
        elif recommendation_type == "close_lane":
            recommendation = self._create_close_lane_recommendation(state, config, recommendation_id, priority)
        elif recommendation_type == "reconfigure":
            recommendation = self._create_reconfigure_recommendation(state, config, recommendation_id, priority)
        else:
            raise ValueError(f"Unsupported recommendation type: {recommendation_type}")
        
        db.add(recommendation)
        db.flush()
        
        return recommendation
    
    def implement_lane_recommendation(self, db: Session, recommendation_id: str, 
                                implemented_by: str) -> LaneRecommendation:
        """Mark a lane recommendation as implemented."""
        
        recommendation = db.query(LaneRecommendation).filter(
            LaneRecommendation.recommendation_id == recommendation_id
        ).first()
        
        if not recommendation:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        # Mark as implemented
        recommendation.implemented = True
        recommendation.implemented_at = datetime.utcnow()
        recommendation.implementation_result = json.dumps({
            "implemented_by": implemented_by,
            "implementation_time": datetime.utcnow().isoformat(),
            "status": "completed"
        })
        
        db.commit()
        return recommendation
    
    def evaluate_recommendation_effectiveness(self, db: Session, recommendation_id: str) -> Dict:
        """Evaluate the effectiveness of an implemented recommendation."""
        
        recommendation = db.query(LaneRecommendation).filter(
            LaneRecommendation.recommendation_id == recommendation_id
        ).first()
        
        if not recommendation or not recommendation.implemented:
            return {"error": "Recommendation not found or not implemented"}
        
        # Get state before and after implementation
        implementation_time = recommendation.implemented_at
        before_time = implementation_time - timedelta(minutes=10)
        after_time = implementation_time + timedelta(minutes=30)
        
        # Get queue events around implementation time
        before_event = db.query(QueueEvent).filter(
            QueueEvent.checkpoint_id == recommendation.checkpoint_id,
            QueueEvent.event_timestamp >= before_time - timedelta(minutes=5),
            QueueEvent.event_timestamp <= before_time + timedelta(minutes=5)
        ).order_by(QueueEvent.event_timestamp.desc()).first()
        
        after_event = db.query(QueueEvent).filter(
            QueueEvent.checkpoint_id == recommendation.checkpoint_id,
            QueueEvent.event_timestamp >= after_time - timedelta(minutes=5),
            QueueEvent.event_timestamp <= after_time + timedelta(minutes=5)
        ).order_by(QueueEvent.event_timestamp.desc()).first()
        
        if not before_event or not after_event:
            return {"error": "Insufficient data to evaluate effectiveness"}
        
        # Calculate improvement
        before_length = before_event.current_queue_length
        after_length = after_event.current_queue_length
        
        if before_length > 0:
            improvement_percentage = ((before_length - after_length) / before_length) * 100
        else:
            improvement_percentage = 0
        
        # Update recommendation with effectiveness data
        recommendation.improvement_percentage = improvement_percentage
        recommendation.before_queue_length = before_length
        recommendation.after_queue_length = after_length
        
        db.commit()
        
        return {
            "recommendation_id": recommendation_id,
            "recommendation_type": recommendation.recommendation_type,
            "before_queue_length": before_length,
            "after_queue_length": after_length,
            "improvement_percentage": round(improvement_percentage, 1),
            "effectiveness": "positive" if improvement_percentage > 5 else "neutral" if improvement_percentage > -5 else "negative"
        }
    
    def get_lane_utilization_report(self, db: Session, terminal: Optional[str] = None) -> List[Dict]:
        """Generate comprehensive lane utilization report."""
        
        query = db.query(QueueState)
        if terminal:
            query = query.filter(QueueState.terminal == terminal)
        
        states = query.all()
        
        report = []
        for state in states:
            config = self.lane_configurations.get(state.checkpoint_type, self.lane_configurations["security"])
            
            # Calculate utilization metrics
            lane_status = json.loads(state.lane_status or "{}")
            utilization_metrics = self._calculate_lane_utilization(state, lane_status, config)
            
            report.append({
                "checkpoint_id": state.checkpoint_id,
                "checkpoint_type": state.checkpoint_type,
                "terminal": state.terminal,
                "total_lanes": state.total_lanes,
                "active_lanes": state.active_lanes,
                "current_queue_length": state.current_queue_length,
                "current_wait_time": state.current_wait_time,
                "utilization_metrics": utilization_metrics,
                "efficiency_score": self._calculate_efficiency_score(state, config),
                "recommendations_pending": self._count_pending_recommendations(db, state.checkpoint_id)
            })
        
        return report
    
    def _calculate_performance_metrics(self, state: QueueState, config: Dict) -> Dict:
        """Calculate current performance metrics."""
        
        # Calculate per-lane utilization
        lane_status = json.loads(state.lane_status or "{}")
        total_capacity = state.active_lanes * config["optimal_capacity_per_lane"]
        
        # Calculate utilization percentage
        utilization = state.current_capacity_utilization
        
        # Calculate service level
        service_level = "good"
        if state.current_wait_time > self.threshold_rules["wait_time"]["high"]:
            service_level = "poor"
        elif state.current_wait_time > self.threshold_rules["wait_time"]["medium"]:
            service_level = "fair"
        
        # Calculate efficiency
        if state.total_processed_today > 0 and state.active_lanes > 0:
            efficiency = state.total_processed_today / (state.active_lanes * config["optimal_capacity_per_lane"])
        else:
            efficiency = 0
        
        return {
            "utilization": utilization,
            "service_level": service_level,
            "efficiency": efficiency,
            "capacity_per_lane": state.current_queue_length / max(state.active_lanes, 1),
            "utilization_status": self._get_utilization_status(utilization),
            "performance_score": self._calculate_performance_score(utilization, service_level, efficiency)
        }
    
    def _evaluate_lane_opening(self, state: QueueState, config: Dict, metrics: Dict) -> Optional[Dict]:
        """Evaluate if opening additional lanes is recommended."""
        
        # Check if we can open more lanes
        if state.active_lanes >= state.total_lanes or state.active_lanes >= config["max_lanes"]:
            return None
        
        # Check if opening is justified
        triggers = []
        
        # High utilization trigger
        if metrics["utilization"] > self.threshold_rules["utilization"]["high"]:
            triggers.append({
                "type": "high_utilization",
                "value": metrics["utilization"],
                "threshold": self.threshold_rules["utilization"]["high"]
            })
        
        # Long wait time trigger
        if state.current_wait_time > self.threshold_rules["wait_time"]["high"]:
            triggers.append({
                "type": "long_wait_time",
                "value": state.current_wait_time,
                "threshold": self.threshold_rules["wait_time"]["high"]
            })
        
        # High queue length trigger
        queue_ratio = state.current_queue_length / (state.active_lanes * config["optimal_capacity_per_lane"])
        if queue_ratio > self.threshold_rules["utilization"]["high"]:
            triggers.append({
                "type": "high_queue_ratio",
                "value": queue_ratio,
                "threshold": self.threshold_rules["utilization"]["high"]
            })
        
        if not triggers:
            return None
        
        # Calculate recommended lanes
        recommended_lanes = min(state.active_lanes + 1, config["max_lanes"])
        
        # Calculate impact
        estimated_wait_reduction = int(state.current_wait_time * 0.3)  # 30% reduction expected
        cost_impact = config["opening_cost_per_hour"]
        
        return {
            "type": "open_lane",
            "priority": "high" if len(triggers) > 1 else "medium",
            "recommended_lanes": recommended_lanes,
            "current_lanes": state.active_lanes,
            "triggers": triggers,
            "impact_assessment": {
                "wait_time_reduction": estimated_wait_reduction,
                "cost_per_hour": cost_impact,
                "implementation_time": config["switch_time_minutes"]
            },
            "confidence": 0.8
        }
    
    def _evaluate_lane_closing(self, state: QueueState, config: Dict, metrics: Dict) -> Optional[Dict]:
        """Evaluate if closing lanes is recommended."""
        
        # Check if we can close lanes
        if state.active_lanes <= config["min_lanes"]:
            return None
        
        # Check if closing is justified
        triggers = []
        
        # Low utilization trigger
        if metrics["utilization"] < self.threshold_rules["utilization"]["low"]:
            triggers.append({
                "type": "low_utilization",
                "value": metrics["utilization"],
                "threshold": self.threshold_rules["utilization"]["low"]
            })
        
        # Short wait time trigger
        if state.current_wait_time < self.threshold_rules["wait_time"]["low"]:
            triggers.append({
                "type": "short_wait_time",
                "value": state.current_wait_time,
                "threshold": self.threshold_rules["wait_time"]["low"]
            })
        
        # Low queue per lane trigger
        queue_per_lane = state.current_queue_length / state.active_lanes
        optimal_per_lane = config["optimal_capacity_per_lane"] * 0.6  # 60% of optimal
        
        if queue_per_lane < optimal_per_lane:
            triggers.append({
                "type": "low_queue_per_lane",
                "value": queue_per_lane,
                "threshold": optimal_per_lane
            })
        
        if not triggers:
            return None
        
        # Calculate recommended lanes
        recommended_lanes = max(config["min_lanes"], state.active_lanes - 1)
        
        # Calculate impact
        estimated_wait_increase = int(state.current_wait_time * 0.2)  # 20% increase expected
        cost_savings = config["closing_savings_per_hour"]
        
        return {
            "type": "close_lane",
            "priority": "medium",
            "recommended_lanes": recommended_lanes,
            "current_lanes": state.active_lanes,
            "triggers": triggers,
            "impact_assessment": {
                "wait_time_increase": estimated_wait_increase,
                "cost_savings_per_hour": cost_savings,
                "implementation_time": config["switch_time_minutes"]
            },
            "confidence": 0.7
        }
    
    def _evaluate_lane_reconfiguration(self, state: QueueState, config: Dict, metrics: Dict) -> Optional[Dict]:
        """Evaluate if lane reconfiguration is needed."""
        
        # Check lane balance
        lane_status = json.loads(state.lane_status or "{}")
        if len(lane_status) < 2:
            return None
        
        # Calculate balance score
        queue_lengths = [
            info.get("queue_length", 0) 
            for info in lane_status.values() 
            if info.get("status") == "active"
        ]
        
        if len(queue_lengths) < 2:
            return None
        
        # Calculate coefficient of variation
        mean_length = sum(queue_lengths) / len(queue_lengths)
        variance = sum((ql - mean_length) ** 2 for ql in queue_lengths) / len(queue_lengths)
        cv = (variance ** 0.5) / max(mean_length, 1)
        
        # Poor balance trigger
        if cv > 0.5:  # High variation
            triggers = [{
                "type": "poor_lane_balance",
                "value": cv,
                "threshold": 0.5
            }]
        else:
            triggers = []
        
        if not triggers:
            return None
        
        # Calculate impact
        balance_improvement = min(0.3, cv * 0.5)  # Expected improvement
        
        return {
            "type": "reconfigure",
            "priority": "low",
            "recommended_lanes": state.active_lanes,  # Keep same number, rebalance
            "current_lanes": state.active_lanes,
            "triggers": triggers,
            "impact_assessment": {
                "balance_improvement": balance_improvement,
                "implementation_time": config["switch_time_minutes"],
                "rebalance_needed": True
            },
            "confidence": 0.6
        }
    
    def _create_open_lane_recommendation(self, state: QueueState, config: Dict, 
                                   recommendation_id: str, priority: str) -> LaneRecommendation:
        """Create lane opening recommendation record."""
        
        recommended_lanes = min(state.active_lanes + 1, config["max_lanes"])
        
        return LaneRecommendation(
            recommendation_id=recommendation_id,
            checkpoint_id=state.checkpoint_id,
            recommendation_type="open_lane",
            current_lanes=state.total_lanes,
            active_lanes=state.active_lanes,
            current_queue_length=state.current_queue_length,
            current_wait_time=state.current_wait_time,
            recommended_lanes=recommended_lanes,
            recommended_action=f"Open additional lane. Current: {state.active_lanes}, Recommended: {recommended_lanes}",
            priority_level=priority,
            impact_assessment=f"Expected wait time reduction: {int(state.current_wait_time * 0.3)} minutes",
            trigger_metric="queue_length",
            trigger_value=float(state.current_queue_length),
            threshold_exceeded=True,
            recommended_by="automated_system",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2)
        )
    
    def _create_close_lane_recommendation(self, state: QueueState, config: Dict, 
                                    recommendation_id: str, priority: str) -> LaneRecommendation:
        """Create lane closing recommendation record."""
        
        recommended_lanes = max(config["min_lanes"], state.active_lanes - 1)
        
        return LaneRecommendation(
            recommendation_id=recommendation_id,
            checkpoint_id=state.checkpoint_id,
            recommendation_type="close_lane",
            current_lanes=state.total_lanes,
            active_lanes=state.active_lanes,
            current_queue_length=state.current_queue_length,
            current_wait_time=state.current_wait_time,
            recommended_lanes=recommended_lanes,
            recommended_action=f"Close underutilized lane. Current: {state.active_lanes}, Recommended: {recommended_lanes}",
            priority_level=priority,
            impact_assessment=f"Cost savings: {config['closing_savings_per_hour']} per hour",
            trigger_metric="utilization",
            trigger_value=state.current_capacity_utilization,
            threshold_exceeded=False,  # Below threshold
            recommended_by="automated_system",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    def _create_reconfigure_recommendation(self, state: QueueState, config: Dict, 
                                     recommendation_id: str, priority: str) -> LaneRecommendation:
        """Create lane reconfiguration recommendation record."""
        
        return LaneRecommendation(
            recommendation_id=recommendation_id,
            checkpoint_id=state.checkpoint_id,
            recommendation_type="reconfigure",
            current_lanes=state.total_lanes,
            active_lanes=state.active_lanes,
            current_queue_length=state.current_queue_length,
            current_wait_time=state.current_wait_time,
            recommended_lanes=state.active_lanes,
            recommended_action=f"Rebalance queue distribution across {state.active_lanes} lanes",
            priority_level=priority,
            impact_assessment="Improve lane balance and efficiency",
            trigger_metric="lane_balance",
            trigger_value=0.5,  # CV threshold
            threshold_exceeded=True,
            recommended_by="automated_system",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    def _calculate_lane_utilization(self, state: QueueState, lane_status: Dict, config: Dict) -> Dict:
        """Calculate detailed lane utilization metrics."""
        
        if not lane_status:
            return {"error": "No lane status data"}
        
        utilization_data = {}
        total_queue = 0
        active_lanes = 0
        
        for lane_id, lane_info in lane_status.items():
            queue_length = lane_info.get("queue_length", 0)
            status = lane_info.get("status", "inactive")
            
            total_queue += queue_length
            if status == "active":
                active_lanes += 1
            
            # Calculate utilization for this lane
            lane_utilization = min(queue_length / config["optimal_capacity_per_lane"], 1.0)
            
            utilization_data[lane_id] = {
                "queue_length": queue_length,
                "status": status,
                "utilization": lane_utilization,
                "efficiency": self._calculate_lane_efficiency(queue_length, config)
            }
        
        return {
            "total_lanes": len(lane_status),
            "active_lanes": active_lanes,
            "total_queue_length": total_queue,
            "average_queue_per_lane": total_queue / max(active_lanes, 1),
            "lane_utilization": utilization_data,
            "balance_score": self._calculate_balance_score(utilization_data)
        }
    
    def _calculate_lane_efficiency(self, queue_length: int, config: Dict) -> float:
        """Calculate efficiency for a single lane."""
        optimal_capacity = config["optimal_capacity_per_lane"]
        
        if queue_length <= optimal_capacity:
            return queue_length / optimal_capacity  # Efficient utilization
        else:
            return 1.0 - ((queue_length - optimal_capacity) / optimal_capacity) * 0.5  # Overloaded but still functioning
    
    def _calculate_balance_score(self, utilization_data: Dict) -> float:
        """Calculate how balanced the lanes are."""
        
        active_utilizations = [
            data["utilization"] 
            for data in utilization_data.values() 
            if data.get("status") == "active"
        ]
        
        if len(active_utilizations) < 2:
            return 1.0
        
        mean_utilization = sum(active_utilizations) / len(active_utilizations)
        variance = sum((u - mean_utilization) ** 2 for u in active_utilizations) / len(active_utilizations)
        cv = (variance ** 0.5) / max(mean_utilization, 0.1)
        
        return max(0, 1 - cv)  # Higher is better balanced
    
    def _calculate_efficiency_score(self, state: QueueState, config: Dict) -> float:
        """Calculate overall efficiency score for the checkpoint."""
        
        # Factors: utilization, service level, processing efficiency
        utilization_score = min(state.current_capacity_utilization, 1.0)
        
        # Service level score (lower wait time is better)
        wait_score = max(0, 1 - (state.current_wait_time / 30))  # 30 minutes = 0 score
        
        # Processing efficiency
        if state.total_processed_today > 0 and state.active_lanes > 0:
            processing_score = min(1.0, state.total_processed_today / (state.active_lanes * config["optimal_capacity_per_lane"] * 8))  # 8 hour shift
        else:
            processing_score = 0
        
        # Weighted average
        efficiency_score = (utilization_score * 0.4 + wait_score * 0.4 + processing_score * 0.2)
        
        return round(efficiency_score, 3)
    
    def _calculate_performance_score(self, utilization: float, service_level: str, efficiency: float) -> float:
        """Calculate overall performance score."""
        
        # Convert service level to numeric score
        service_scores = {"good": 1.0, "fair": 0.7, "poor": 0.3}
        service_score = service_scores.get(service_level, 0.5)
        
        # Weighted average
        performance_score = (utilization * 0.4 + service_score * 0.4 + efficiency * 0.2)
        
        return round(performance_score, 3)
    
    def _get_utilization_status(self, utilization: float) -> str:
        """Get utilization status category."""
        
        if utilization > self.threshold_rules["utilization"]["critical"]:
            return "critical"
        elif utilization > self.threshold_rules["utilization"]["high"]:
            return "high"
        elif utilization > self.threshold_rules["utilization"]["medium"]:
            return "medium"
        else:
            return "low"
    
    def _count_pending_recommendations(self, db: Session, checkpoint_id: str) -> int:
        """Count pending recommendations for a checkpoint."""
        
        return db.query(LaneRecommendation).filter(
            LaneRecommendation.checkpoint_id == checkpoint_id,
            LaneRecommendation.implemented == False,
            LaneRecommendation.expires_at > datetime.utcnow()
        ).count()


# Global instance
smart_lane_management = SmartLaneManagementEngine()
