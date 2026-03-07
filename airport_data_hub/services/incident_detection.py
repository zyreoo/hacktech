"""
Infrastructure Incident Detection and Alerting Service.

Advanced incident detection for:
- Asset offline detection
- Repeated error pattern recognition
- Network degradation monitoring
- Anomaly detection and correlation
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    InfrastructureAsset, AssetStatusEvent, NetworkMonitoringSession,
    InfrastructureIncident, Alert
)
from ..database import SessionLocal


class IncidentDetectionEngine:
    """Advanced incident detection and alerting system."""
    
    def __init__(self):
        self.detection_thresholds = {
            "offline_timeout_minutes": 5,           # Asset considered offline after 5 minutes
            "error_frequency_threshold": 5,         # 5 errors in 1 hour triggers incident
            "error_burst_threshold": 3,            # 3 errors in 10 minutes triggers incident
            "network_degradation_latency": 500,       # Latency above this triggers incident
            "network_degradation_packet_loss": 3.0,  # Packet loss above this triggers incident
            "anomaly_detection_window": 60,          # Look back 60 minutes for anomalies
            "incident_correlation_window": 30          # Correlate incidents within 30 minutes
        }
        
        self.incident_types = {
            "asset_offline": {
                "severity": "high",
                "description": "Asset has gone offline and is not responding"
            },
            "repeated_errors": {
                "severity": "medium",
                "description": "Asset is experiencing repeated error events"
            },
            "network_degradation": {
                "severity": "medium",
                "description": "Asset network connectivity is degraded"
            },
            "performance_anomaly": {
                "severity": "low",
                "description": "Asset performance is outside normal parameters"
            },
            "security_breach": {
                "severity": "critical",
                "description": "Security anomaly or tampering detected"
            }
        }
    
    def detect_incidents(self, db: Session) -> List[InfrastructureIncident]:
        """Run comprehensive incident detection across all assets."""
        
        incidents = []
        
        # Get all active assets
        assets = db.query(InfrastructureAsset).filter(
            InfrastructureAsset.status != "maintenance"
        ).all()
        
        for asset in assets:
            # Run different detection algorithms
            asset_incidents = []
            
            # 1. Asset offline detection
            offline_incident = self._detect_asset_offline(db, asset)
            if offline_incident:
                asset_incidents.append(offline_incident)
            
            # 2. Repeated error detection
            error_incident = self._detect_repeated_errors(db, asset)
            if error_incident:
                asset_incidents.append(error_incident)
            
            # 3. Network degradation detection
            network_incident = self._detect_network_degradation(db, asset)
            if network_incident:
                asset_incidents.append(network_incident)
            
            # 4. Performance anomaly detection
            anomaly_incident = self._detect_performance_anomalies(db, asset)
            if anomaly_incident:
                asset_incidents.append(anomaly_incident)
            
            # 5. Security breach detection
            security_incident = self._detect_security_breaches(db, asset)
            if security_incident:
                asset_incidents.append(security_incident)
            
            incidents.extend(asset_incidents)
        
        # Correlate related incidents
        correlated_incidents = self._correlate_incidents(db, incidents)
        
        # Create incident records
        created_incidents = []
        for incident_data in correlated_incidents:
            incident = self._create_incident(db, incident_data)
            created_incidents.append(incident)
        
        return created_incidents
    
    def _detect_asset_offline(self, db: Session, asset: InfrastructureAsset) -> Optional[Dict]:
        """Detect if asset has gone offline."""
        
        # Check last heartbeat
        if not asset.last_heartbeat:
            return {
                "incident_type": "asset_offline",
                "asset_id": asset.id,
                "detection_method": "heartbeat_timeout",
                "severity": "high",
                "title": f"Asset {asset.asset_name} is offline",
                "description": f"No heartbeat received from {asset.asset_name} for over {self.detection_thresholds['offline_timeout_minutes']} minutes",
                "affected_assets": [asset.id],
                "detection_confidence": 0.9
            }
        
        # Calculate time since last heartbeat
        time_since_heartbeat = datetime.utcnow() - asset.last_heartbeat
        minutes_since_heartbeat = time_since_heartbeat.total_seconds() / 60
        
        if minutes_since_heartbeat > self.detection_thresholds["offline_timeout_minutes"]:
            return {
                "incident_type": "asset_offline",
                "asset_id": asset.id,
                "detection_method": "heartbeat_timeout",
                "severity": "high",
                "title": f"Asset {asset.asset_name} is offline",
                "description": f"No heartbeat received from {asset.asset_name} for {int(minutes_since_heartbeat)} minutes",
                "affected_assets": [asset.id],
                "detection_confidence": min(0.9, minutes_since_heartbeat / 10.0)
            }
        
        return None
    
    def _detect_repeated_errors(self, db: Session, asset: InfrastructureAsset) -> Optional[Dict]:
        """Detect patterns of repeated errors."""
        
        # Get recent error events
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        recent_errors = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset.id,
            AssetStatusEvent.event_type == "error",
            AssetStatusEvent.created_at >= cutoff_time
        ).all()
        
        # Check for error frequency threshold
        if len(recent_errors) >= self.detection_thresholds["error_frequency_threshold"]:
            return {
                "incident_type": "repeated_errors",
                "asset_id": asset.id,
                "detection_method": "pattern_analysis",
                "severity": "medium",
                "title": f"Repeated errors on {asset.asset_name}",
                "description": f"Asset {asset.asset_name} has generated {len(recent_errors)} errors in the last hour",
                "affected_assets": [asset.id],
                "detection_confidence": min(0.8, len(recent_errors) / 10.0),
                "error_details": [
                    {
                        "error_code": error.error_code,
                        "message": error.event_message,
                        "timestamp": error.created_at.isoformat()
                    }
                    for error in recent_errors
                ]
            }
        
        # Check for error burst (many errors in short time)
        burst_cutoff = datetime.utcnow() - timedelta(minutes=10)
        burst_errors = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset.id,
            AssetStatusEvent.event_type == "error",
            AssetStatusEvent.created_at >= burst_cutoff
        ).count()
        
        if burst_errors >= self.detection_thresholds["error_burst_threshold"]:
            return {
                "incident_type": "repeated_errors",
                "asset_id": asset.id,
                "detection_method": "burst_detection",
                "severity": "high",
                "title": f"Error burst on {asset.asset_name}",
                "description": f"Asset {asset.asset_name} has generated {burst_errors} errors in the last 10 minutes",
                "affected_assets": [asset.id],
                "detection_confidence": 0.9
            }
        
        return None
    
    def _detect_network_degradation(self, db: Session, asset: InfrastructureAsset) -> Optional[Dict]:
        """Detect network connectivity degradation."""
        
        # Get latest network monitoring session
        latest_session = db.query(NetworkMonitoringSession).filter(
            NetworkMonitoringSession.asset_id == asset.id
        ).order_by(NetworkMonitoringSession.session_start.desc()).first()
        
        if not latest_session:
            return None
        
        # Check latency degradation
        latency_degraded = (latest_session.avg_latency_ms and 
                           latest_session.avg_latency_ms > self.detection_thresholds["network_degradation_latency"])
        
        # Check packet loss degradation
        packet_loss_degraded = (latest_session.packet_loss_percentage and 
                                latest_session.packet_loss_percentage > self.detection_thresholds["network_degradation_packet_loss"])
        
        # Check connection instability
        connection_unstable = (latest_session.disconnect_count > 3 or 
                              not latest_session.connection_stable)
        
        if latency_degraded or packet_loss_degraded or connection_unstable:
            severity = "high" if (latency_degraded and packet_loss_degraded) else "medium"
            
            issues = []
            if latency_degraded:
                issues.append(f"High latency: {latest_session.avg_latency_ms}ms")
            if packet_loss_degraded:
                issues.append(f"High packet loss: {latest_session.packet_loss_percentage}%")
            if connection_unstable:
                issues.append(f"Connection unstable: {latest_session.disconnect_count} disconnects")
            
            return {
                "incident_type": "network_degradation",
                "asset_id": asset.id,
                "detection_method": "network_monitoring",
                "severity": severity,
                "title": f"Network degradation on {asset.asset_name}",
                "description": f"Network connectivity issues detected: {', '.join(issues)}",
                "affected_assets": [asset.id],
                "detection_confidence": 0.8,
                "network_metrics": {
                    "avg_latency_ms": latest_session.avg_latency_ms,
                    "packet_loss_percentage": latest_session.packet_loss_percentage,
                    "disconnect_count": latest_session.disconnect_count,
                    "connection_stable": latest_session.connection_stable
                }
            }
        
        return None
    
    def _detect_performance_anomalies(self, db: Session, asset: InfrastructureAsset) -> Optional[Dict]:
        """Detect performance anomalies using statistical analysis."""
        
        # Get recent performance metrics
        cutoff_time = datetime.utcnow() - timedelta(hours=self.detection_thresholds["anomaly_detection_window"])
        recent_events = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset.id,
            AssetStatusEvent.created_at >= cutoff_time,
            AssetStatusEvent.network_latency_ms.isnot(None)
        ).all()
        
        if len(recent_events) < 5:  # Need sufficient data for anomaly detection
            return None
        
        # Extract latency values
        latencies = [event.network_latency_ms for event in recent_events if event.network_latency_ms]
        
        if not latencies:
            return None
        
        # Calculate statistical measures
        import statistics
        mean_latency = statistics.mean(latencies)
        stdev_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0
        
        # Check for recent anomalies (values beyond 2 standard deviations)
        recent_cutoff = datetime.utcnow() - timedelta(minutes=10)
        recent_latencies = [
            event.network_latency_ms for event in recent_events
            if event.network_latency_ms and event.created_at >= recent_cutoff
        ]
        
        for latency in recent_latencies:
            z_score = abs(latency - mean_latency) / stdev_latency if stdev_latency > 0 else 0
            
            if z_score > 2.0:  # Beyond 2 standard deviations
                return {
                    "incident_type": "performance_anomaly",
                    "asset_id": asset.id,
                    "detection_method": "statistical_analysis",
                    "severity": "low",
                    "title": f"Performance anomaly on {asset.asset_name}",
                    "description": f"Unusual latency detected: {latency}ms (normal: {mean_latency:.1f}±{stdev_latency:.1f}ms)",
                    "affected_assets": [asset.id],
                    "detection_confidence": 0.7,
                    "anomaly_details": {
                        "observed_value": latency,
                        "expected_mean": mean_latency,
                        "expected_stdev": stdev_latency,
                        "z_score": z_score
                    }
                }
        
        return None
    
    def _detect_security_breaches(self, db: Session, asset: InfrastructureAsset) -> Optional[Dict]:
        """Detect security-related incidents."""
        
        # Check for tamper detection
        if asset.tamper_detected:
            return {
                "incident_type": "security_breach",
                "asset_id": asset.id,
                "detection_method": "tamper_detection",
                "severity": "critical",
                "title": f"Security breach on {asset.asset_name}",
                "description": f"Tampering detected on {asset.asset_name} at {asset.location}",
                "affected_assets": [asset.id],
                "detection_confidence": 0.95,
                "security_details": {
                    "tamper_detected": asset.tamper_detected,
                    "tamper_alert_count": asset.tamper_alert_count,
                    "last_tamper_time": asset.last_tamper_time.isoformat() if asset.last_tamper_time else None
                }
            }
        
        # Check for unusual access patterns (simplified)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        recent_events = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset.id,
            AssetStatusEvent.created_at >= cutoff_time
        ).count()
        
        # High frequency of status changes could indicate security issues
        if recent_events > 20:  # More than 20 events in 1 hour
            return {
                "incident_type": "security_breach",
                "asset_id": asset.id,
                "detection_method": "pattern_analysis",
                "severity": "medium",
                "title": f"Suspicious activity on {asset.asset_name}",
                "description": f"Unusual activity pattern detected: {recent_events} events in the last hour",
                "affected_assets": [asset.id],
                "detection_confidence": 0.6,
                "security_details": {
                    "event_frequency": recent_events,
                    "suspicious_pattern": "high_frequency_status_changes"
                }
            }
        
        return None
    
    def _correlate_incidents(self, db: Session, incidents: List[Dict]) -> List[Dict]:
        """Correlate related incidents to avoid duplicates."""
        
        correlated_incidents = []
        incident_window = self.detection_thresholds["incident_correlation_window"]
        
        for incident in incidents:
            # Check if similar incident already exists
            similar_incident = db.query(InfrastructureIncident).filter(
                InfrastructureIncident.primary_asset_id == incident["asset_id"],
                InfrastructureIncident.incident_type == incident["incident_type"],
                InfrastructureIncident.status == "open",
                InfrastructureIncident.created_at >= datetime.utcnow() - timedelta(minutes=incident_window)
            ).first()
            
            if similar_incident:
                # Update existing incident instead of creating new one
                similar_incident.detection_confidence = max(
                    similar_incident.detection_confidence or 0,
                    incident["detection_confidence"]
                )
                similar_incident.updated_at = datetime.utcnow()
                continue
            
            # Generate unique incident ID
            incident["incident_id"] = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            correlated_incidents.append(incident)
        
        return correlated_incidents
    
    def _create_incident(self, db: Session, incident_data: Dict) -> InfrastructureIncident:
        """Create infrastructure incident record."""
        
        incident = InfrastructureIncident(
            incident_id=incident_data["incident_id"],
            incident_type=incident_data["incident_type"],
            severity=incident_data["severity"],
            title=incident_data["title"],
            description=incident_data["description"],
            primary_asset_id=incident_data["asset_id"],
            affected_assets=json.dumps(incident_data["affected_assets"]),
            detection_method=incident_data["detection_method"],
            detection_time=datetime.utcnow(),
            detection_confidence=incident_data["detection_confidence"],
            operational_impact=self._assess_operational_impact(incident_data),
            passenger_impact=self._assess_passenger_impact(incident_data),
            status="open"
        )
        
        db.add(incident)
        db.flush()
        
        # Create corresponding alert
        self._create_alert(db, incident, incident_data)
        
        return incident
    
    def _create_alert(self, db: Session, incident: InfrastructureIncident, incident_data: Dict):
        """Create alert for incident."""
        
        alert = Alert(
            alert_type="infrastructure_incident",
            severity=incident_data["severity"],
            source_module="incident_detection",
            message=incident_data["title"],
            related_entity_type="infrastructure_incident",
            related_entity_id=incident.incident_id,
            created_at=datetime.utcnow(),
            uniqueness_key=f"infrastructure_incident:{incident.incident_id}"
        )
        
        db.add(alert)
    
    def _assess_operational_impact(self, incident_data: Dict) -> str:
        """Assess operational impact of incident."""
        
        incident_type = incident_data["incident_type"]
        severity = incident_data["severity"]
        
        impact_mapping = {
            ("asset_offline", "critical"): "critical",
            ("asset_offline", "high"): "high",
            ("repeated_errors", "high"): "high",
            ("repeated_errors", "medium"): "medium",
            ("network_degradation", "high"): "high",
            ("network_degradation", "medium"): "medium",
            ("performance_anomaly", "medium"): "low",
            ("performance_anomaly", "low"): "minimal",
            ("security_breach", "critical"): "critical",
            ("security_breach", "medium"): "high"
        }
        
        return impact_mapping.get((incident_type, severity), "medium")
    
    def _assess_passenger_impact(self, incident_data: Dict) -> str:
        """Assess passenger impact of incident."""
        
        incident_type = incident_data["incident_type"]
        severity = incident_data["severity"]
        
        impact_mapping = {
            ("asset_offline", "critical"): "high",
            ("asset_offline", "high"): "medium",
            ("repeated_errors", "high"): "medium",
            ("repeated_errors", "medium"): "low",
            ("network_degradation", "high"): "medium",
            ("network_degradation", "medium"): "low",
            ("performance_anomaly", "medium"): "low",
            ("performance_anomaly", "low"): "none",
            ("security_breach", "critical"): "high",
            ("security_breach", "medium"): "medium"
        }
        
        return impact_mapping.get((incident_type, severity), "low")
    
    def get_active_incidents(self, db: Session, severity: Optional[str] = None, 
                          incident_type: Optional[str] = None) -> List[InfrastructureIncident]:
        """Get currently active incidents."""
        
        query = db.query(InfrastructureIncident).filter(
            InfrastructureIncident.status.in_(["open", "investigating"])
        )
        
        if severity:
            query = query.filter(InfrastructureIncident.severity == severity)
        
        if incident_type:
            query = query.filter(InfrastructureIncident.incident_type == incident_type)
        
        return query.order_by(InfrastructureIncident.detection_time.desc()).all()
    
    def resolve_incident(self, db: Session, incident_id: str, resolution_data: Dict) -> InfrastructureIncident:
        """Resolve an incident with resolution details."""
        
        incident = db.query(InfrastructureIncident).filter(
            InfrastructureIncident.incident_id == incident_id
        ).first()
        
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        # Update incident with resolution
        incident.status = "resolved"
        incident.resolution_time = datetime.utcnow()
        incident.resolution_description = resolution_data.get("description")
        incident.root_cause = resolution_data.get("root_cause")
        incident.preventive_actions = json.dumps(resolution_data.get("preventive_actions", []))
        incident.updated_at = datetime.utcnow()
        
        return incident
    
    def get_incident_summary(self, db: Session, hours_back: int = 24) -> Dict:
        """Get summary of recent incidents."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        incidents = db.query(InfrastructureIncident).filter(
            InfrastructureIncident.detection_time >= cutoff_time
        ).all()
        
        summary = {
            "period_hours": hours_back,
            "total_incidents": len(incidents),
            "incidents_by_type": {},
            "incidents_by_severity": {},
            "incidents_by_status": {},
            "average_resolution_time": 0,
            "mttr": 0  # Mean Time To Resolve
        }
        
        resolution_times = []
        
        for incident in incidents:
            # Count by type
            incident_type = incident.incident_type
            summary["incidents_by_type"][incident_type] = summary["incidents_by_type"].get(incident_type, 0) + 1
            
            # Count by severity
            severity = incident.severity
            summary["incidents_by_severity"][severity] = summary["incidents_by_severity"].get(severity, 0) + 1
            
            # Count by status
            status = incident.status
            summary["incidents_by_status"][status] = summary["incidents_by_status"].get(status, 0) + 1
            
            # Calculate resolution time
            if incident.resolution_time and incident.detection_time:
                resolution_minutes = (incident.resolution_time - incident.detection_time).total_seconds() / 60
                resolution_times.append(resolution_minutes)
        
        # Calculate average resolution time
        if resolution_times:
            summary["average_resolution_time"] = sum(resolution_times) / len(resolution_times)
            summary["mttr"] = summary["average_resolution_time"]
        
        return summary


# Global instance
incident_detection = IncidentDetectionEngine()
