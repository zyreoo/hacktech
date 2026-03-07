"""
Infrastructure Monitoring API endpoints.

Comprehensive API for:
- Asset registry and monitoring
- Health prediction and scoring
- Network monitoring and heartbeat
- Incident detection and alerting
- Self-healing actions
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..services.asset_monitoring import asset_monitoring
from ..services.asset_health_prediction import asset_health_prediction
from ..services.network_monitoring import network_monitoring
from ..services.incident_detection import incident_detection
from ..services.self_healing import self_healing
from ..models import (
    InfrastructureAsset, AssetStatusEvent, AssetMaintenanceRecord,
    NetworkMonitoringSession, InfrastructureIncident, SelfHealingAction
)

router = APIRouter(prefix="/infrastructure-monitoring", tags=["infrastructure-monitoring"])


# Request models
class AssetRegistrationRequest(BaseModel):
    asset_type: str
    asset_name: str
    location: str
    terminal: Optional[str] = None
    gate: Optional[str] = None
    status: Optional[str] = "operational"
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    health_score: Optional[float] = 1.0
    network_health: Optional[float] = 1.0
    operator_id: Optional[str] = None


class AssetStatusUpdateRequest(BaseModel):
    status: Optional[str] = None
    health_score: Optional[float] = None
    network_health: Optional[float] = None
    network_latency_ms: Optional[float] = None
    packet_loss_percentage: Optional[float] = None
    error_count_24h: Optional[int] = None
    usage_cycles: Optional[int] = None
    total_usage_time: Optional[float] = None
    event_message: Optional[str] = None
    severity: Optional[str] = "info"
    operator_id: Optional[str] = None
    event_data: Optional[Dict] = None


class HeartbeatRequest(BaseModel):
    latency_ms: float
    packet_loss: float
    connected: bool
    available_services: List[str]
    degraded_services: List[str]


class IncidentResolutionRequest(BaseModel):
    description: str
    root_cause: Optional[str] = None
    preventive_actions: List[str]


class HealingActionRequest(BaseModel):
    incident_id: Optional[str] = None
    asset_id: int
    action_type: str
    action_name: str
    action_description: str
    triggered_by: str


# Asset Registry and Monitoring
@router.post("/assets/register")
def register_asset(request: AssetRegistrationRequest, db: Session = Depends(get_db)):
    """Register a new infrastructure asset."""
    try:
        asset = asset_monitoring.register_asset(db, request.model_dump())
        return {"asset_id": asset.id, "message": "Asset registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assets")
def get_asset_registry(
    asset_type: Optional[str] = None,
    terminal: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get filtered asset registry."""
    assets = asset_monitoring.get_asset_registry(db, asset_type, terminal, status)
    return {"assets": assets, "total": len(assets)}


@router.get("/assets/{asset_id}")
def get_asset_details(asset_id: int, db: Session = Depends(get_db)):
    """Get comprehensive asset details and summary."""
    try:
        summary = asset_monitoring.get_asset_summary(db, asset_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/assets/{asset_id}/status")
def update_asset_status(asset_id: int, request: AssetStatusUpdateRequest, db: Session = Depends(get_db)):
    """Update asset status and create event log."""
    try:
        event = asset_monitoring.update_asset_status(db, asset_id, request.model_dump())
        return {"event_id": event.id, "message": "Asset status updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assets/{asset_id}/heartbeat")
def record_heartbeat(asset_id: int, request: HeartbeatRequest, db: Session = Depends(get_db)):
    """Record asset heartbeat and update metrics."""
    try:
        event = asset_monitoring.record_heartbeat(db, asset_id, request.model_dump())
        return {"event_id": event.id, "message": "Heartbeat recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assets/{asset_id}/events")
def get_asset_events(
    asset_id: int,
    event_type: Optional[str] = None,
    hours_back: int = 24,
    db: Session = Depends(get_db)
):
    """Get recent events for an asset."""
    events = asset_monitoring.get_asset_events(db, asset_id, event_type, hours_back)
    return {"events": events, "total": len(events)}


@router.get("/assets/health/critical")
def get_critical_assets(db: Session = Depends(get_db)):
    """Get assets in critical state or with low health scores."""
    assets = asset_monitoring.get_critical_assets(db)
    return {"critical_assets": assets, "total": len(assets)}


@router.get("/assets/health/scores")
def get_assets_by_health(
    min_health: float = 0.0,
    max_health: float = 1.0,
    db: Session = Depends(get_db)
):
    """Get assets within health score range."""
    assets = asset_monitoring.get_assets_by_health_score(db, min_health, max_health)
    return {"assets": assets, "total": len(assets)}


@router.get("/assets/{asset_id}/uptime")
def get_asset_uptime_stats(asset_id: int, days: int = 30, db: Session = Depends(get_db)):
    """Calculate uptime statistics for an asset."""
    try:
        stats = asset_monitoring.get_asset_uptime_stats(db, asset_id, days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Health Prediction and Scoring
@router.post("/assets/{asset_id}/health/predict")
def calculate_asset_health_score(asset_id: int, db: Session = Depends(get_db)):
    """Calculate comprehensive health score for an asset."""
    try:
        health_data = asset_health_prediction.calculate_asset_health_score(db, asset_id)
        return health_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assets/{asset_id}/failure-predict")
def predict_failure_probability(
    asset_id: int,
    prediction_hours: int = 24,
    db: Session = Depends(get_db)
):
    """Predict failure probability for specified time window."""
    try:
        prediction = asset_health_prediction.predict_failure_probability(db, asset_id, prediction_hours)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assets/maintenance-alerts")
def generate_predictive_maintenance_alerts(db: Session = Depends(get_db)):
    """Generate maintenance alerts for assets at risk."""
    try:
        alerts = asset_health_prediction.generate_predictive_maintenance_alerts(db)
        return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/maintenance-needed")
def get_assets_needing_maintenance(
    priority_threshold: str = "high",
    db: Session = Depends(get_db)
):
    """Get assets that need maintenance based on predictions."""
    try:
        assets = asset_health_prediction.get_assets_needing_maintenance(db, priority_threshold)
        return {"assets": assets, "total": len(assets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Network Monitoring and Heartbeat
@router.post("/assets/{asset_id}/network/start-monitoring")
def start_network_monitoring_session(asset_id: int, db: Session = Depends(get_db)):
    """Start a new monitoring session for an asset."""
    try:
        session = network_monitoring.start_monitoring_session(db, asset_id)
        return {"session_id": session.id, "message": "Network monitoring started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/assets/{asset_id}/network/heartbeat")
def record_network_heartbeat(asset_id: int, request: HeartbeatRequest, db: Session = Depends(get_db)):
    """Record network heartbeat data and update monitoring session."""
    try:
        session = network_monitoring.record_heartbeat(db, asset_id, request.model_dump())
        return {"session_id": session.id, "message": "Network heartbeat recorded"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assets/{asset_id}/network/health-check")
def check_network_health(asset_id: int, db: Session = Depends(get_db)):
    """Perform comprehensive network health check."""
    try:
        health_data = network_monitoring.check_network_health(db, asset_id)
        return health_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/network/anomalies")
def get_network_anomalies(hours_back: int = 24, db: Session = Depends(get_db)):
    """Detect network anomalies from monitoring data."""
    try:
        anomalies = network_monitoring.get_network_anomalies(db, hours_back)
        return {"anomalies": anomalies, "total": len(anomalies)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network/connectivity-summary")
def get_connectivity_summary(terminal: Optional[str] = None, db: Session = Depends(get_db)):
    """Get connectivity summary for assets."""
    try:
        summary = network_monitoring.get_connectivity_summary(db, terminal)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Incident Detection and Alerting
@router.post("/incidents/detect")
def detect_incidents(db: Session = Depends(get_db)):
    """Run comprehensive incident detection across all assets."""
    try:
        incidents = incident_detection.detect_incidents(db)
        return {"incidents_detected": len(incidents), "incidents": incidents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/active")
def get_active_incidents(
    severity: Optional[str] = None,
    incident_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get currently active incidents."""
    try:
        incidents = incident_detection.get_active_incidents(db, severity, incident_type)
        return {"incidents": incidents, "total": len(incidents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/summary")
def get_incident_summary(hours_back: int = 24, db: Session = Depends(get_db)):
    """Get summary of recent incidents."""
    try:
        summary = incident_detection.get_incident_summary(db, hours_back)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, request: IncidentResolutionRequest, db: Session = Depends(get_db)):
    """Resolve an incident with resolution details."""
    try:
        incident = incident_detection.resolve_incident(db, incident_id, request.model_dump())
        return {"incident_id": incident.incident_id, "message": "Incident resolved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Self-Healing Actions
@router.post("/incidents/{incident_id}/analyze-healing")
def analyze_incident_for_healing(incident_id: str, db: Session = Depends(get_db)):
    """Analyze incident and recommend self-healing actions."""
    try:
        actions = self_healing.analyze_incident_for_healing(db, incident_id)
        return {"healing_actions": actions, "total": len(actions)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/healing/actions/execute")
def execute_healing_action(request: HealingActionRequest, db: Session = Depends(get_db)):
    """Execute a self-healing action."""
    try:
        action = self_healing.execute_healing_action(db, request.model_dump())
        return {
            "action_id": action.id,
            "success": action.successful,
            "message": "Healing action executed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assets/maintenance-windows/optimize")
def optimize_maintenance_windows(
    asset_ids: List[int] = Body(...),
    db: Session = Depends(get_db)
):
    """Optimize maintenance windows based on flight schedules and asset criticality."""
    try:
        windows = self_healing.optimize_maintenance_windows(db, asset_ids)
        return {"maintenance_windows": windows, "total": len(windows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assets/{failed_asset_id}/reroute")
def recommend_asset_rerouting(
    failed_asset_id: int,
    service_requirements: Dict = Body(...),
    db: Session = Depends(get_db)
):
    """Recommend asset rerouting when device fails."""
    try:
        recommendations = self_healing.recommend_asset_rerouting(db, failed_asset_id, service_requirements)
        return {"rerouting_recommendations": recommendations, "total": len(recommendations)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/operations/notify")
def notify_operations_dashboard(notification_data: Dict, db: Session = Depends(get_db)):
    """Create notifications for operations dashboard."""
    try:
        alert = self_healing.notify_operations_dashboard(db, notification_data)
        return {"alert_id": alert.id, "message": "Operations notification created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/healing/actions/history")
def get_healing_action_history(
    asset_id: Optional[int] = None,
    hours_back: int = 24,
    db: Session = Depends(get_db)
):
    """Get history of self-healing actions."""
    try:
        actions = self_healing.get_healing_action_history(db, asset_id, hours_back)
        return {"actions": actions, "total": len(actions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/healing/effectiveness")
def get_healing_effectiveness(days_back: int = 30, db: Session = Depends(get_db)):
    """Calculate effectiveness of self-healing actions."""
    try:
        effectiveness = self_healing.get_healing_effectiveness(db, days_back)
        return effectiveness
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Maintenance Records
@router.get("/assets/{asset_id}/maintenance")
def get_asset_maintenance_history(asset_id: int, db: Session = Depends(get_db)):
    """Get maintenance history for an asset."""
    try:
        records = db.query(AssetMaintenanceRecord).filter(
            AssetMaintenanceRecord.asset_id == asset_id
        ).order_by(AssetMaintenanceRecord.created_at.desc()).limit(20).all()
        return {"maintenance_records": records, "total": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assets/{asset_id}/maintenance")
def create_maintenance_record(asset_id: int, maintenance_data: Dict, db: Session = Depends(get_db)):
    """Create a maintenance record for an asset."""
    try:
        record = AssetMaintenanceRecord(
            asset_id=asset_id,
            maintenance_type=maintenance_data.get("maintenance_type", "corrective"),
            maintenance_reason=maintenance_data.get("maintenance_reason"),
            maintenance_description=maintenance_data.get("maintenance_description"),
            scheduled_start=datetime.fromisoformat(maintenance_data.get("scheduled_start", datetime.utcnow().isoformat())),
            scheduled_end=datetime.fromisoformat(maintenance_data.get("scheduled_end", datetime.utcnow().isoformat())),
            affected_operations=json.dumps(maintenance_data.get("affected_operations", [])),
            passenger_impact=maintenance_data.get("passenger_impact", "low"),
            technician_id=maintenance_data.get("technician_id"),
            maintenance_cost=maintenance_data.get("maintenance_cost")
        )
        db.add(record)
        return {"record_id": record.id, "message": "Maintenance record created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Network Monitoring Sessions
@router.get("/assets/{asset_id}/network/sessions")
def get_network_monitoring_sessions(asset_id: int, db: Session = Depends(get_db)):
    """Get network monitoring sessions for an asset."""
    try:
        sessions = db.query(NetworkMonitoringSession).filter(
            NetworkMonitoringSession.asset_id == asset_id
        ).order_by(NetworkMonitoringSession.session_start.desc()).limit(10).all()
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/assets/{asset_id}/network/end-session")
def end_network_monitoring_session(asset_id: int, end_reason: Optional[str] = None, db: Session = Depends(get_db)):
    """End monitoring session for an asset."""
    try:
        session = network_monitoring.end_monitoring_session(db, asset_id, end_reason)
        return {"session_id": session.id, "duration_minutes": session.session_duration_minutes}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
