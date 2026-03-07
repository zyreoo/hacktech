"""
Infrastructure Asset Monitoring Service.

Comprehensive asset registry and monitoring system for:
- Asset registration and lifecycle management
- Real-time status tracking and event logging
- Operational metrics collection and analysis
- Health monitoring and performance tracking
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from ..models import (
    InfrastructureAsset, AssetStatusEvent, AssetMaintenanceRecord,
    NetworkMonitoringSession, InfrastructureIncident
)
from ..database import SessionLocal


class AssetMonitoringEngine:
    """Comprehensive asset monitoring and registry system."""
    
    def __init__(self):
        self.asset_types = {
            "security_scanner": {
                "default_health_threshold": 0.8,
                "critical_latency_ms": 1000,
                "max_packet_loss": 5.0,
                "maintenance_interval_hours": 168  # 7 days
            },
            "belt": {
                "default_health_threshold": 0.75,
                "critical_latency_ms": 2000,
                "max_packet_loss": 3.0,
                "maintenance_interval_hours": 72  # 3 days
            },
            "kiosk": {
                "default_health_threshold": 0.85,
                "critical_latency_ms": 500,
                "max_packet_loss": 2.0,
                "maintenance_interval_hours": 24  # 1 day
            },
            "pos": {
                "default_health_threshold": 0.9,
                "critical_latency_ms": 300,
                "max_packet_loss": 1.0,
                "maintenance_interval_hours": 12  # 12 hours
            },
            "display": {
                "default_health_threshold": 0.8,
                "critical_latency_ms": 800,
                "max_packet_loss": 4.0,
                "maintenance_interval_hours": 48  # 2 days
            },
            "sensor": {
                "default_health_threshold": 0.7,
                "critical_latency_ms": 1500,
                "max_packet_loss": 6.0,
                "maintenance_interval_hours": 96  # 4 days
            }
        }
    
    def register_asset(self, db: Session, asset_data: Dict) -> InfrastructureAsset:
        """Register a new infrastructure asset in the registry."""
        
        # Create new asset
        asset = InfrastructureAsset(
            asset_type=asset_data["asset_type"],
            asset_name=asset_data["asset_name"],
            location=asset_data["location"],
            terminal=asset_data.get("terminal"),
            gate=asset_data.get("gate"),
            status=asset_data.get("status", "operational"),
            ip_address=asset_data.get("ip_address"),
            mac_address=asset_data.get("mac_address"),
            health_score=asset_data.get("health_score", 1.0),
            network_health=asset_data.get("network_health", 1.0),
            last_heartbeat=datetime.utcnow(),
            uptime_percentage=100.0,
            total_uptime_hours=0.0,
            usage_cycles=0,
            total_usage_time=0.0,
            maintenance_priority="normal",
            last_updated_by="registration"
        )
        
        db.add(asset)
        db.flush()
        
        # Create registration event
        self._create_status_event(
            db, asset.id, "status_change", 
            previous_status=None, new_status="registered",
            event_message=f"Asset {asset.asset_name} registered in monitoring system",
            event_severity="info",
            operator_id=asset_data.get("operator_id")
        )
        
        return asset
    
    def update_asset_status(self, db: Session, asset_id: int, status_data: Dict) -> AssetStatusEvent:
        """Update asset status and create event log."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        previous_status = asset.status
        new_status = status_data.get("status", previous_status)
        
        # Update asset fields
        if "status" in status_data:
            asset.status = status_data["status"]
        if "health_score" in status_data:
            asset.health_score = status_data["health_score"]
        if "network_health" in status_data:
            asset.network_health = status_data["network_health"]
        if "network_latency_ms" in status_data:
            asset.network_latency_ms = status_data["network_latency_ms"]
        if "packet_loss_percentage" in status_data:
            asset.packet_loss_percentage = status_data["packet_loss_percentage"]
        if "error_count_24h" in status_data:
            asset.error_count_24h = status_data["error_count_24h"]
        if "usage_cycles" in status_data:
            asset.usage_cycles = status_data["usage_cycles"]
        if "total_usage_time" in status_data:
            asset.total_usage_time = status_data["total_usage_time"]
        
        asset.last_heartbeat = datetime.utcnow()
        asset.updated_at = datetime.utcnow()
        asset.last_updated_by = status_data.get("updated_by", "system")
        
        # Create status change event
        event = self._create_status_event(
            db, asset_id, "status_change",
            previous_status=previous_status, new_status=new_status,
            event_message=status_data.get("event_message", f"Status changed from {previous_status} to {new_status}"),
            event_severity=status_data.get("severity", "info"),
            network_latency_ms=status_data.get("network_latency_ms"),
            packet_loss_percentage=status_data.get("packet_loss_percentage"),
            operator_id=status_data.get("operator_id"),
            event_data=json.dumps(status_data.get("event_data", {}))
        )
        
        return event
    
    def record_heartbeat(self, db: Session, asset_id: int, heartbeat_data: Dict) -> AssetStatusEvent:
        """Record asset heartbeat and update metrics."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Update heartbeat and metrics
        asset.last_heartbeat = datetime.utcnow()
        asset.network_latency_ms = heartbeat_data.get("latency_ms", asset.network_latency_ms)
        asset.packet_loss_percentage = heartbeat_data.get("packet_loss", asset.packet_loss_percentage)
        
        # Calculate uptime if we have previous heartbeat
        if heartbeat_data.get("status") == "online":
            asset.uptime_percentage = self._calculate_uptime_percentage(db, asset_id)
        
        asset.updated_at = datetime.utcnow()
        
        # Create heartbeat event
        event = self._create_status_event(
            db, asset_id, "heartbeat",
            event_message=f"Heartbeat received - latency: {asset.network_latency_ms}ms, packet loss: {asset.packet_loss_percentage}%",
            network_latency_ms=asset.network_latency_ms,
            packet_loss_percentage=asset.packet_loss_percentage,
            event_data=json.dumps(heartbeat_data)
        )
        
        return event
    
    def record_asset_error(self, db: Session, asset_id: int, error_data: Dict) -> AssetStatusEvent:
        """Record asset error and update error counters."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Update error tracking
        asset.error_count_24h += 1
        asset.last_error_time = datetime.utcnow()
        
        # Update status if error is critical
        if error_data.get("severity") == "critical":
            asset.status = "failed"
        
        asset.updated_at = datetime.utcnow()
        
        # Create error event
        event = self._create_status_event(
            db, asset_id, "error",
            event_message=error_data.get("message", "Asset error recorded"),
            event_severity=error_data.get("severity", "error"),
            error_code=error_data.get("error_code"),
            network_latency_ms=error_data.get("network_latency_ms"),
            packet_loss_percentage=error_data.get("packet_loss"),
            event_data=json.dumps(error_data.get("error_details", {}))
        )
        
        return event
    
    def get_asset_registry(self, db: Session, asset_type: Optional[str] = None, 
                         terminal: Optional[str] = None, status: Optional[str] = None) -> List[InfrastructureAsset]:
        """Get filtered asset registry."""
        
        query = db.query(InfrastructureAsset)
        
        if asset_type:
            query = query.filter(InfrastructureAsset.asset_type == asset_type)
        if terminal:
            query = query.filter(InfrastructureAsset.terminal == terminal)
        if status:
            query = query.filter(InfrastructureAsset.status == status)
        
        return query.order_by(InfrastructureAsset.asset_name).all()
    
    def get_asset_events(self, db: Session, asset_id: int, 
                       event_type: Optional[str] = None, hours_back: int = 24) -> List[AssetStatusEvent]:
        """Get recent events for an asset."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        query = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset_id,
            AssetStatusEvent.created_at >= cutoff_time
        )
        
        if event_type:
            query = query.filter(AssetStatusEvent.event_type == event_type)
        
        return query.order_by(AssetStatusEvent.created_at.desc()).all()
    
    def get_assets_by_health_score(self, db: Session, min_health: float = 0.0, 
                                max_health: float = 1.0) -> List[InfrastructureAsset]:
        """Get assets within health score range."""
        
        return db.query(InfrastructureAsset).filter(
            InfrastructureAsset.health_score >= min_health,
            InfrastructureAsset.health_score <= max_health
        ).order_by(InfrastructureAsset.health_score).all()
    
    def get_critical_assets(self, db: Session) -> List[InfrastructureAsset]:
        """Get assets in critical state or with low health scores."""
        
        return db.query(InfrastructureAsset).filter(
            or_(
                InfrastructureAsset.status == "failed",
                InfrastructureAsset.status == "offline",
                InfrastructureAsset.health_score < 0.5,
                InfrastructureAsset.failure_probability_24h > 0.7
            )
        ).order_by(InfrastructureAsset.health_score).all()
    
    def get_asset_uptime_stats(self, db: Session, asset_id: int, days: int = 30) -> Dict:
        """Calculate uptime statistics for an asset."""
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Get status events in the period
        events = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset_id,
            AssetStatusEvent.created_at >= cutoff_time
        ).order_by(AssetStatusEvent.created_at).all()
        
        if not events:
            return {
                "period_days": days,
                "uptime_percentage": 0,
                "downtime_hours": 0,
                "error_count": 0,
                "status_changes": 0
            }
        
        # Calculate uptime based on status changes
        total_time = days * 24 * 60  # total minutes in period
        downtime_minutes = 0
        error_count = 0
        status_changes = 0
        
        current_status = "operational"
        last_change_time = cutoff_time
        
        for event in events:
            if event.event_type == "status_change":
                status_changes += 1
                
                # Calculate downtime for previous status
                if current_status in ["failed", "offline", "maintenance"]:
                    downtime_minutes += (event.created_at - last_change_time).total_seconds() / 60
                
                current_status = event.new_status or current_status
                last_change_time = event.created_at
            
            elif event.event_type == "error":
                error_count += 1
        
        # Calculate final period
        if current_status in ["failed", "offline", "maintenance"]:
            downtime_minutes += (datetime.utcnow() - last_change_time).total_seconds() / 60
        
        uptime_percentage = max(0, (total_time - downtime_minutes) / total_time * 100)
        
        return {
            "period_days": days,
            "uptime_percentage": round(uptime_percentage, 2),
            "downtime_hours": round(downtime_minutes / 60, 2),
            "error_count": error_count,
            "status_changes": status_changes
        }
    
    def _create_status_event(self, db: Session, asset_id: int, event_type: str,
                          previous_status: Optional[str] = None, new_status: Optional[str] = None,
                          event_message: Optional[str] = None, event_severity: str = "info",
                          network_latency_ms: Optional[float] = None,
                          packet_loss_percentage: Optional[float] = None,
                          error_code: Optional[str] = None,
                          operator_id: Optional[str] = None,
                          event_data: Optional[str] = None) -> AssetStatusEvent:
        """Create and save asset status event."""
        
        event = AssetStatusEvent(
            asset_id=asset_id,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            event_message=event_message,
            event_severity=event_severity,
            network_latency_ms=network_latency_ms,
            packet_loss_percentage=packet_loss_percentage,
            error_code=error_code,
            operator_id=operator_id,
            event_data=event_data,
            automatic_detection=operator_id is None
        )
        
        db.add(event)
        db.flush()
        return event
    
    def _calculate_uptime_percentage(self, db: Session, asset_id: int) -> float:
        """Calculate uptime percentage for last 24 hours."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Get recent status changes
        events = db.query(AssetStatusEvent).filter(
            AssetStatusEvent.asset_id == asset_id,
            AssetStatusEvent.event_type == "status_change",
            AssetStatusEvent.created_at >= cutoff_time
        ).order_by(AssetStatusEvent.created_at).all()
        
        if not events:
            return 100.0  # Assume operational if no status changes
        
        # Calculate uptime based on status changes
        total_minutes = 24 * 60
        downtime_minutes = 0
        
        current_status = "operational"
        last_change_time = cutoff_time
        
        for event in events:
            if current_status in ["failed", "offline", "maintenance"]:
                downtime_minutes += (event.created_at - last_change_time).total_seconds() / 60
            
            current_status = event.new_status or current_status
            last_change_time = event.created_at
        
        # Calculate final period
        if current_status in ["failed", "offline", "maintenance"]:
            downtime_minutes += (datetime.utcnow() - last_change_time).total_seconds() / 60
        
        uptime_percentage = max(0, (total_minutes - downtime_minutes) / total_minutes * 100)
        return round(uptime_percentage, 2)
    
    def get_asset_summary(self, db: Session, asset_id: int) -> Dict:
        """Get comprehensive asset summary."""
        
        asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
        if not asset:
            return {}
        
        # Get recent events
        recent_events = self.get_asset_events(db, asset_id, hours_back=24)
        
        # Get uptime stats
        uptime_stats = self.get_asset_uptime_stats(db, asset_id, days=7)
        
        # Get maintenance history
        maintenance_records = db.query(AssetMaintenanceRecord).filter(
            AssetMaintenanceRecord.asset_id == asset_id
        ).order_by(AssetMaintenanceRecord.created_at.desc()).limit(5).all()
        
        return {
            "asset": {
                "id": asset.id,
                "name": asset.asset_name,
                "type": asset.asset_type,
                "location": asset.location,
                "terminal": asset.terminal,
                "gate": asset.gate,
                "status": asset.status,
                "health_score": asset.health_score,
                "network_health": asset.network_health,
                "last_heartbeat": asset.last_heartbeat.isoformat() if asset.last_heartbeat else None,
                "uptime_percentage": asset.uptime_percentage,
                "error_count_24h": asset.error_count_24h,
                "failure_probability_24h": asset.failure_probability_24h,
                "maintenance_priority": asset.maintenance_priority
            },
            "recent_events": [
                {
                    "type": event.event_type,
                    "message": event.event_message,
                    "severity": event.event_severity,
                    "created_at": event.created_at.isoformat()
                }
                for event in recent_events[:10]
            ],
            "uptime_stats": uptime_stats,
            "maintenance_history": [
                {
                    "type": record.maintenance_type,
                    "reason": record.maintenance_reason,
                    "scheduled_start": record.scheduled_start.isoformat(),
                    "downtime_minutes": record.downtime_minutes,
                    "created_at": record.created_at.isoformat()
                }
                for record in maintenance_records
            ]
        }


# Global instance
asset_monitoring = AssetMonitoringEngine()
