"""
Self-Healing Actions and Recommendations Service.

Intelligent self-healing system for:
- Automatic maintenance window optimization
- Asset rerouting and failover
- Automated corrective actions
- Operations dashboard notifications
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    InfrastructureAsset, InfrastructureIncident, SelfHealingAction,
    AssetMaintenanceRecord, Flight
)
from ..database import SessionLocal


class SelfHealingEngine:
    """Intelligent self-healing and automated recommendation system."""
    
    def __init__(self):
        self.healing_actions = {
            "restart": {
                "description": "Restart asset service",
                "applicable_types": ["kiosk", "pos", "display", "sensor"],
                "success_rate": 0.7,
                "disruption_time": 2  # minutes
            },
            "reroute": {
                "description": "Reroute to backup asset",
                "applicable_types": ["security_scanner", "belt", "pos"],
                "success_rate": 0.8,
                "disruption_time": 5
            },
            "maintenance_window": {
                "description": "Schedule maintenance window",
                "applicable_types": ["belt", "security_scanner", "sensor"],
                "success_rate": 0.9,
                "disruption_time": 30
            },
            "config_change": {
                "description": "Apply configuration fix",
                "applicable_types": ["kiosk", "pos", "display"],
                "success_rate": 0.6,
                "disruption_time": 1
            },
            "notification": {
                "description": "Notify operations team",
                "applicable_types": ["all"],
                "success_rate": 1.0,
                "disruption_time": 0
            }
        }
        
        self.maintenance_window_rules = {
            "low_traffic_hours": [(22, 6), (10, 12)],  # 10pm-6am, 10am-12pm
            "min_window_hours": 2,
            "max_window_hours": 6,
            "advance_notice_hours": 4,
            "flight_load_threshold": 0.7  # Schedule when flight load < 70%
        }
    
    def analyze_incident_for_healing(self, db: Session, incident_id: str) -> List[Dict]:
        """Analyze incident and recommend self-healing actions."""
        
        incident = db.query(InfrastructureIncident).filter(
            InfrastructureIncident.incident_id == incident_id
        ).first()
        
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        # Get affected asset
        asset = db.query(InfrastructureAsset).filter(
            InfrastructureAsset.id == incident.primary_asset_id
        ).first()
        
        if not asset:
            return []
        
        # Analyze incident and generate healing recommendations
        healing_actions = []
        
        # 1. Asset offline -> Restart or reroute
        if incident.incident_type == "asset_offline":
            healing_actions.extend(self._handle_offline_asset(db, asset, incident))
        
        # 2. Repeated errors -> Config change or restart
        elif incident.incident_type == "repeated_errors":
            healing_actions.extend(self._handle_repeated_errors(db, asset, incident))
        
        # 3. Network degradation -> Config change or reroute
        elif incident.incident_type == "network_degradation":
            healing_actions.extend(self._handle_network_degradation(db, asset, incident))
        
        # 4. Performance anomaly -> Config change
        elif incident.incident_type == "performance_anomaly":
            healing_actions.extend(self._handle_performance_anomaly(db, asset, incident))
        
        # 5. Security breach -> Notification and isolation
        elif incident.incident_type == "security_breach":
            healing_actions.extend(self._handle_security_breach(db, asset, incident))
        
        return healing_actions
    
    def execute_healing_action(self, db: Session, action_data: Dict) -> SelfHealingAction:
        """Execute a self-healing action."""
        
        # Create healing action record
        action = SelfHealingAction(
            incident_id=action_data.get("incident_id"),
            asset_id=action_data["asset_id"],
            action_type=action_data["action_type"],
            action_name=action_data["action_name"],
            action_description=action_data["action_description"],
            triggered_by=action_data["triggered_by"],
            executed_at=datetime.utcnow(),
            execution_status="executing"
        )
        
        db.add(action)
        db.flush()
        
        # Execute the action (simulation)
        execution_result = self._execute_action_simulation(db, action_data)
        
        # Update action with results
        action.execution_status = "completed" if execution_result["success"] else "failed"
        action.execution_result = json.dumps(execution_result)
        action.successful = execution_result["success"]
        action.impact_assessment = execution_result["impact_assessment"]
        action.passenger_disruption = execution_result["passenger_disruption"]
        action.completed_at = datetime.utcnow()
        
        # Update asset if action was successful
        if execution_result["success"]:
            self._update_asset_after_healing(db, action_data["asset_id"], execution_result)
        
        return action
    
    def optimize_maintenance_windows(self, db: Session, asset_ids: List[int]) -> List[Dict]:
        """Optimize maintenance windows based on flight schedules and asset criticality."""
        
        windows = []
        
        for asset_id in asset_ids:
            asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
            if not asset:
                continue
            
            # Get flight load for asset location
            flight_load = self._calculate_flight_load(db, asset)
            
            # Find optimal maintenance windows
            optimal_windows = self._find_optimal_maintenance_windows(db, asset, flight_load)
            
            for window in optimal_windows:
                window.update({
                    "asset_id": asset_id,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type,
                    "location": asset.location,
                    "flight_load_at_window": flight_load,
                    "recommended_actions": self._generate_maintenance_recommendations(asset, window)
                })
            
            windows.extend(optimal_windows)
        
        # Sort by priority and flight load
        windows.sort(key=lambda x: (
            -self.maintenance_window_rules["flight_load_threshold"] + x.get("flight_load_at_window", 0),
            x.get("priority_score", 0)
        ), reverse=True)
        
        return windows
    
    def recommend_asset_rerouting(self, db: Session, failed_asset_id: int, 
                              service_requirements: Dict) -> List[Dict]:
        """Recommend asset rerouting when device fails."""
        
        failed_asset = db.query(InfrastructureAsset).filter(
            InfrastructureAsset.id == failed_asset_id
        ).first()
        
        if not failed_asset:
            return []
        
        # Find alternative assets
        alternatives = db.query(InfrastructureAsset).filter(
            InfrastructureAsset.asset_type == failed_asset.asset_type,
            InfrastructureAsset.terminal == failed_asset.terminal,
            InfrastructureAsset.status == "operational",
            InfrastructureAsset.id != failed_asset_id
        ).all()
        
        recommendations = []
        
        for alternative in alternatives:
            # Calculate suitability score
            suitability = self._calculate_rerouting_suitability(
                failed_asset, alternative, service_requirements
            )
            
            if suitability["score"] > 0.5:  # Minimum suitability threshold
                recommendation = {
                    "failed_asset_id": failed_asset_id,
                    "failed_asset_name": failed_asset.asset_name,
                    "alternative_asset_id": alternative.id,
                    "alternative_asset_name": alternative.asset_name,
                    "alternative_location": alternative.location,
                    "suitability_score": suitability["score"],
                    "suitability_factors": suitability["factors"],
                    "rerouting_plan": self._generate_rerouting_plan(failed_asset, alternative),
                    "estimated_downtime": self.healing_actions["reroute"]["disruption_time"],
                    "passenger_impact": suitability["passenger_impact"]
                }
                recommendations.append(recommendation)
        
        # Sort by suitability score
        recommendations.sort(key=lambda x: x["suitability_score"], reverse=True)
        
        return recommendations
    
    def notify_operations_dashboard(self, db: Session, notification_data: Dict):
        """Create notifications for operations dashboard."""
        
        # Create alert for operations dashboard
        from ..models import Alert
        alert = Alert(
            alert_type=notification_data.get("alert_type", "self_healing"),
            severity=notification_data.get("severity", "medium"),
            source_module="self_healing_engine",
            message=notification_data["message"],
            related_entity_type=notification_data.get("entity_type", "infrastructure_asset"),
            related_entity_id=notification_data.get("entity_id"),
            created_at=datetime.utcnow(),
            uniqueness_key=f"self_healing:{notification_data.get('entity_id', 'unknown')}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        )
        
        db.add(alert)
        
        return alert
    
    def get_healing_action_history(self, db: Session, asset_id: Optional[int] = None,
                               hours_back: int = 24) -> List[SelfHealingAction]:
        """Get history of self-healing actions."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        query = db.query(SelfHealingAction).filter(
            SelfHealingAction.executed_at >= cutoff_time
        )
        
        if asset_id:
            query = query.filter(SelfHealingAction.asset_id == asset_id)
        
        return query.order_by(SelfHealingAction.executed_at.desc()).all()
    
    def get_healing_effectiveness(self, db: Session, days_back: int = 30) -> Dict:
        """Calculate effectiveness of self-healing actions."""
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)
        actions = db.query(SelfHealingAction).filter(
            SelfHealingAction.executed_at >= cutoff_time
        ).all()
        
        if not actions:
            return {
                "period_days": days_back,
                "total_actions": 0,
                "success_rate": 0,
                "actions_by_type": {},
                "average_resolution_time": 0,
                "passenger_disruption_rate": 0
            }
        
        # Calculate metrics
        total_actions = len(actions)
        successful_actions = sum(1 for action in actions if action.successful)
        success_rate = (successful_actions / total_actions) * 100 if total_actions > 0 else 0
        
        # Group by action type
        actions_by_type = {}
        for action in actions:
            action_type = action.action_type
            if action_type not in actions_by_type:
                actions_by_type[action_type] = {"total": 0, "successful": 0}
            actions_by_type[action_type]["total"] += 1
            if action.successful:
                actions_by_type[action_type]["successful"] += 1
        
        # Calculate passenger disruption rate
        disruptive_actions = sum(1 for action in actions if action.passenger_disruption)
        disruption_rate = (disruptive_actions / total_actions) * 100 if total_actions > 0 else 0
        
        return {
            "period_days": days_back,
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "success_rate": round(success_rate, 1),
            "actions_by_type": actions_by_type,
            "passenger_disruption_rate": round(disruption_rate, 1)
        }
    
    def _handle_offline_asset(self, db: Session, asset: InfrastructureAsset, 
                            incident: InfrastructureIncident) -> List[Dict]:
        """Generate healing actions for offline assets."""
        
        actions = []
        
        # Action 1: Attempt restart
        if asset.asset_type in self.healing_actions["restart"]["applicable_types"]:
            actions.append({
                "action_type": "restart",
                "action_name": f"Restart {asset.asset_name}",
                "action_description": f"Automated restart attempt for offline {asset.asset_type}",
                "priority": "high",
                "estimated_success_rate": self.healing_actions["restart"]["success_rate"],
                "passenger_disruption": self.healing_actions["restart"]["disruption_time"] > 0
            })
        
        # Action 2: Find backup/reroute option
        alternatives = self.recommend_asset_rerouting(
            db, asset.id, {"service": "primary_function"}
        )
        
        if alternatives:
            best_alternative = alternatives[0]  # Highest scoring alternative
            actions.append({
                "action_type": "reroute",
                "action_name": f"Reroute to {best_alternative['alternative_asset_name']}",
                "action_description": f"Reroute services from {asset.asset_name} to {best_alternative['alternative_asset_name']}",
                "priority": "high",
                "estimated_success_rate": self.healing_actions["reroute"]["success_rate"],
                "passenger_disruption": self.healing_actions["reroute"]["disruption_time"] > 0,
                "alternative_asset_id": best_alternative["alternative_asset_id"]
            })
        
        # Action 3: Notify operations
        actions.append({
            "action_type": "notification",
            "action_name": "Notify operations team",
            "action_description": f"Asset {asset.asset_name} is offline and requires manual intervention",
            "priority": "critical",
            "estimated_success_rate": 1.0,
            "passenger_disruption": False
        })
        
        return actions
    
    def _handle_repeated_errors(self, db: Session, asset: InfrastructureAsset, 
                              incident: InfrastructureIncident) -> List[Dict]:
        """Generate healing actions for repeated errors."""
        
        actions = []
        
        # Action 1: Configuration change
        if asset.asset_type in self.healing_actions["config_change"]["applicable_types"]:
            actions.append({
                "action_type": "config_change",
                "action_name": f"Apply config fix to {asset.asset_name}",
                "action_description": f"Apply automated configuration fix for repeated errors on {asset.asset_type}",
                "priority": "medium",
                "estimated_success_rate": self.healing_actions["config_change"]["success_rate"],
                "passenger_disruption": self.healing_actions["config_change"]["disruption_time"] > 0
            })
        
        # Action 2: Restart service
        if asset.asset_type in self.healing_actions["restart"]["applicable_types"]:
            actions.append({
                "action_type": "restart",
                "action_name": f"Restart {asset.asset_name} service",
                "action_description": f"Restart service to clear repeated errors on {asset.asset_type}",
                "priority": "medium",
                "estimated_success_rate": self.healing_actions["restart"]["success_rate"],
                "passenger_disruption": self.healing_actions["restart"]["disruption_time"] > 0
            })
        
        # Action 3: Schedule maintenance
        if incident.severity == "high":
            actions.append({
                "action_type": "maintenance_window",
                "action_name": f"Schedule maintenance for {asset.asset_name}",
                "action_description": f"Schedule preventive maintenance due to repeated errors",
                "priority": "high",
                "estimated_success_rate": self.healing_actions["maintenance_window"]["success_rate"],
                "passenger_disruption": True
            })
        
        return actions
    
    def _handle_network_degradation(self, db: Session, asset: InfrastructureAsset, 
                                incident: InfrastructureIncident) -> List[Dict]:
        """Generate healing actions for network degradation."""
        
        actions = []
        
        # Action 1: Configuration optimization
        if asset.asset_type in self.healing_actions["config_change"]["applicable_types"]:
            actions.append({
                "action_type": "config_change",
                "action_name": f"Optimize network config for {asset.asset_name}",
                "action_description": f"Apply network configuration optimization for {asset.asset_type}",
                "priority": "medium",
                "estimated_success_rate": self.healing_actions["config_change"]["success_rate"],
                "passenger_disruption": self.healing_actions["config_change"]["disruption_time"] > 0
            })
        
        # Action 2: Reroute to backup
        alternatives = self.recommend_asset_rerouting(
            db, asset.id, {"service": "network_connectivity"}
        )
        
        if alternatives:
            best_alternative = alternatives[0]
            actions.append({
                "action_type": "reroute",
                "action_name": f"Reroute network to {best_alternative['alternative_asset_name']}",
                "action_description": f"Reroute network services to alternative asset",
                "priority": "high",
                "estimated_success_rate": self.healing_actions["reroute"]["success_rate"],
                "passenger_disruption": self.healing_actions["reroute"]["disruption_time"] > 0,
                "alternative_asset_id": best_alternative["alternative_asset_id"]
            })
        
        return actions
    
    def _handle_performance_anomaly(self, db: Session, asset: InfrastructureAsset, 
                                  incident: InfrastructureIncident) -> List[Dict]:
        """Generate healing actions for performance anomalies."""
        
        actions = []
        
        # Action 1: Configuration tuning
        if asset.asset_type in self.healing_actions["config_change"]["applicable_types"]:
            actions.append({
                "action_type": "config_change",
                "action_name": f"Tune performance config for {asset.asset_name}",
                "action_description": f"Apply performance tuning configuration for {asset.asset_type}",
                "priority": "low",
                "estimated_success_rate": self.healing_actions["config_change"]["success_rate"],
                "passenger_disruption": self.healing_actions["config_change"]["disruption_time"] > 0
            })
        
        # Action 2: Restart service
        actions.append({
            "action_type": "restart",
            "action_name": f"Restart {asset.asset_name} for performance",
            "action_description": f"Restart service to resolve performance anomaly",
            "priority": "low",
            "estimated_success_rate": self.healing_actions["restart"]["success_rate"],
            "passenger_disruption": self.healing_actions["restart"]["disruption_time"] > 0
        })
        
        return actions
    
    def _handle_security_breach(self, db: Session, asset: InfrastructureAsset, 
                               incident: InfrastructureIncident) -> List[Dict]:
        """Generate healing actions for security breaches."""
        
        actions = []
        
        # Action 1: Immediate notification
        actions.append({
            "action_type": "notification",
            "action_name": "SECURITY BREACH ALERT",
            "action_description": f"Security breach detected on {asset.asset_name} - immediate response required",
            "priority": "critical",
            "estimated_success_rate": 1.0,
            "passenger_disruption": False
        })
        
        # Action 2: Isolate asset (if applicable)
        if asset.asset_type in ["kiosk", "pos"]:
            actions.append({
                "action_type": "config_change",
                "action_name": f"Isolate {asset.asset_name} from network",
                "action_description": f"Network isolation of compromised {asset.asset_type}",
                "priority": "critical",
                "estimated_success_rate": 0.8,
                "passenger_disruption": True
            })
        
        return actions
    
    def _execute_action_simulation(self, db: Session, action_data: Dict) -> Dict:
        """Simulate execution of healing action."""
        
        import random
        
        action_type = action_data["action_type"]
        base_success_rate = self.healing_actions[action_type]["success_rate"]
        
        # Add some randomness and factors
        success_probability = base_success_rate
        
        # Adjust for asset condition
        asset = db.query(InfrastructureAsset).filter(
            InfrastructureAsset.id == action_data["asset_id"]
        ).first()
        
        if asset and asset.health_score:
            success_probability *= asset.health_score
        
        # Simulate execution
        success = random.random() < success_probability
        
        return {
            "success": success,
            "impact_assessment": "positive" if success else "negative",
            "passenger_disruption": self.healing_actions[action_type]["disruption_time"] > 0,
            "execution_time": self.healing_actions[action_type]["disruption_time"],
            "details": {
                "action_type": action_type,
                "base_success_rate": base_success_rate,
                "adjusted_success_rate": success_probability,
                "asset_health_factor": asset.health_score if asset else None
            }
        }
    
    def _update_asset_after_healing(self, db: Session, asset_id: int, execution_result: Dict):
        """Update asset after successful healing action."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset or not execution_result["success"]:
            return
        
        # Update asset based on action type
        if execution_result["details"]["action_type"] == "restart":
            asset.status = "operational"
            asset.last_heartbeat = datetime.utcnow()
            asset.error_count_24h = 0  # Reset error count
        
        elif execution_result["details"]["action_type"] == "config_change":
            asset.network_health = min(1.0, asset.network_health + 0.1)  # Improve network health
        
        asset.updated_at = datetime.utcnow()
        asset.last_updated_by = "auto_healing"
    
    def _calculate_flight_load(self, db: Session, asset: InfrastructureAsset) -> float:
        """Calculate current flight load for asset location."""
        
        # Get flights in next 6 hours for asset terminal
        future_time = datetime.utcnow() + timedelta(hours=6)
        
        flights = db.query(Flight).filter(
            Flight.scheduled_time <= future_time,
            Flight.scheduled_time >= datetime.utcnow(),
            Flight.terminal == asset.terminal
        ).all()
        
        if not flights:
            return 0.0
        
        # Calculate load based on flight count and capacity
        total_flights = len(flights)
        max_flights = 10  # Assumed maximum flights per 6-hour window
        
        return min(total_flights / max_flights, 1.0)
    
    def _find_optimal_maintenance_windows(self, db: Session, asset: InfrastructureAsset, 
                                     flight_load: float) -> List[Dict]:
        """Find optimal maintenance windows based on flight schedules."""
        
        windows = []
        current_time = datetime.utcnow()
        
        # Look at next 48 hours
        for hours_ahead in range(2, 49, 2):  # Every 2 hours for 48 hours
            window_start = current_time + timedelta(hours=hours_ahead)
            window_end = window_start + timedelta(hours=4)  # 4-hour window
            
            # Check if it's during low traffic hours
            is_low_traffic = self._is_low_traffic_period(window_start)
            
            # Calculate flight load during window
            window_flights = db.query(Flight).filter(
                Flight.scheduled_time >= window_start,
                Flight.scheduled_time < window_end,
                Flight.terminal == asset.terminal
            ).count()
            
            window_load = window_flights / 5.0  # Normalize to 0-1
            
            # Calculate priority score
            priority_score = 0
            if is_low_traffic:
                priority_score += 3
            if window_load < self.maintenance_window_rules["flight_load_threshold"]:
                priority_score += 2
            if hours_ahead >= self.maintenance_window_rules["advance_notice_hours"]:
                priority_score += 1
            
            if priority_score > 0:
                windows.append({
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "duration_hours": 4,
                    "is_low_traffic": is_low_traffic,
                    "flight_load": window_load,
                    "priority_score": priority_score
                })
        
        return windows
    
    def _is_low_traffic_period(self, time: datetime) -> bool:
        """Check if time is during low traffic period."""
        
        hour = time.hour
        for start_hour, end_hour in self.maintenance_window_rules["low_traffic_hours"]:
            if start_hour <= end_hour:
                if start_hour <= hour <= end_hour:
                    return True
            else:  # Overnight period (e.g., 22-6)
                if hour >= start_hour or hour <= end_hour:
                    return True
        return False
    
    def _calculate_rerouting_suitability(self, failed_asset: InfrastructureAsset, 
                                       alternative: InfrastructureAsset, 
                                       requirements: Dict) -> Dict:
        """Calculate suitability score for asset rerouting."""
        
        score = 0.0
        factors = {}
        
        # Factor 1: Asset health (40% weight)
        if alternative.health_score:
            health_score = alternative.health_score * 0.4
            score += health_score
            factors["health"] = alternative.health_score
        
        # Factor 2: Proximity (25% weight)
        if failed_asset.location and alternative.location:
            # Simple proximity check (same terminal/gate area)
            same_terminal = failed_asset.terminal == alternative.terminal
            proximity_score = (0.25 if same_terminal else 0.1)
            score += proximity_score
            factors["proximity"] = proximity_score / 0.25
        
        # Factor 3: Current load (20% weight)
        if alternative.error_count_24h is not None:
            load_score = max(0, (5 - alternative.error_count_24h) / 5.0) * 0.2
            score += load_score
            factors["load"] = load_score / 0.2
        
        # Factor 4: Network health (15% weight)
        if alternative.network_health:
            network_score = alternative.network_health * 0.15
            score += network_score
            factors["network"] = alternative.network_health
        
        passenger_impact = "low" if score > 0.7 else "medium" if score > 0.4 else "high"
        
        return {
            "score": min(score, 1.0),
            "factors": factors,
            "passenger_impact": passenger_impact
        }
    
    def _generate_rerouting_plan(self, failed_asset: InfrastructureAsset, 
                               alternative: InfrastructureAsset) -> Dict:
        """Generate detailed rerouting plan."""
        
        return {
            "steps": [
                f"1. Disable services on {failed_asset.asset_name}",
                f"2. Update routing configuration to {alternative.asset_name}",
                f"3. Verify service availability on {alternative.asset_name}",
                f"4. Monitor performance for 30 minutes",
                f"5. Update operations dashboard with new status"
            ],
            "estimated_time_minutes": self.healing_actions["reroute"]["disruption_time"],
            "rollback_plan": [
                f"1. Restore original routing when {failed_asset.asset_name} is recovered",
                f"2. Verify all services are functioning",
                f"3. Update monitoring configuration"
            ]
        }
    
    def _generate_maintenance_recommendations(self, asset: InfrastructureAsset, 
                                        window: Dict) -> List[str]:
        """Generate maintenance recommendations for asset."""
        
        recommendations = []
        
        # Asset-specific recommendations
        if asset.asset_type == "security_scanner":
            recommendations.extend([
                "Calibrate scanning sensors and optics",
                "Update security signature database",
                "Test scanning range and accuracy"
            ])
        elif asset.asset_type == "belt":
            recommendations.extend([
                "Inspect belt tension and alignment",
                "Check motor and drive systems",
                "Test safety sensors and emergency stops"
            ])
        elif asset.asset_type == "kiosk":
            recommendations.extend([
                "Update software and security patches",
                "Clean and calibrate touch screen",
                "Test payment processing systems"
            ])
        
        # Time-based recommendations
        if window.get("is_low_traffic"):
            recommendations.append("Ideal low-traffic window for maintenance")
        else:
            recommendations.append("Consider passenger impact during maintenance")
        
        return recommendations


# Global instance
self_healing = SelfHealingEngine()
