"""
Enhanced Passenger Flow API endpoints.

Comprehensive API for:
- Queue data ingestion from multiple sources
- Real-time queue state tracking
- Queue prediction and forecasting
- Smart lane management
- Passenger wave detection
- Flow visualization and dashboard
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..services.queue_data_ingestion import queue_data_ingestion
from ..services.queue_state_engine import queue_state_engine
from ..services.queue_prediction import queue_prediction
from ..services.smart_lane_management import smart_lane_management
from ..services.passenger_wave_detection import passenger_wave_detection
from ..services.flow_visualization import flow_visualization

router = APIRouter(prefix="/passenger-flow", tags=["passenger-flow"])


# Legacy endpoint for backward compatibility
@router.get("")
def list_passenger_flow_legacy(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    """Legacy passenger flow endpoint - redirects to comprehensive dashboard."""
    try:
        # Return comprehensive dashboard data for backward compatibility
        dashboard = flow_visualization.get_realtime_dashboard(db)
        return {
            "passenger_flows": [],
            "dashboard": dashboard,
            "message": "Enhanced passenger flow system active. Use /passenger-flow/dashboard/comprehensive for full features.",
            "available_endpoints": {
                "states": "/passenger-flow/states",
                "dashboard": "/passenger-flow/dashboard/comprehensive", 
                "ingestion": "/passenger-flow/ingestion",
                "predictions": "/passenger-flow/predictions",
                "lanes": "/passenger-flow/lanes",
                "waves": "/passenger-flow/waves",
                "visualization": "/passenger-flow/visualization"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Request models
class CameraDataRequest(BaseModel):
    sensor_id: str
    checkpoint_type: str
    terminal: str
    gate: Optional[str] = None
    passenger_count: int
    queue_length_meters: float
    flow_rate_ppm: float
    dwell_time_seconds: Optional[float] = None
    lane_id: Optional[str] = None
    confidence: Optional[float] = None
    lighting_level: Optional[str] = "good"
    camera_angle: Optional[float] = 0
    camera_height: Optional[float] = 3.0
    sensor_timestamp: datetime


class ManualDataRequest(BaseModel):
    sensor_id: str
    checkpoint_type: str
    terminal: str
    gate: Optional[str] = None
    passenger_count: int
    queue_length_meters: float
    flow_rate_ppm: float
    dwell_time_seconds: Optional[float] = None
    lane_id: Optional[str] = None
    staff_notes: Optional[str] = None
    reporting_delay: Optional[int] = 0
    sensor_timestamp: datetime


class SensorDataRequest(BaseModel):
    sensor_id: str
    sensor_type: str
    checkpoint_type: str
    terminal: str
    gate: Optional[str] = None
    passenger_count: int
    queue_length_meters: float
    flow_rate_ppm: float
    dwell_time_seconds: Optional[float] = None
    lane_id: Optional[str] = None
    ambient_temperature: Optional[float] = 20.0
    average_passenger_weight: Optional[float] = 70.0
    luggage_present: Optional[bool] = False
    sensor_timestamp: datetime


class LaneRecommendationRequest(BaseModel):
    checkpoint_id: str
    recommendation_type: str
    priority: str = "medium"
    implemented_by: Optional[str] = None


class LaneStatusUpdateRequest(BaseModel):
    checkpoint_id: str
    lane_updates: Dict[str, Dict]


# Queue Data Ingestion Endpoints
@router.post("/ingestion/camera")
def ingest_camera_data(request: CameraDataRequest, db: Session = Depends(get_db)):
    """Ingest camera-based queue monitoring data."""
    try:
        sensor_data = queue_data_ingestion.ingest_camera_data(db, request.model_dump())
        return {
            "sensor_data_id": sensor_data.id,
            "message": "Camera data ingested successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingestion/manual")
def ingest_manual_data(request: ManualDataRequest, db: Session = Depends(get_db)):
    """Ingest manual staff input data."""
    try:
        sensor_data = queue_data_ingestion.ingest_manual_data(db, request.model_dump())
        return {
            "sensor_data_id": sensor_data.id,
            "message": "Manual data ingested successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingestion/sensor")
def ingest_sensor_data(request: SensorDataRequest, db: Session = Depends(get_db)):
    """Ingest sensor data from infrared, weight sensors, etc."""
    try:
        sensor_data = queue_data_ingestion.ingest_sensor_data(db, request.model_dump())
        return {
            "sensor_data_id": sensor_data.id,
            "message": "Sensor data ingested successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingestion/batch")
def batch_ingest_data(data_batch: List[Dict], db: Session = Depends(get_db)):
    """Batch ingest multiple sensor data records."""
    try:
        sensor_records = queue_data_ingestion.batch_ingest_data(db, data_batch)
        return {
            "ingested_count": len(sensor_records),
            "message": "Batch data ingested successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Queue State Engine Endpoints
@router.get("/states")
def get_all_queue_states(
    terminal: Optional[str] = Query(None),
    checkpoint_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all current queue states."""
    try:
        states = queue_state_engine.get_all_states(db, terminal, checkpoint_type)
        return {
            "states": states,
            "total": len(states),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/states/{checkpoint_id}")
def get_queue_state(checkpoint_id: str, db: Session = Depends(get_db)):
    """Get current state for a specific checkpoint."""
    try:
        state = queue_state_engine.get_current_state(db, checkpoint_id)
        if not state:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        return {
            "state": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/states/critical")
def get_critical_queues(db: Session = Depends(get_db)):
    """Get queues in critical state."""
    try:
        critical_queues = queue_state_engine.get_critical_queues(db)
        return {
            "critical_queues": critical_queues,
            "total": len(critical_queues),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/states/{checkpoint_id}/metrics")
def get_queue_metrics(
    checkpoint_id: str,
    hours_back: int = Query(24),
    db: Session = Depends(get_db)
):
    """Get comprehensive metrics for a checkpoint."""
    try:
        metrics = queue_state_engine.get_queue_metrics(db, checkpoint_id, hours_back)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/states/{checkpoint_id}/lanes")
def update_lane_status(
    checkpoint_id: str,
    request: LaneStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update lane status for a checkpoint."""
    try:
        state = queue_state_engine.update_lane_status(db, checkpoint_id, request.lane_updates)
        return {
            "checkpoint_id": checkpoint_id,
            "updated_state": state,
            "message": "Lane status updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/states/{checkpoint_id}/efficiency")
def get_lane_efficiency_metrics(checkpoint_id: str, db: Session = Depends(get_db)):
    """Get lane efficiency metrics for a checkpoint."""
    try:
        metrics = queue_state_engine.get_lane_efficiency_metrics(db, checkpoint_id)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Queue Prediction Endpoints
@router.post("/states/{checkpoint_id}/predict")
def predict_queue_state(
    checkpoint_id: str,
    horizons: List[int] = Body([10, 20, 30]),
    db: Session = Depends(get_db)
):
    """Generate queue predictions for specified time horizons."""
    try:
        predictions = queue_prediction.predict_queue_state(db, checkpoint_id, horizons)
        return {
            "checkpoint_id": checkpoint_id,
            "predictions": predictions,
            "total": len(predictions),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/states/{checkpoint_id}/predictions")
def get_prediction_accuracy(
    checkpoint_id: str,
    hours_back: int = Query(24),
    db: Session = Depends(get_db)
):
    """Get prediction accuracy metrics."""
    try:
        accuracy = queue_prediction.get_prediction_accuracy(db, checkpoint_id, hours_back)
        return accuracy
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/states/{checkpoint_id}/predictions/accuracy")
def update_prediction_accuracy(
    checkpoint_id: str,
    actual_queue_length: int,
    actual_wait_time: int,
    db: Session = Depends(get_db)
):
    """Update predictions with actual values for accuracy tracking."""
    try:
        queue_prediction.update_prediction_accuracy(db, checkpoint_id, actual_queue_length, actual_wait_time)
        return {
            "checkpoint_id": checkpoint_id,
            "message": "Prediction accuracy updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/predictions/congestion-windows")
def predict_congestion_windows(
    terminal: Optional[str] = Query(None),
    hours_ahead: int = Query(4),
    db: Session = Depends(get_db)
):
    """Predict future congestion windows."""
    try:
        windows = queue_prediction.predict_congestion_windows(db, terminal, hours_ahead)
        return {
            "terminal": terminal,
            "hours_ahead": hours_ahead,
            "congestion_windows": windows,
            "total": len(windows),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Smart Lane Management Endpoints
@router.post("/lanes/analyze")
def analyze_lane_requirements(
    checkpoint_id: str,
    db: Session = Depends(get_db)
):
    """Analyze current lane requirements and generate recommendations."""
    try:
        analysis = smart_lane_management.analyze_lane_requirements(db, checkpoint_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lanes/recommendations")
def generate_lane_recommendation(request: LaneRecommendationRequest, db: Session = Depends(get_db)):
    """Generate specific lane recommendation."""
    try:
        recommendation = smart_lane_management.generate_lane_recommendation(
            db, request.checkpoint_id, request.recommendation_type, request.priority
        )
        return {
            "recommendation": recommendation,
            "message": "Lane recommendation generated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/lanes/recommendations/{recommendation_id}/implement")
def implement_lane_recommendation(
    recommendation_id: str,
    implemented_by: str = Body(...),
    db: Session = Depends(get_db)
):
    """Mark a lane recommendation as implemented."""
    try:
        recommendation = smart_lane_management.implement_lane_recommendation(db, recommendation_id, implemented_by)
        return {
            "recommendation_id": recommendation_id,
            "message": "Recommendation implemented successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lanes/recommendations/{recommendation_id}/effectiveness")
def evaluate_recommendation_effectiveness(recommendation_id: str, db: Session = Depends(get_db)):
    """Evaluate the effectiveness of an implemented recommendation."""
    try:
        effectiveness = smart_lane_management.evaluate_recommendation_effectiveness(db, recommendation_id)
        return effectiveness
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lanes/utilization-report")
def get_lane_utilization_report(
    terminal: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Generate comprehensive lane utilization report."""
    try:
        report = smart_lane_management.get_lane_utilization_report(db, terminal)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Passenger Wave Detection Endpoints
@router.get("/waves/detect")
def detect_passenger_waves(
    terminal: Optional[str] = Query(None),
    hours_ahead: int = Query(4),
    hours_back: int = Query(2),
    db: Session = Depends(get_db)
):
    """Detect passenger waves based on flight schedules."""
    try:
        waves = passenger_wave_detection.detect_passenger_waves(db, terminal, hours_ahead, hours_back)
        return {
            "terminal": terminal,
            "hours_ahead": hours_ahead,
            "hours_back": hours_back,
            "waves": waves,
            "total": len(waves),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/waves/predict-congestion")
def predict_congestion_from_waves(
    terminal: Optional[str] = Query(None),
    hours_ahead: int = Query(6),
    db: Session = Depends(get_db)
):
    """Predict future congestion windows based on wave patterns."""
    try:
        windows = passenger_wave_detection.predict_congestion_windows(db, terminal, hours_ahead)
        return {
            "terminal": terminal,
            "hours_ahead": hours_ahead,
            "congestion_windows": windows,
            "total": len(windows),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/waves/active")
def get_active_waves(terminal: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get currently active passenger waves."""
    try:
        waves = passenger_wave_detection.get_active_waves(db, terminal)
        return {
            "terminal": terminal,
            "active_waves": waves,
            "total": len(waves),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/waves/{wave_id}/update")
def update_wave_status(
    wave_id: str,
    current_flow_rate: float = Body(...),
    current_queue_lengths: Dict[str, int] = Body(...),
    db: Session = Depends(get_db)
):
    """Update wave status with current metrics."""
    try:
        wave = passenger_wave_detection.update_wave_status(db, wave_id, current_flow_rate, current_queue_lengths)
        return {
            "wave_id": wave_id,
            "updated_wave": wave,
            "message": "Wave status updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/waves/analyze-patterns")
def analyze_wave_patterns(days_back: int = Query(30), db: Session = Depends(get_db)):
    """Analyze historical wave patterns."""
    try:
        patterns = passenger_wave_detection.analyze_wave_patterns(db, days_back)
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/waves/impact-summary")
def get_wave_impact_summary(hours_back: int = Query(24), db: Session = Depends(get_db)):
    """Get summary of wave impacts for recent period."""
    try:
        summary = passenger_wave_detection.get_wave_impact_summary(db, hours_back)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Flow Visualization Endpoints
@router.post("/visualization/heatmap")
def generate_terminal_heatmap(
    terminal: str = Body(...),
    floor_level: str = Body("ground"),
    db: Session = Depends(get_db)
):
    """Generate terminal congestion heatmap."""
    try:
        heatmap = flow_visualization.generate_terminal_heatmap(db, terminal, floor_level)
        return {
            "heatmap": heatmap,
            "message": "Heatmap generated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/visualization/dashboard")
def get_realtime_dashboard(
    terminal: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Generate real-time dashboard data."""
    try:
        dashboard = flow_visualization.get_realtime_dashboard(db, terminal)
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visualization/flow-trends")
def get_flow_trends(
    terminal: Optional[str] = Query(None),
    hours_back: int = Query(4),
    db: Session = Depends(get_db)
):
    """Analyze flow trends over time."""
    try:
        trends = flow_visualization.get_flow_trends(db, terminal, hours_back)
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visualization/congestion-analysis")
def get_congestion_analysis(
    terminal: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Analyze current congestion patterns."""
    try:
        analysis = flow_visualization.get_congestion_analysis(db, terminal)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Comprehensive Dashboard Endpoint
@router.get("/dashboard/comprehensive")
def get_comprehensive_dashboard(
    terminal: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard with all passenger flow data."""
    try:
        # Get all data components
        dashboard_data = flow_visualization.get_realtime_dashboard(db, terminal)
        
        # Add predictions
        if dashboard_data.get("checkpoint_details"):
            for checkpoint in dashboard_data["checkpoint_details"]:
                predictions = queue_prediction.predict_queue_state(db, checkpoint["checkpoint_id"], [10, 20, 30])
                checkpoint["predictions"] = predictions
        
        # Add wave analysis
        waves = passenger_wave_detection.get_active_waves(db, terminal)
        dashboard_data["active_waves"] = waves
        
        # Add lane recommendations
        if dashboard_data.get("checkpoint_details"):
            for checkpoint in dashboard_data["checkpoint_details"]:
                analysis = smart_lane_management.analyze_lane_requirements(db, checkpoint["checkpoint_id"])
                checkpoint["lane_recommendations"] = analysis.get("recommendations", [])
        
        return {
            "dashboard": dashboard_data,
            "timestamp": datetime.utcnow().isoformat(),
            "data_sources": [
                "queue_states",
                "predictions", 
                "wave_detection",
                "lane_management",
                "congestion_analysis"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health and Status Endpoints
@router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    """Get overall passenger flow system health status."""
    try:
        # Get basic metrics
        states = queue_state_engine.get_all_states(db)
        critical_queues = queue_state_engine.get_critical_queues(db)
        active_waves = passenger_wave_detection.get_active_waves(db)
        
        total_checkpoints = len(states)
        operational_checkpoints = len([s for s in states if s.current_queue_length >= 0])
        
        health_score = 1.0
        if total_checkpoints > 0:
            health_score = operational_checkpoints / total_checkpoints
        
        return {
            "system_health": "healthy" if health_score > 0.8 else "degraded" if health_score > 0.6 else "critical",
            "health_score": round(health_score, 3),
            "total_checkpoints": total_checkpoints,
            "operational_checkpoints": operational_checkpoints,
            "critical_queues": len(critical_queues),
            "active_waves": len(active_waves),
            "data_freshness": _calculate_data_freshness(states),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_data_freshness(states) -> str:
    """Calculate data freshness based on last update times."""
    if not states:
        return "no_data"
    
    now = datetime.utcnow()
    recent_updates = [s.last_updated for s in states if s.last_updated]
    
    if not recent_updates:
        return "stale"
    
    # Calculate average age of data
    avg_age_minutes = sum((now - update).total_seconds() / 60 for update in recent_updates) / len(recent_updates)
    
    if avg_age_minutes < 5:
        return "fresh"
    elif avg_age_minutes < 15:
        return "current"
    elif avg_age_minutes < 60:
        return "stale"
    else:
        return "very_stale"
