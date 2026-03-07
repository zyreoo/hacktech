"""
Asset Health Prediction and Scoring Service.

Advanced predictive analytics for:
- Asset health scoring based on multiple factors
- Failure probability calculation using historical data
- Predictive maintenance recommendations
- Risk assessment and prioritization
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from ..models import (
    InfrastructureAsset, AssetStatusEvent, AssetMaintenanceRecord,
    NetworkMonitoringSession
)
from ..database import SessionLocal


class AssetHealthPredictionEngine:
    """Advanced asset health prediction and scoring system."""
    
    def __init__(self):
        self.health_weights = {
            "current_status": 0.25,      # Current operational status
            "uptime_percentage": 0.20,    # Historical uptime
            "error_rate": 0.20,           # Recent error frequency
            "network_health": 0.15,         # Network connectivity
            "maintenance_history": 0.10,     # Maintenance frequency
            "usage_patterns": 0.10           # Usage intensity
        }
        
        self.failure_risk_factors = {
            "age_factor": 0.15,            # Asset age and wear
            "usage_intensity": 0.20,        # How heavily used
            "error_frequency": 0.25,         # Recent error patterns
            "maintenance_delay": 0.15,        # Overdue maintenance
            "network_degradation": 0.15,      # Network issues
            "environmental_stress": 0.10       # Operating conditions
        }
    
    def calculate_asset_health_score(self, db: Session, asset_id: int) -> Dict:
        """Calculate comprehensive health score for an asset."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Calculate individual health factors
        status_score = self._calculate_status_score(asset)
        uptime_score = self._calculate_uptime_score(db, asset_id)
        error_score = self._calculate_error_score(db, asset_id)
        network_score = self._calculate_network_score(asset)
        maintenance_score = self._calculate_maintenance_score(db, asset_id)
        usage_score = self._calculate_usage_score(asset)
        
        # Calculate weighted health score
        health_score = (
            status_score * self.health_weights["current_status"] +
            uptime_score * self.health_weights["uptime_percentage"] +
            error_score * self.health_weights["error_rate"] +
            network_score * self.health_weights["network_health"] +
            maintenance_score * self.health_weights["maintenance_history"] +
            usage_score * self.health_weights["usage_patterns"]
        )
        
        # Update asset health score
        asset.health_score = round(health_score, 3)
        asset.updated_at = datetime.utcnow()
        
        return {
            "asset_id": asset_id,
            "health_score": health_score,
            "health_factors": {
                "status_score": status_score,
                "uptime_score": uptime_score,
                "error_score": error_score,
                "network_score": network_score,
                "maintenance_score": maintenance_score,
                "usage_score": usage_score
            },
            "health_level": self._get_health_level(health_score),
            "recommendations": self._generate_health_recommendations(health_score, asset)
        }
    
    def predict_failure_probability(self, db: Session, asset_id: int, 
                              prediction_hours: int = 24) -> Dict:
        """Predict failure probability for specified time window."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Calculate risk factors
        age_factor = self._calculate_age_factor(asset)
        usage_intensity = self._calculate_usage_intensity(db, asset_id)
        error_frequency = self._calculate_error_frequency(db, asset_id)
        maintenance_delay = self._calculate_maintenance_delay(asset)
        network_degradation = self._calculate_network_degradation(asset)
        environmental_stress = self._calculate_environmental_stress(asset)
        
        # Calculate weighted failure probability
        failure_probability = (
            age_factor * self.failure_risk_factors["age_factor"] +
            usage_intensity * self.failure_risk_factors["usage_intensity"] +
            error_frequency * self.failure_risk_factors["error_frequency"] +
            maintenance_delay * self.failure_risk_factors["maintenance_delay"] +
            network_degradation * self.failure_risk_factors["network_degradation"] +
            environmental_stress * self.failure_risk_factors["environmental_stress"]
        )
        
        # Apply time-based scaling
        time_multiplier = self._get_time_multiplier(prediction_hours)
        adjusted_probability = failure_probability * time_multiplier
        
        # Cap at reasonable maximum
        final_probability = min(adjusted_probability, 0.95)
        
        # Update asset predictions
        if prediction_hours == 24:
            asset.failure_probability_24h = round(final_probability, 3)
        elif prediction_hours == 168:  # 7 days
            asset.failure_probability_7d = round(final_probability, 3)
        
        # Predict failure time if probability is high
        predicted_failure_time = None
        if final_probability > 0.7:
            predicted_failure_time = self._predict_failure_time(asset, final_probability)
            asset.predicted_failure_time = predicted_failure_time
        
        # Update maintenance priority
        asset.maintenance_priority = self._calculate_maintenance_priority(final_probability, asset)
        
        return {
            "asset_id": asset_id,
            "prediction_hours": prediction_hours,
            "failure_probability": round(final_probability, 3),
            "risk_level": self._get_risk_level(final_probability),
            "risk_factors": {
                "age_factor": age_factor,
                "usage_intensity": usage_intensity,
                "error_frequency": error_frequency,
                "maintenance_delay": maintenance_delay,
                "network_degradation": network_degradation,
                "environmental_stress": environmental_stress
            },
            "predicted_failure_time": predicted_failure_time.isoformat() if predicted_failure_time else None,
            "maintenance_priority": asset.maintenance_priority,
            "recommended_actions": self._generate_failure_recommendations(final_probability, asset)
        }
    
    def generate_predictive_maintenance_alerts(self, db: Session) -> List[Dict]:
        """Generate maintenance alerts for assets at risk."""
        
        alerts = []
        
        # Get all assets
        assets = db.query(InfrastructureAsset).all()
        
        for asset in assets:
            # Calculate 24h failure probability
            prediction = self.predict_failure_probability(db, asset.id, 24)
            
            # Generate alert if risk is significant
            if prediction["failure_probability"] > 0.3:  # 30% threshold
                alert = {
                    "asset_id": asset.id,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type,
                    "location": asset.location,
                    "alert_type": "predictive_maintenance",
                    "severity": self._get_alert_severity(prediction["failure_probability"]),
                    "failure_probability_24h": prediction["failure_probability"],
                    "risk_level": prediction["risk_level"],
                    "predicted_failure_time": prediction["predicted_failure_time"],
                    "maintenance_priority": prediction["maintenance_priority"],
                    "recommended_actions": prediction["recommended_actions"],
                    "generated_at": datetime.utcnow().isoformat()
                }
                alerts.append(alert)
        
        # Sort by failure probability
        alerts.sort(key=lambda x: x["failure_probability_24h"], reverse=True)
        
        return alerts
    
    def get_assets_needing_maintenance(self, db: Session, priority_threshold: str = "high") -> List[InfrastructureAsset]:
        """Get assets that need maintenance based on predictions."""
        
        priority_order = {"critical": 4, "high": 3, "normal": 2, "low": 1}
        min_priority = priority_order.get(priority_threshold, 2)
        
        return db.query(InfrastructureAsset).filter(
            and_(
                InfrastructureAsset.maintenance_priority.in_(
                    [p for p, level in priority_order.items() if level >= min_priority]
                ),
                or_(
                    InfrastructureAsset.failure_probability_24h > 0.3,
                    InfrastructureAsset.health_score < 0.6,
                    InfrastructureAsset.next_maintenance <= datetime.utcnow()
                )
            )
        ).order_by(desc(InfrastructureAsset.failure_probability_24h)).all()
    
    def _calculate_status_score(self, asset: InfrastructureAsset) -> float:
        """Calculate score based on current status."""
        
        status_scores = {
            "operational": 1.0,
            "degraded": 0.7,
            "maintenance": 0.3,
            "offline": 0.1,
            "failed": 0.0
        }
        
        return status_scores.get(asset.status, 0.5)
    
    def _calculate_uptime_score(self, db: Session, asset_id: int) -> float:
        """Calculate score based on uptime percentage."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset or asset.uptime_percentage is None:
            return 0.5  # Default if no data
        
        # Linear scaling: 100% = 1.0, 90% = 0.8, 80% = 0.6, etc.
        uptime = asset.uptime_percentage
        if uptime >= 99:
            return 1.0
        elif uptime >= 95:
            return 0.9
        elif uptime >= 90:
            return 0.8
        elif uptime >= 85:
            return 0.7
        elif uptime >= 80:
            return 0.6
        elif uptime >= 70:
            return 0.4
        else:
            return 0.2
    
    def _calculate_error_score(self, db: Session, asset_id: int) -> float:
        """Calculate score based on recent error frequency."""
        
        # Get error events from last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        error_count = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset_id,
            AssetStatusEvent.event_type == "error",
            AssetStatusEvent.created_at >= cutoff_time
        ).count()
        
        # Inverse scoring: fewer errors = higher score
        if error_count == 0:
            return 1.0
        elif error_count <= 2:
            return 0.8
        elif error_count <= 5:
            return 0.6
        elif error_count <= 10:
            return 0.4
        else:
            return 0.2
    
    def _calculate_network_score(self, asset: InfrastructureAsset) -> float:
        """Calculate score based on network health metrics."""
        
        if asset.network_health is None:
            return 0.5
        
        # Network health is already 0-1 scale
        return asset.network_health
    
    def _calculate_maintenance_score(self, db: Session, asset_id: int) -> float:
        """Calculate score based on maintenance history."""
        
        # Get maintenance records from last 90 days
        cutoff_time = datetime.utcnow() - timedelta(days=90)
        maintenance_count = db.query(AssetMaintenanceRecord).filter(
            AssetMaintenanceRecord.asset_id == asset_id,
            AssetMaintenanceRecord.created_at >= cutoff_time
        ).count()
        
        # Score based on maintenance frequency (lower is better)
        if maintenance_count == 0:
            return 0.8  # No maintenance could be good or bad
        elif maintenance_count <= 2:
            return 0.9  # Optimal maintenance
        elif maintenance_count <= 5:
            return 0.7  # Normal maintenance
        elif maintenance_count <= 10:
            return 0.5  # High maintenance
        else:
            return 0.3  # Excessive maintenance
    
    def _calculate_usage_score(self, asset: InfrastructureAsset) -> float:
        """Calculate score based on usage patterns."""
        
        if not asset.usage_cycles or not asset.total_usage_time:
            return 0.5
        
        # Calculate usage intensity (cycles per hour)
        if asset.total_usage_time > 0:
            usage_intensity = asset.usage_cycles / (asset.total_usage_time / 60)  # cycles per hour
        else:
            return 0.5
        
        # Score based on usage intensity (moderate usage is optimal)
        if usage_intensity < 1:
            return 0.7  # Light usage
        elif usage_intensity <= 5:
            return 1.0  # Optimal usage
        elif usage_intensity <= 10:
            return 0.8  # Moderate usage
        elif usage_intensity <= 20:
            return 0.6  # Heavy usage
        else:
            return 0.3  # Extreme usage
    
    def _calculate_age_factor(self, asset: InfrastructureAsset) -> float:
        """Calculate age-based risk factor."""
        
        # Asset age in days (assuming created_at represents installation date)
        if not asset.created_at:
            return 0.1
        
        age_days = (datetime.utcnow() - asset.created_at).days
        
        # Risk increases with age
        if age_days < 30:
            return 0.1  # Very new
        elif age_days < 90:
            return 0.2  # New
        elif age_days < 365:
            return 0.3  # Less than 1 year
        elif age_days < 730:
            return 0.5  # 1-2 years
        elif age_days < 1825:
            return 0.7  # 2-5 years
        else:
            return 0.9  # More than 5 years
    
    def _calculate_usage_intensity(self, db: Session, asset_id: int) -> float:
        """Calculate usage intensity risk factor."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            return 0.5
        
        return self._calculate_usage_score(asset)  # Reuse usage score as intensity factor
    
    def _calculate_error_frequency(self, db: Session, asset_id: int) -> float:
        """Calculate error frequency risk factor."""
        
        # Get error events from last 7 days
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        error_count = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset_id,
            AssetStatusEvent.event_type == "error",
            AssetStatusEvent.created_at >= cutoff_time
        ).count()
        
        # Normalize to 0-1 scale (10+ errors = 1.0 risk)
        return min(error_count / 10.0, 1.0)
    
    def _calculate_maintenance_delay(self, asset: InfrastructureAsset) -> float:
        """Calculate maintenance delay risk factor."""
        
        if not asset.next_maintenance:
            return 0.1  # Low risk if no scheduled maintenance
        
        # Calculate how overdue maintenance is
        overdue_hours = (datetime.utcnow() - asset.next_maintenance).total_seconds() / 3600
        
        if overdue_hours < 0:
            return 0.0  # Maintenance is in the future
        elif overdue_hours < 24:
            return 0.3  # Slightly overdue
        elif overdue_hours < 72:
            return 0.6  # Moderately overdue
        else:
            return 0.9  # Significantly overdue
    
    def _calculate_network_degradation(self, asset: InfrastructureAsset) -> float:
        """Calculate network degradation risk factor."""
        
        if asset.network_health is None:
            return 0.5
        
        # Inverse of network health (lower health = higher risk)
        return 1.0 - asset.network_health
    
    def _calculate_environmental_stress(self, asset: InfrastructureAsset) -> float:
        """Calculate environmental stress risk factor."""
        
        # Simplified environmental stress based on location and asset type
        high_stress_locations = ["security_point", "baggage_claim", "outdoor"]
        high_stress_types = ["belt", "sensor", "security_scanner"]
        
        stress_level = 0.3  # Base stress
        
        if any(loc in asset.location.lower() for loc in high_stress_locations):
            stress_level += 0.3
        
        if asset.asset_type in high_stress_types:
            stress_level += 0.2
        
        return min(stress_level, 1.0)
    
    def _get_time_multiplier(self, hours: int) -> float:
        """Get time-based multiplier for failure prediction."""
        
        # Longer time windows = higher probability
        if hours <= 1:
            return 0.1
        elif hours <= 6:
            return 0.3
        elif hours <= 24:
            return 1.0
        elif hours <= 72:
            return 1.5
        elif hours <= 168:
            return 2.0
        else:
            return 3.0
    
    def _predict_failure_time(self, asset: InfrastructureAsset, probability: float) -> Optional[datetime]:
        """Predict approximate failure time based on probability."""
        
        if probability < 0.5:
            return None
        
        # Estimate time to failure based on probability
        # Higher probability = sooner failure
        hours_to_failure = int((1.0 - probability) * 48)  # 0-48 hours based on probability
        
        predicted_time = datetime.utcnow() + timedelta(hours=hours_to_failure)
        return predicted_time
    
    def _calculate_maintenance_priority(self, failure_probability: float, asset: InfrastructureAsset) -> str:
        """Calculate maintenance priority based on risk factors."""
        
        if failure_probability > 0.8 or asset.status == "failed":
            return "critical"
        elif failure_probability > 0.6 or asset.health_score < 0.4:
            return "high"
        elif failure_probability > 0.3 or asset.health_score < 0.6:
            return "normal"
        else:
            return "low"
    
    def _get_health_level(self, health_score: float) -> str:
        """Get health level category from score."""
        
        if health_score >= 0.9:
            return "excellent"
        elif health_score >= 0.8:
            return "good"
        elif health_score >= 0.7:
            return "fair"
        elif health_score >= 0.5:
            return "poor"
        else:
            return "critical"
    
    def _get_risk_level(self, failure_probability: float) -> str:
        """Get risk level category from failure probability."""
        
        if failure_probability >= 0.8:
            return "critical"
        elif failure_probability >= 0.6:
            return "high"
        elif failure_probability >= 0.3:
            return "medium"
        else:
            return "low"
    
    def _get_alert_severity(self, failure_probability: float) -> str:
        """Get alert severity from failure probability."""
        
        if failure_probability >= 0.8:
            return "critical"
        elif failure_probability >= 0.6:
            return "high"
        elif failure_probability >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_health_recommendations(self, health_score: float, asset: InfrastructureAsset) -> List[str]:
        """Generate recommendations based on health score."""
        
        recommendations = []
        
        if health_score < 0.5:
            recommendations.append("Immediate inspection required")
            recommendations.append("Consider temporary replacement")
        elif health_score < 0.7:
            recommendations.append("Schedule maintenance within 24 hours")
            recommendations.append("Monitor closely for degradation")
        elif health_score < 0.8:
            recommendations.append("Schedule maintenance within 72 hours")
            recommendations.append("Check for performance issues")
        else:
            recommendations.append("Continue routine monitoring")
        
        # Asset-specific recommendations
        if asset.asset_type == "security_scanner" and health_score < 0.8:
            recommendations.append("Calibrate scanning sensors")
        elif asset.asset_type == "belt" and health_score < 0.7:
            recommendations.append("Inspect belt tension and alignment")
        elif asset.asset_type == "kiosk" and health_score < 0.8:
            recommendations.append("Update software and check touch screen")
        
        return recommendations
    
    def _generate_failure_recommendations(self, failure_probability: float, asset: InfrastructureAsset) -> List[str]:
        """Generate recommendations based on failure probability."""
        
        recommendations = []
        
        if failure_probability > 0.8:
            recommendations.extend([
                "IMMEDIATE ACTION REQUIRED",
                "Prepare backup equipment",
                "Notify operations center",
                "Schedule emergency maintenance"
            ])
        elif failure_probability > 0.6:
            recommendations.extend([
                "Schedule maintenance within 12 hours",
                "Prepare contingency plans",
                "Increase monitoring frequency"
            ])
        elif failure_probability > 0.3:
            recommendations.extend([
                "Schedule maintenance within 48 hours",
                "Check spare parts availability",
                "Review recent performance data"
            ])
        else:
            recommendations.extend([
                "Continue routine monitoring",
                "Schedule preventive maintenance"
            ])
        
        return recommendations


# Global instance
asset_health_prediction = AssetHealthPredictionEngine()
