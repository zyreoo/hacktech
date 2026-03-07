"""
Network Monitoring and Heartbeat Service.

Real-time network monitoring for:
- Heartbeat checks for all connected assets
- Latency and packet loss monitoring
- Service availability tracking
- Connectivity status management
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..models import (
    InfrastructureAsset, NetworkMonitoringSession, AssetStatusEvent,
    InfrastructureIncident
)
from ..database import SessionLocal


class NetworkMonitoringEngine:
    """Advanced network monitoring and heartbeat system."""
    
    def __init__(self):
        self.monitoring_intervals = {
            "security_scanner": 30,      # 30 seconds
            "belt": 60,                  # 1 minute
            "kiosk": 15,                 # 15 seconds
            "pos": 10,                    # 10 seconds
            "display": 45,                 # 45 seconds
            "sensor": 120                  # 2 minutes
        }
        
        self.network_thresholds = {
            "critical_latency_ms": 1000,
            "warning_latency_ms": 500,
            "critical_packet_loss": 5.0,
            "warning_packet_loss": 2.0,
            "max_disconnects": 3,
            "connection_timeout_seconds": 10
        }
        
        self.service_ports = {
            "kiosk": [80, 443, 8080],           # Web services
            "pos": [8081, 8082, 8083],              # POS services
            "security_scanner": [9000, 9001],         # Scanner services
            "display": [8084, 8085],                  # Display services
            "belt": [8086, 8087],                    # Control services
            "sensor": [8088, 8089]                     # Sensor services
        }
    
    def start_monitoring_session(self, db: Session, asset_id: int) -> NetworkMonitoringSession:
        """Start a new monitoring session for an asset."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Create new monitoring session
        session = NetworkMonitoringSession(
            asset_id=asset_id,
            session_start=datetime.utcnow(),
            connection_stable=True,
            services_monitored=json.dumps(self.service_ports.get(asset.asset_type, []))
        )
        
        db.add(session)
        db.flush()
        
        # Perform initial connectivity check
        connectivity_result = self._check_asset_connectivity(asset)
        
        # Update session with initial results
        session.avg_latency_ms = connectivity_result["latency_ms"]
        session.max_latency_ms = connectivity_result["latency_ms"]
        session.min_latency_ms = connectivity_result["latency_ms"]
        session.packet_loss_percentage = connectivity_result["packet_loss"]
        session.connection_stable = connectivity_result["connected"]
        session.services_available = json.dumps(connectivity_result["available_services"])
        session.services_degraded = json.dumps(connectivity_result["degraded_services"])
        
        # Create heartbeat event
        self._create_heartbeat_event(
            db, asset_id, connectivity_result,
            session_id=session.id
        )
        
        return session
    
    def record_heartbeat(self, db: Session, asset_id: int, heartbeat_data: Dict) -> NetworkMonitoringSession:
        """Record heartbeat data and update monitoring session."""
        
        # Get active monitoring session
        session = db.query(NetworkMonitoringSession).filter(
            NetworkMonitoringSession.asset_id == asset_id,
            NetworkMonitoringSession.session_end.is_(None)
        ).order_by(NetworkMonitoringSession.session_start.desc()).first()
        
        if not session:
            # Start new session if none exists
            session = self.start_monitoring_session(db, asset_id)
        
        # Update session metrics
        latency = heartbeat_data.get("latency_ms", 0)
        packet_loss = heartbeat_data.get("packet_loss", 0)
        
        # Update latency statistics
        if session.avg_latency_ms is None:
            session.avg_latency_ms = latency
            session.max_latency_ms = latency
            session.min_latency_ms = latency
        else:
            # Calculate rolling average
            session.avg_latency_ms = (session.avg_latency_ms + latency) / 2
            session.max_latency_ms = max(session.max_latency_ms, latency)
            session.min_latency_ms = min(session.min_latency_ms, latency)
        
        session.packet_loss_percentage = packet_loss
        
        # Check for connection issues
        if heartbeat_data.get("connected", False):
            if not session.connection_stable:
                # Reconnection detected
                session.reconnect_count += 1
                session.connection_stable = True
        else:
            # Disconnection detected
            session.disconnect_count += 1
            session.connection_stable = False
        
        # Update service availability
        available_services = heartbeat_data.get("available_services", [])
        degraded_services = heartbeat_data.get("degraded_services", [])
        
        session.services_available = json.dumps(available_services)
        session.services_degraded = json.dumps(degraded_services)
        
        # Create heartbeat event
        self._create_heartbeat_event(
            db, asset_id, heartbeat_data,
            session_id=session.id
        )
        
        return session
    
    def end_monitoring_session(self, db: Session, asset_id: int, end_reason: Optional[str] = None) -> NetworkMonitoringSession:
        """End monitoring session for an asset."""
        
        session = db.query(NetworkMonitoringSession).filter(
            NetworkMonitoringSession.asset_id == asset_id,
            NetworkMonitoringSession.session_end.is_(None)
        ).order_by(NetworkMonitoringSession.session_start.desc()).first()
        
        if not session:
            raise ValueError(f"No active monitoring session found for asset {asset_id}")
        
        # Calculate session duration
        session.session_end = datetime.utcnow()
        session.session_duration_minutes = int(
            (session.session_end - session.session_start).total_seconds() / 60
        )
        
        # Create session end event
        self._create_session_end_event(db, asset_id, session, end_reason)
        
        return session
    
    def check_network_health(self, db: Session, asset_id: int) -> Dict:
        """Perform comprehensive network health check."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Perform connectivity test
        connectivity_result = self._check_asset_connectivity(asset)
        
        # Get recent monitoring data
        recent_session = db.query(NetworkMonitoringSession).filter(
            NetworkMonitoringSession.asset_id == asset_id
        ).order_by(NetworkMonitoringSession.session_start.desc()).first()
        
        # Calculate health metrics
        health_metrics = {
            "asset_id": asset_id,
            "asset_name": asset.asset_name,
            "asset_type": asset.asset_type,
            "location": asset.location,
            "timestamp": datetime.utcnow().isoformat(),
            "connectivity": {
                "connected": connectivity_result["connected"],
                "latency_ms": connectivity_result["latency_ms"],
                "packet_loss": connectivity_result["packet_loss"],
                "jitter_ms": connectivity_result["jitter_ms"]
            },
            "services": {
                "total_services": len(self.service_ports.get(asset.asset_type, [])),
                "available_services": connectivity_result["available_services"],
                "degraded_services": connectivity_result["degraded_services"],
                "unavailable_services": connectivity_result["unavailable_services"]
            },
            "session_stats": None,
            "health_status": self._get_network_health_status(connectivity_result),
            "recommendations": self._generate_network_recommendations(connectivity_result, asset)
        }
        
        # Add session statistics if available
        if recent_session:
            health_metrics["session_stats"] = {
                "current_session_duration": int(
                    (datetime.utcnow() - recent_session.session_start).total_seconds() / 60
                ),
                "avg_latency": recent_session.avg_latency_ms,
                "max_latency": recent_session.max_latency_ms,
                "min_latency": recent_session.min_latency_ms,
                "packet_loss": recent_session.packet_loss_percentage,
                "disconnect_count": recent_session.disconnect_count,
                "reconnect_count": recent_session.reconnect_count,
                "connection_stable": recent_session.connection_stable
            }
        
        return health_metrics
    
    def get_network_anomalies(self, db: Session, hours_back: int = 24) -> List[Dict]:
        """Detect network anomalies from monitoring data."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Get recent monitoring sessions
        sessions = db.query(NetworkMonitoringSession).filter(
            NetworkMonitoringSession.session_start >= cutoff_time
        ).all()
        
        anomalies = []
        
        for session in sessions:
            session_anomalies = []
            
            # Check for high latency
            if (session.avg_latency_ms and 
                session.avg_latency_ms > self.network_thresholds["critical_latency_ms"]):
                session_anomalies.append({
                    "type": "high_latency",
                    "severity": "critical",
                    "value": session.avg_latency_ms,
                    "threshold": self.network_thresholds["critical_latency_ms"]
                })
            elif (session.avg_latency_ms and 
                  session.avg_latency_ms > self.network_thresholds["warning_latency_ms"]):
                session_anomalies.append({
                    "type": "high_latency",
                    "severity": "warning",
                    "value": session.avg_latency_ms,
                    "threshold": self.network_thresholds["warning_latency_ms"]
                })
            
            # Check for high packet loss
            if (session.packet_loss_percentage and 
                session.packet_loss_percentage > self.network_thresholds["critical_packet_loss"]):
                session_anomalies.append({
                    "type": "high_packet_loss",
                    "severity": "critical",
                    "value": session.packet_loss_percentage,
                    "threshold": self.network_thresholds["critical_packet_loss"]
                })
            elif (session.packet_loss_percentage and 
                  session.packet_loss_percentage > self.network_thresholds["warning_packet_loss"]):
                session_anomalies.append({
                    "type": "high_packet_loss",
                    "severity": "warning",
                    "value": session.packet_loss_percentage,
                    "threshold": self.network_thresholds["warning_packet_loss"]
                })
            
            # Check for connection instability
            if session.disconnect_count > self.network_thresholds["max_disconnects"]:
                session_anomalies.append({
                    "type": "connection_instability",
                    "severity": "critical",
                    "value": session.disconnect_count,
                    "threshold": self.network_thresholds["max_disconnects"]
                })
            
            # Add anomalies to results if any found
            if session_anomalies:
                anomalies.append({
                    "asset_id": session.asset_id,
                    "session_id": session.id,
                    "session_start": session.session_start.isoformat(),
                    "anomalies": session_anomalies
                })
        
        return anomalies
    
    def get_connectivity_summary(self, db: Session, terminal: Optional[str] = None) -> Dict:
        """Get connectivity summary for assets."""
        
        # Get assets with monitoring data
        query = db.query(InfrastructureAsset)
        if terminal:
            query = query.filter(InfrastructureAsset.terminal == terminal)
        
        assets = query.all()
        
        summary = {
            "total_assets": len(assets),
            "connected_assets": 0,
            "disconnected_assets": 0,
            "degraded_assets": 0,
            "assets_by_type": {},
            "average_latency": 0,
            "average_packet_loss": 0,
            "critical_issues": []
        }
        
        total_latency = 0
        total_packet_loss = 0
        assets_with_metrics = 0
        
        for asset in assets:
            asset_type = asset.asset_type
            if asset_type not in summary["assets_by_type"]:
                summary["assets_by_type"][asset_type] = {
                    "total": 0,
                    "connected": 0,
                    "disconnected": 0,
                    "degraded": 0
                }
            
            summary["assets_by_type"][asset_type]["total"] += 1
            
            # Get latest monitoring session
            latest_session = db.query(NetworkMonitoringSession).filter(
                NetworkMonitoringSession.asset_id == asset.id
            ).order_by(NetworkMonitoringSession.session_start.desc()).first()
            
            if latest_session:
                # Determine connectivity status
                if latest_session.connection_stable and latest_session.disconnect_count == 0:
                    status = "connected"
                    summary["connected_assets"] += 1
                    summary["assets_by_type"][asset_type]["connected"] += 1
                elif latest_session.disconnect_count > self.network_thresholds["max_disconnects"]:
                    status = "disconnected"
                    summary["disconnected_assets"] += 1
                    summary["assets_by_type"][asset_type]["disconnected"] += 1
                else:
                    status = "degraded"
                    summary["degraded_assets"] += 1
                    summary["assets_by_type"][asset_type]["degraded"] += 1
                
                # Add to averages
                if latest_session.avg_latency_ms:
                    total_latency += latest_session.avg_latency_ms
                    total_packet_loss += latest_session.packet_loss_percentage or 0
                    assets_with_metrics += 1
                
                # Check for critical issues
                if (latest_session.avg_latency_ms and 
                    latest_session.avg_latency_ms > self.network_thresholds["critical_latency_ms"]):
                    summary["critical_issues"].append({
                        "asset_id": asset.id,
                        "asset_name": asset.asset_name,
                        "issue": "critical_latency",
                        "value": latest_session.avg_latency_ms
                    })
                
                if (latest_session.packet_loss_percentage and 
                    latest_session.packet_loss_percentage > self.network_thresholds["critical_packet_loss"]):
                    summary["critical_issues"].append({
                        "asset_id": asset.id,
                        "asset_name": asset.asset_name,
                        "issue": "critical_packet_loss",
                        "value": latest_session.packet_loss_percentage
                    })
        
        # Calculate averages
        if assets_with_metrics > 0:
            summary["average_latency"] = round(total_latency / assets_with_metrics, 2)
            summary["average_packet_loss"] = round(total_packet_loss / assets_with_metrics, 2)
        
        return summary
    
    def _check_asset_connectivity(self, asset: InfrastructureAsset) -> Dict:
        """Simulate connectivity check for an asset."""
        
        # Simulate network connectivity test
        # In production, this would use actual network testing tools
        
        base_latency = {
            "kiosk": 50,
            "pos": 30,
            "security_scanner": 100,
            "display": 80,
            "belt": 150,
            "sensor": 200
        }
        
        # Add some randomness for simulation
        import random
        latency = base_latency.get(asset.asset_type, 100) + random.randint(-20, 50)
        packet_loss = max(0, random.uniform(0, 3))
        jitter = random.uniform(0, 10)
        
        # Determine connectivity based on asset status and network metrics
        connected = asset.status != "offline" and asset.status != "failed"
        
        if latency > self.network_thresholds["critical_latency_ms"]:
            connected = False
        elif packet_loss > self.network_thresholds["critical_packet_loss"]:
            connected = False
        
        # Check service availability
        expected_services = self.service_ports.get(asset.asset_type, [])
        available_services = []
        degraded_services = []
        unavailable_services = []
        
        for service_port in expected_services:
            if connected and packet_loss < 1.0:
                available_services.append(f"service_{service_port}")
            elif connected and packet_loss < 3.0:
                degraded_services.append(f"service_{service_port}")
            else:
                unavailable_services.append(f"service_{service_port}")
        
        return {
            "connected": connected,
            "latency_ms": latency,
            "packet_loss": round(packet_loss, 2),
            "jitter_ms": round(jitter, 2),
            "available_services": available_services,
            "degraded_services": degraded_services,
            "unavailable_services": unavailable_services
        }
    
    def _get_network_health_status(self, connectivity_result: Dict) -> str:
        """Determine overall network health status."""
        
        latency = connectivity_result["latency_ms"]
        packet_loss = connectivity_result["packet_loss"]
        connected = connectivity_result["connected"]
        
        if not connected:
            return "offline"
        elif latency > self.network_thresholds["critical_latency_ms"] or packet_loss > self.network_thresholds["critical_packet_loss"]:
            return "critical"
        elif latency > self.network_thresholds["warning_latency_ms"] or packet_loss > self.network_thresholds["warning_packet_loss"]:
            return "degraded"
        else:
            return "healthy"
    
    def _generate_network_recommendations(self, connectivity_result: Dict, asset: InfrastructureAsset) -> List[str]:
        """Generate network-related recommendations."""
        
        recommendations = []
        latency = connectivity_result["latency_ms"]
        packet_loss = connectivity_result["packet_loss"]
        connected = connectivity_result["connected"]
        
        if not connected:
            recommendations.extend([
                "Asset is offline - check power and network connections",
                "Verify IP configuration and firewall settings",
                "Contact network operations team immediately"
            ])
        elif latency > self.network_thresholds["critical_latency_ms"]:
            recommendations.extend([
                "Critical latency detected - investigate network congestion",
                "Check for network hardware issues",
                "Consider network path optimization"
            ])
        elif packet_loss > self.network_thresholds["critical_packet_loss"]:
            recommendations.extend([
                "Critical packet loss detected - check network equipment",
                "Inspect cabling and connections",
                "Test network segment isolation"
            ])
        elif latency > self.network_thresholds["warning_latency_ms"]:
            recommendations.extend([
                "Elevated latency - monitor for trends",
                "Consider load balancing",
                "Review network configuration"
            ])
        elif packet_loss > self.network_thresholds["warning_packet_loss"]:
            recommendations.extend([
                "Elevated packet loss - investigate interference",
                "Check for hardware degradation",
                "Monitor network quality metrics"
            ])
        
        return recommendations
    
    def _create_heartbeat_event(self, db: Session, asset_id: int, 
                               heartbeat_data: Dict, session_id: Optional[int] = None):
        """Create heartbeat status event."""
        
        event = AssetStatusEvent(
            asset_id=asset_id,
            event_type="heartbeat",
            event_message=f"Network heartbeat - latency: {heartbeat_data.get('latency_ms', 'N/A')}ms, packet loss: {heartbeat_data.get('packet_loss', 'N/A')}%",
            network_latency_ms=heartbeat_data.get("latency_ms"),
            packet_loss_percentage=heartbeat_data.get("packet_loss"),
            event_data=json.dumps({
                "session_id": session_id,
                "connected": heartbeat_data.get("connected"),
                "available_services": heartbeat_data.get("available_services", []),
                "degraded_services": heartbeat_data.get("degraded_services", [])
            }),
            automatic_detection=True
        )
        
        db.add(event)
    
    def _create_session_end_event(self, db: Session, asset_id: int, 
                                session: NetworkMonitoringSession, end_reason: Optional[str]):
        """Create session end event."""
        
        event = AssetStatusEvent(
            asset_id=asset_id,
            event_type="heartbeat",
            event_message=f"Monitoring session ended - duration: {session.session_duration_minutes} minutes",
            event_data=json.dumps({
                "session_id": session.id,
                "duration_minutes": session.session_duration_minutes,
                "avg_latency": session.avg_latency_ms,
                "packet_loss": session.packet_loss_percentage,
                "disconnect_count": session.disconnect_count,
                "reconnect_count": session.reconnect_count,
                "end_reason": end_reason
            }),
            automatic_detection=True
        )
        
        db.add(event)


# Global instance
network_monitoring = NetworkMonitoringEngine()
