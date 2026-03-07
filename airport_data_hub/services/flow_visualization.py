"""
Flow Visualization and Dashboard Service.

Advanced terminal flow visualization:
- Terminal heatmap generation
- Color-coded congestion mapping
- Real-time queue dashboard
- Flow direction analysis
"""

import json
import uuid
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    TerminalHeatmap, QueueState, QueueEvent, PassengerWave, Flight
)
from ..database import SessionLocal


class FlowVisualizationEngine:
    """Advanced flow visualization and dashboard system."""
    
    def __init__(self):
        self.heatmap_config = {
            "grid_resolution": 5,  # 5 meters per cell
            "terminal_dimensions": {
                "T1": {"width": 200, "height": 150},  # meters
                "T2": {"width": 180, "height": 120},
                "T3": {"width": 220, "height": 160}
            },
            "congestion_colors": {
                "low": "#00FF00",      # Green
                "medium": "#FFFF00",   # Yellow
                "high": "#FFA500",     # Orange
                "critical": "#FF0000"  # Red
            },
            "congestion_thresholds": {
                "low": 0.2,      # < 20% capacity
                "medium": 0.4,    # < 40% capacity
                "high": 0.7,      # < 70% capacity
                "critical": 0.9     # < 90% capacity
            }
        }
        
        self.dashboard_config = {
            "refresh_interval_seconds": 30,
            "historical_hours": 4,
            "prediction_horizons": [10, 20, 30],
            "alert_thresholds": {
                "queue_length": {"warning": 20, "critical": 35},
                "wait_time": {"warning": 10, "critical": 20},
                "utilization": {"warning": 0.7, "critical": 0.85}
            }
        }
    
    def generate_terminal_heatmap(self, db: Session, terminal: str, 
                            floor_level: str = "ground") -> TerminalHeatmap:
        """Generate terminal congestion heatmap."""
        
        # Get terminal dimensions
        dimensions = self.heatmap_config["terminal_dimensions"].get(terminal, {"width": 200, "height": 150})
        
        # Calculate grid dimensions
        grid_width = dimensions["width"] // self.heatmap_config["grid_resolution"]
        grid_height = dimensions["height"] // self.heatmap_config["grid_resolution"]
        
        # Get queue states for this terminal
        queue_states = db.query(QueueState).filter(
            QueueState.terminal == terminal
        ).all()
        
        # Initialize density grid
        density_grid = [[0.0 for _ in range(grid_width)] for _ in range(grid_height)]
        
        # Map queue states to grid positions
        for state in queue_states:
            x, y = self._map_checkpoint_to_grid(state, dimensions, grid_width, grid_height)
            if 0 <= x < grid_width and 0 <= y < grid_height:
                # Calculate density for this cell
                density = self._calculate_cell_density(state, dimensions)
                density_grid[y][x] = max(density_grid[y][x], density)
        
        # Apply smoothing (simple average with neighbors)
        smoothed_grid = self._smooth_heatmap(density_grid)
        
        # Identify congestion zones
        congestion_zones = self._identify_congestion_zones(smoothed_grid)
        
        # Calculate flow directions (simplified)
        flow_directions = self._calculate_flow_directions(queue_states, dimensions)
        
        # Generate heatmap ID
        heatmap_id = f"HM-{terminal}-{floor_level}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        return TerminalHeatmap(
            heatmap_id=heatmap_id,
            terminal=terminal,
            floor_level=floor_level,
            grid_resolution=self.heatmap_config["grid_resolution"],
            grid_width=grid_width,
            grid_height=grid_height,
            density_data=json.dumps(smoothed_grid),
            congestion_zones=json.dumps(congestion_zones),
            flow_directions=json.dumps(flow_directions),
            congestion_levels=json.dumps(self.heatmap_config["congestion_colors"]),
            peak_density=max(max(row) for row in smoothed_grid),
            average_density=sum(sum(row) for row in smoothed_grid) / (grid_width * grid_height),
            total_passengers=sum(state.current_queue_length for state in queue_states),
            timestamp=datetime.utcnow(),
            contributing_flights=json.dumps(self._get_contributing_flights(db, terminal)),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
    
    def get_realtime_dashboard(self, db: Session, terminal: Optional[str] = None) -> Dict:
        """Generate real-time dashboard data."""
        
        # Get current queue states
        query = db.query(QueueState)
        if terminal:
            query = query.filter(QueueState.terminal == terminal)
        
        states = query.all()
        
        # Calculate dashboard metrics
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "terminal": terminal or "all",
            "summary": {
                "total_checkpoints": len(states),
                "active_checkpoints": len([s for s in states if s.current_queue_length > 0]),
                "total_passengers": sum(s.current_queue_length for s in states),
                "average_wait_time": sum(s.current_wait_time for s in states) / max(len(states), 1),
                "critical_queues": len([s for s in states if s.current_wait_time > self.dashboard_config["alert_thresholds"]["wait_time"]["critical"]])
            },
            "checkpoint_details": [],
            "alerts": [],
            "predictions": []
        }
        
        # Process each checkpoint
        for state in states:
            checkpoint_data = self._process_checkpoint_for_dashboard(state)
            dashboard_data["checkpoint_details"].append(checkpoint_data)
            
            # Check for alerts
            alerts = self._generate_checkpoint_alerts(state)
            dashboard_data["alerts"].extend(alerts)
        
        # Get predictions
        for state in states:
            predictions = self._get_checkpoint_predictions(db, state)
            dashboard_data["predictions"].extend(predictions)
        
        return dashboard_data
    
    def get_flow_trends(self, db: Session, terminal: Optional[str] = None, 
                       hours_back: int = 4) -> Dict:
        """Analyze flow trends over time."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Get historical queue events
        query = db.query(QueueEvent).filter(
            QueueEvent.event_timestamp >= cutoff_time
        )
        
        if terminal:
            query = query.filter(QueueEvent.terminal == terminal)
        
        events = query.order_by(QueueEvent.event_timestamp.desc()).all()
        
        if not events:
            return {"error": "No data available for trend analysis"}
        
        # Group events by time intervals
        interval_minutes = 30  # 30-minute intervals
        trend_data = self._group_events_by_interval(events, interval_minutes)
        
        # Calculate trends
        trends = {
            "queue_length_trend": self._calculate_trend([d["avg_queue_length"] for d in trend_data]),
            "wait_time_trend": self._calculate_trend([d["avg_wait_time"] for d in trend_data]),
            "utilization_trend": self._calculate_trend([d["avg_utilization"] for d in trend_data]),
            "peak_periods": self._identify_peak_periods(trend_data),
            "flow_patterns": self._analyze_flow_patterns(trend_data)
        }
        
        return {
            "terminal": terminal or "all",
            "period_hours": hours_back,
            "interval_minutes": interval_minutes,
            "data_points": len(trend_data),
            "trends": trends,
            "time_series": trend_data
        }
    
    def get_congestion_analysis(self, db: Session, terminal: Optional[str] = None) -> Dict:
        """Analyze current congestion patterns."""
        
        # Get current states
        query = db.query(QueueState)
        if terminal:
            query = query.filter(QueueState.terminal == terminal)
        
        states = query.all()
        
        if not states:
            return {"error": "No queue data available"}
        
        # Congestion analysis
        congestion_analysis = {
            "overall_congestion": self._calculate_overall_congestion(states),
            "congestion_by_checkpoint": [],
            "congestion_by_type": {},
            "bottlenecks": [],
            "recommendations": []
        }
        
        # Analyze each checkpoint
        for state in states:
            checkpoint_congestion = self._analyze_checkpoint_congestion(state)
            congestion_analysis["congestion_by_checkpoint"].append(checkpoint_congestion)
            
            # Group by checkpoint type
            checkpoint_type = state.checkpoint_type
            if checkpoint_type not in congestion_analysis["congestion_by_type"]:
                congestion_analysis["congestion_by_type"][checkpoint_type] = {
                    "count": 0,
                    "total_queue": 0,
                    "average_wait": 0,
                    "critical_count": 0
                }
            
            congestion_analysis["congestion_by_type"][checkpoint_type]["count"] += 1
            congestion_analysis["congestion_by_type"][checkpoint_type]["total_queue"] += state.current_queue_length
            congestion_analysis["congestion_by_type"][checkpoint_type]["average_wait"] += state.current_wait_time
            if checkpoint_congestion["level"] == "critical":
                congestion_analysis["congestion_by_type"][checkpoint_type]["critical_count"] += 1
        
        # Identify bottlenecks
        congestion_analysis["bottlenecks"] = self._identify_bottlenecks(congestion_analysis["congestion_by_checkpoint"])
        
        # Generate recommendations
        congestion_analysis["recommendations"] = self._generate_congestion_recommendations(congestion_analysis)
        
        return congestion_analysis
    
    def _map_checkpoint_to_grid(self, state: QueueState, dimensions: Dict, 
                               grid_width: int, grid_height: int) -> Tuple[int, int]:
        """Map checkpoint location to grid coordinates."""
        
        # Simplified mapping based on checkpoint ID and terminal layout
        # In production, this would use actual terminal layout data
        
        checkpoint_mappings = {
            # Terminal T1 mappings (simplified)
            "T1": {
                "security_1": (10, 20),   "security_2": (30, 20),
                "checkin_1": (15, 40),  "checkin_2": (25, 40),
                "boarding_1": (5, 10),   "boarding_2": (15, 10),
                "immigration_1": (35, 30), "immigration_2": (45, 30)
            },
            # Terminal T2 mappings
            "T2": {
                "security_1": (8, 15),    "security_2": (25, 15),
                "checkin_1": (12, 35),  "checkin_2": (20, 35),
                "boarding_1": (4, 8),    "boarding_2": (12, 8),
                "immigration_1": (28, 25), "immigration_2": (38, 25)
            }
        }
        
        terminal_mappings = checkpoint_mappings.get(state.terminal, checkpoint_mappings["T1"])
        checkpoint_key = f"{state.checkpoint_type}_{state.active_lanes}"  # Simplified
        
        return terminal_mappings.get(checkpoint_key, (grid_width // 2, grid_height // 2))
    
    def _calculate_cell_density(self, state: QueueState, dimensions: Dict) -> float:
        """Calculate passenger density for a grid cell."""
        
        # Simplified density calculation based on queue length and checkpoint capacity
        checkpoint_capacity = {
            "security": 50, "checkin": 30, "boarding": 100, "immigration": 40
        }.get(state.checkpoint_type, 50)
        
        # Density as percentage of capacity
        density = state.current_capacity_utilization
        
        # Adjust for checkpoint size (larger checkpoints affect larger area)
        size_factor = {
            "security": 1.2, "checkin": 0.8, "boarding": 1.5, "immigration": 1.0
        }.get(state.checkpoint_type, 1.0)
        
        return density * size_factor
    
    def _smooth_heatmap(self, grid: List[List[float]]) -> List[List[float]]:
        """Apply smoothing to heatmap grid."""
        
        if not grid:
            return grid
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        # Simple Gaussian smoothing
        smoothed_grid = [[0.0 for _ in range(width)] for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                # Calculate weighted average with neighbors
                total = 0
                count = 0
                
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < height and 0 <= nx < width:
                            weight = 1.0 if (dx == 0 and dy == 0) else 0.5
                            total += grid[ny][nx] * weight
                            count += weight
                
                smoothed_grid[y][x] = total / count if count > 0 else grid[y][x]
        
        return smoothed_grid
    
    def _identify_congestion_zones(self, grid: List[List[float]]) -> List[Dict]:
        """Identify congested areas in the heatmap."""
        
        if not grid:
            return []
        
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        
        congestion_zones = []
        visited = [[False for _ in range(width)] for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                if not visited[y][x] and grid[y][x] > self.heatmap_config["congestion_thresholds"]["medium"]:
                    # Start flood fill to find congested area
                    zone = self._flood_fill_congestion(grid, x, y, visited, width, height)
                    if len(zone) > 2:  # Minimum zone size
                        congestion_zones.append({
                            "zone_id": len(congestion_zones),
                            "cells": zone,
                            "center_x": sum(c[0] for c in zone) / len(zone),
                            "center_y": sum(c[1] for c in zone) / len(zone),
                            "peak_density": max(grid[cy][cx] for cx, cy in zone),
                            "area_size": len(zone)
                        })
        
        return congestion_zones
    
    def _flood_fill_congestion(self, grid: List[List[float]], start_x: int, start_y: int, 
                             visited: List[List[bool]], width: int, height: int) -> List[Tuple[int, int]]:
        """Flood fill algorithm to find congested area."""
        
        threshold = self.heatmap_config["congestion_thresholds"]["medium"]
        stack = [(start_x, start_y)]
        zone = []
        
        while stack:
            x, y = stack.pop()
            
            if (x < 0 or x >= width or y < 0 or y >= height or 
                visited[y][x] or grid[y][x] < threshold):
                continue
            
            visited[y][x] = True
            zone.append((x, y))
            
            # Add neighbors
            stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
        
        return zone
    
    def _calculate_flow_directions(self, states: List[QueueState], dimensions: Dict) -> List[Dict]:
        """Calculate flow directions between checkpoints."""
        
        flow_directions = []
        
        # Simplified flow calculation based on queue changes
        for i, state in enumerate(states):
            if i == 0:
                continue
            
            # Calculate flow from previous state
            # This is simplified - in production would use historical data
            direction = {
                "checkpoint_id": state.checkpoint_id,
                "direction": "unknown",  # Would calculate from trend
                "magnitude": state.current_queue_length / 10,  # Normalized
                "angle": 0  # Would calculate from spatial analysis
            }
            
            flow_directions.append(direction)
        
        return flow_directions
    
    def _process_checkpoint_for_dashboard(self, state: QueueState) -> Dict:
        """Process checkpoint data for dashboard display."""
        
        return {
            "checkpoint_id": state.checkpoint_id,
            "checkpoint_type": state.checkpoint_type,
            "terminal": state.terminal,
            "gate": state.gate,
            "current_queue_length": state.current_queue_length,
            "current_wait_time": state.current_wait_time,
            "utilization": state.current_capacity_utilization,
            "active_lanes": state.active_lanes,
            "total_lanes": state.total_lanes,
            "status": self._get_checkpoint_status(state),
            "predictions": {
                "10min": state.predicted_length_10min,
                "20min": state.predicted_length_20min,
                "30min": state.predicted_length_30min
            }
        }
    
    def _generate_checkpoint_alerts(self, state: QueueState) -> List[Dict]:
        """Generate alerts for a checkpoint."""
        
        alerts = []
        
        # Queue length alert
        if state.current_queue_length > self.dashboard_config["alert_thresholds"]["queue_length"]["critical"]:
            alerts.append({
                "type": "queue_length",
                "level": "critical",
                "message": f"Queue length critical: {state.current_queue_length}",
                "value": state.current_queue_length,
                "threshold": self.dashboard_config["alert_thresholds"]["queue_length"]["critical"]
            })
        elif state.current_queue_length > self.dashboard_config["alert_thresholds"]["queue_length"]["warning"]:
            alerts.append({
                "type": "queue_length",
                "level": "warning",
                "message": f"Queue length high: {state.current_queue_length}",
                "value": state.current_queue_length,
                "threshold": self.dashboard_config["alert_thresholds"]["queue_length"]["warning"]
            })
        
        # Wait time alert
        if state.current_wait_time > self.dashboard_config["alert_thresholds"]["wait_time"]["critical"]:
            alerts.append({
                "type": "wait_time",
                "level": "critical",
                "message": f"Wait time critical: {state.current_wait_time} min",
                "value": state.current_wait_time,
                "threshold": self.dashboard_config["alert_thresholds"]["wait_time"]["critical"]
            })
        elif state.current_wait_time > self.dashboard_config["alert_thresholds"]["wait_time"]["warning"]:
            alerts.append({
                "type": "wait_time",
                "level": "warning",
                "message": f"Wait time high: {state.current_wait_time} min",
                "value": state.current_wait_time,
                "threshold": self.dashboard_config["alert_thresholds"]["wait_time"]["warning"]
            })
        
        # Utilization alert
        if state.current_capacity_utilization > self.dashboard_config["alert_thresholds"]["utilization"]["critical"]:
            alerts.append({
                "type": "utilization",
                "level": "critical",
                "message": f"Utilization critical: {state.current_capacity_utilization:.1%}",
                "value": state.current_capacity_utilization,
                "threshold": self.dashboard_config["alert_thresholds"]["utilization"]["critical"]
            })
        elif state.current_capacity_utilization > self.dashboard_config["alert_thresholds"]["utilization"]["warning"]:
            alerts.append({
                "type": "utilization",
                "level": "warning",
                "message": f"Utilization high: {state.current_capacity_utilization:.1%}",
                "value": state.current_capacity_utilization,
                "threshold": self.dashboard_config["alert_thresholds"]["utilization"]["warning"]
            })
        
        return alerts
    
    def _get_checkpoint_predictions(self, db: Session, state: QueueState) -> List[Dict]:
        """Get predictions for a checkpoint."""
        
        # Get recent predictions
        predictions = db.query(QueuePrediction).filter(
            QueuePrediction.checkpoint_id == state.checkpoint_id,
            QueuePrediction.target_timestamp > datetime.utcnow()
        ).order_by(QueuePrediction.prediction_horizon).limit(3).all()
        
        return [{
            "horizon": pred.prediction_horizon,
            "predicted_length": pred.predicted_queue_length,
            "predicted_wait": pred.predicted_wait_time,
            "confidence": pred.confidence_score,
            "target_time": pred.target_timestamp.isoformat()
        } for pred in predictions]
    
    def _get_checkpoint_status(self, state: QueueState) -> str:
        """Get overall status for a checkpoint."""
        
        if state.current_wait_time > self.dashboard_config["alert_thresholds"]["wait_time"]["critical"]:
            return "critical"
        elif state.current_wait_time > self.dashboard_config["alert_thresholds"]["wait_time"]["warning"]:
            return "warning"
        elif state.current_capacity_utilization > self.dashboard_config["alert_thresholds"]["utilization"]["warning"]:
            return "warning"
        elif state.current_queue_length == 0:
            return "empty"
        else:
            return "normal"
    
    def _get_contributing_flights(self, db: Session, terminal: str) -> List[int]:
        """Get flights contributing to current terminal activity."""
        
        future_time = datetime.utcnow() + timedelta(hours=2)
        
        flights = db.query(Flight).filter(
            Flight.scheduled_time >= datetime.utcnow(),
            Flight.scheduled_time <= future_time,
            Flight.terminal == terminal
        ).limit(10).all()
        
        return [flight.id for flight in flights]
    
    def _group_events_by_interval(self, events: List[QueueEvent], interval_minutes: int) -> List[Dict]:
        """Group events by time intervals for trend analysis."""
        
        if not events:
            return []
        
        # Sort events by time
        events.sort(key=lambda e: e.event_timestamp, reverse=True)
        
        # Group by intervals
        intervals = []
        current_interval = []
        interval_start = events[0].event_timestamp if events else datetime.utcnow()
        
        for event in events:
            time_diff = (interval_start - event.event_timestamp).total_seconds() / 60
            
            if abs(time_diff) > interval_minutes:
                # Save current interval
                if current_interval:
                    intervals.append(self._summarize_interval(current_interval))
                
                # Start new interval
                current_interval = [event]
                interval_start = event.event_timestamp
            else:
                current_interval.append(event)
        
        # Don't forget the last interval
        if current_interval:
            intervals.append(self._summarize_interval(current_interval))
        
        return intervals
    
    def _summarize_interval(self, events: List[QueueEvent]) -> Dict:
        """Summarize events in a time interval."""
        
        if not events:
            return {}
        
        return {
            "timestamp": events[0].event_timestamp.isoformat(),
            "event_count": len(events),
            "avg_queue_length": sum(e.current_queue_length for e in events) / len(events),
            "max_queue_length": max(e.current_queue_length for e in events),
            "min_queue_length": min(e.current_queue_length for e in events),
            "avg_wait_time": sum(e.average_wait_time for e in events) / len(events),
            "max_wait_time": max(e.average_wait_time for e in events),
            "avg_utilization": sum(e.capacity_utilization for e in events) / len(events)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values."""
        
        if len(values) < 2:
            return "stable"
        
        # Simple linear regression
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(range(n), values))
        sum_x2 = sum(x * x for x in range(n))
        
        if (n * sum_x2 - sum_x * sum_x) == 0:
            return "stable"
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        if abs(slope) < 0.1:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _identify_peak_periods(self, trend_data: List[Dict]) -> List[Dict]:
        """Identify peak periods from trend data."""
        
        peak_periods = []
        
        for i, interval in enumerate(trend_data):
            if interval["avg_queue_length"] > max(20, sum(d["avg_queue_length"] for d in trend_data) / len(trend_data) * 1.5):
                peak_periods.append({
                    "timestamp": interval["timestamp"],
                    "queue_length": interval["avg_queue_length"],
                    "wait_time": interval["avg_wait_time"],
                    "severity": "high" if interval["avg_queue_length"] > sum(d["avg_queue_length"] for d in trend_data) / len(trend_data) * 2 else "medium"
                })
        
        return peak_periods
    
    def _analyze_flow_patterns(self, trend_data: List[Dict]) -> Dict:
        """Analyze flow patterns from trend data."""
        
        if not trend_data:
            return {}
        
        # Calculate flow variability
        queue_lengths = [d["avg_queue_length"] for d in trend_data]
        wait_times = [d["avg_wait_time"] for d in trend_data]
        
        return {
            "average_queue_length": sum(queue_lengths) / len(queue_lengths),
            "max_queue_length": max(queue_lengths),
            "min_queue_length": min(queue_lengths),
            "queue_variability": self._calculate_coefficient_of_variation(queue_lengths),
            "average_wait_time": sum(wait_times) / len(wait_times),
            "max_wait_time": max(wait_times),
            "wait_variability": self._calculate_coefficient_of_variation(wait_times),
            "stability_score": self._calculate_stability_score(queue_lengths, wait_times)
        }
    
    def _calculate_coefficient_of_variation(self, values: List[float]) -> float:
        """Calculate coefficient of variation."""
        
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        
        return (variance ** 0.5) / max(mean, 1)
    
    def _calculate_stability_score(self, queue_lengths: List[float], wait_times: List[float]) -> float:
        """Calculate overall stability score."""
        
        if not queue_lengths or not wait_times:
            return 1.0
        
        # Lower variability = higher stability
        queue_cv = self._calculate_coefficient_of_variation(queue_lengths)
        wait_cv = self._calculate_coefficient_of_variation(wait_times)
        
        # Combine into stability score (0-1, higher is better)
        stability = max(0, 1 - (queue_cv + wait_cv) / 2)
        
        return round(stability, 3)
    
    def _calculate_overall_congestion(self, states: List[QueueState]) -> Dict:
        """Calculate overall congestion metrics."""
        
        if not states:
            return {"level": "unknown", "score": 0}
        
        total_passengers = sum(s.current_queue_length for s in states)
        total_capacity = sum(s.current_capacity_utilization * 100 for s in states)  # Convert to percentage
        
        overall_utilization = total_capacity / max(len(states), 1) / 100
        
        # Determine overall congestion level
        if overall_utilization > self.heatmap_config["congestion_thresholds"]["critical"]:
            level = "critical"
        elif overall_utilization > self.heatmap_config["congestion_thresholds"]["high"]:
            level = "high"
        elif overall_utilization > self.heatmap_config["congestion_thresholds"]["medium"]:
            level = "medium"
        else:
            level = "low"
        
        return {
            "level": level,
            "score": round(overall_utilization, 3),
            "total_passengers": total_passengers,
            "total_checkpoints": len(states)
        }
    
    def _identify_bottlenecks(self, checkpoint_congestion: List[Dict]) -> List[Dict]:
        """Identify bottlenecks from congestion analysis."""
        
        # Sort by congestion severity
        sorted_checkpoints = sorted(checkpoint_congestion, 
                              key=lambda x: (x["utilization"], x["wait_time"]), 
                              reverse=True)
        
        bottlenecks = []
        
        # Top 3 most congested checkpoints
        for i, checkpoint in enumerate(sorted_checkpoints[:3]):
            bottlenecks.append({
                "rank": i + 1,
                "checkpoint_id": checkpoint["checkpoint_id"],
                "checkpoint_type": checkpoint["checkpoint_type"],
                "utilization": checkpoint["utilization"],
                "wait_time": checkpoint["wait_time"],
                "severity": checkpoint["level"],
                "impact_score": checkpoint["utilization"] * 0.7 + checkpoint["wait_time"] / 30 * 0.3
            })
        
        return bottlenecks
    
    def _generate_congestion_recommendations(self, congestion_analysis: Dict) -> List[str]:
        """Generate recommendations based on congestion analysis."""
        
        recommendations = []
        
        # Check for critical issues
        if congestion_analysis["overall_congestion"]["level"] == "critical":
            recommendations.append("Open additional lanes immediately at critical checkpoints")
            recommendations.append("Deploy staff to high-congestion areas")
            recommendations.append("Activate contingency procedures")
        
        # Check for type-specific issues
        for checkpoint_type, data in congestion_analysis["congestion_by_type"].items():
            if data["critical_count"] > 0:
                if checkpoint_type == "security":
                    recommendations.append("Open additional security screening lanes")
                elif checkpoint_type == "checkin":
                    recommendations.append("Activate self-service kiosks")
                elif checkpoint_type == "boarding":
                    recommendations.append("Stagger boarding calls")
                elif checkpoint_type == "immigration":
                    recommendations.append("Open additional immigration booths")
        
        # General recommendations
        if len(congestion_analysis["bottlenecks"]) > 0:
            recommendations.append("Reallocate resources from low-congestion to high-congestion areas")
            recommendations.append("Review and optimize checkpoint layouts")
        
        return recommendations


# Global instance
flow_visualization = FlowVisualizationEngine()
