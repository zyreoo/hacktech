"""
Queue Data Ingestion Service.

Comprehensive queue data ingestion from multiple sources:
- Camera counts with computer vision
- Manual staff input
- Sensor data (infrared, weight sensors)
- Data normalization and validation
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..models import (
    QueueSensorData, QueueEvent, QueueState, Flight
)
from ..database import SessionLocal


class QueueDataIngestionEngine:
    """Advanced queue data ingestion and normalization system."""
    
    def __init__(self):
        self.sensor_types = {
            "camera": {"confidence_threshold": 0.7, "processing_delay": 30},
            "manual": {"confidence_threshold": 0.9, "processing_delay": 0},
            "infrared": {"confidence_threshold": 0.8, "processing_delay": 15},
            "weight_sensor": {"confidence_threshold": 0.85, "processing_delay": 10}
        }
        
        self.checkpoint_types = ["security", "checkin", "boarding", "immigration"]
        
        self.normalization_rules = {
            "queue_length_factors": {
                "camera": 1.0,      # Direct count from video
                "manual": 1.0,      # Staff count
                "infrared": 0.9,    # May miss some passengers
                "weight_sensor": 1.1   # May overcount with luggage
            },
            "flow_rate_factors": {
                "camera": 1.0,
                "manual": 0.95,     # Manual counting slower
                "infrared": 1.05,
                "weight_sensor": 0.9
            }
        }
    
    def ingest_camera_data(self, db: Session, camera_data: Dict) -> QueueSensorData:
        """Ingest camera-based queue monitoring data."""
        
        # Validate camera data
        validated_data = self._validate_sensor_data(camera_data, "camera")
        
        # Apply camera-specific processing
        processed_data = self._process_camera_data(validated_data)
        
        # Create sensor data record
        sensor_data = QueueSensorData(
            sensor_id=processed_data["sensor_id"],
            sensor_type="camera",
            checkpoint_type=processed_data["checkpoint_type"],
            terminal=processed_data["terminal"],
            gate=processed_data.get("gate"),
            passenger_count=processed_data["passenger_count"],
            queue_length_meters=processed_data["queue_length_meters"],
            flow_rate_ppm=processed_data["flow_rate_ppm"],
            dwell_time_seconds=processed_data["dwell_time_seconds"],
            lane_id=processed_data.get("lane_id"),
            confidence_score=processed_data["confidence_score"],
            data_source="automatic",
            sensor_timestamp=processed_data["sensor_timestamp"],
            created_at=datetime.utcnow()
        )
        
        db.add(sensor_data)
        db.flush()
        
        # Create normalized queue event
        queue_event = self._create_normalized_event(db, sensor_data, processed_data)
        db.add(queue_event)
        
        return sensor_data
    
    def ingest_manual_data(self, db: Session, manual_data: Dict) -> QueueSensorData:
        """Ingest manual staff input data."""
        
        # Validate manual data
        validated_data = self._validate_sensor_data(manual_data, "manual")
        
        # Apply manual-specific processing
        processed_data = self._process_manual_data(validated_data)
        
        # Create sensor data record
        sensor_data = QueueSensorData(
            sensor_id=processed_data["sensor_id"],
            sensor_type="manual",
            checkpoint_type=processed_data["checkpoint_type"],
            terminal=processed_data["terminal"],
            gate=processed_data.get("gate"),
            passenger_count=processed_data["passenger_count"],
            queue_length_meters=processed_data["queue_length_meters"],
            flow_rate_ppm=processed_data["flow_rate_ppm"],
            dwell_time_seconds=processed_data["dwell_time_seconds"],
            lane_id=processed_data.get("lane_id"),
            confidence_score=processed_data["confidence_score"],
            data_source="manual",
            staff_notes=processed_data.get("staff_notes"),
            sensor_timestamp=processed_data["sensor_timestamp"],
            created_at=datetime.utcnow()
        )
        
        db.add(sensor_data)
        db.flush()
        
        # Create normalized queue event
        queue_event = self._create_normalized_event(db, sensor_data, processed_data)
        db.add(queue_event)
        
        return sensor_data
    
    def ingest_sensor_data(self, db: Session, sensor_data: Dict) -> QueueSensorData:
        """Ingest sensor data from infrared, weight sensors, etc."""
        
        sensor_type = sensor_data.get("sensor_type", "infrared")
        
        # Validate sensor data
        validated_data = self._validate_sensor_data(sensor_data, sensor_type)
        
        # Apply sensor-specific processing
        if sensor_type == "infrared":
            processed_data = self._process_infrared_data(validated_data)
        elif sensor_type == "weight_sensor":
            processed_data = self._process_weight_sensor_data(validated_data)
        else:
            processed_data = validated_data
        
        # Create sensor data record
        sensor_record = QueueSensorData(
            sensor_id=processed_data["sensor_id"],
            sensor_type=sensor_type,
            checkpoint_type=processed_data["checkpoint_type"],
            terminal=processed_data["terminal"],
            gate=processed_data.get("gate"),
            passenger_count=processed_data["passenger_count"],
            queue_length_meters=processed_data["queue_length_meters"],
            flow_rate_ppm=processed_data["flow_rate_ppm"],
            dwell_time_seconds=processed_data["dwell_time_seconds"],
            lane_id=processed_data.get("lane_id"),
            confidence_score=processed_data["confidence_score"],
            data_source="automatic",
            sensor_timestamp=processed_data["sensor_timestamp"],
            created_at=datetime.utcnow()
        )
        
        db.add(sensor_record)
        db.flush()
        
        # Create normalized queue event
        queue_event = self._create_normalized_event(db, sensor_record, processed_data)
        db.add(queue_event)
        
        return sensor_record
    
    def batch_ingest_data(self, db: Session, data_batch: List[Dict]) -> List[QueueSensorData]:
        """Batch ingest multiple sensor data records."""
        
        sensor_records = []
        queue_events = []
        
        for data in data_batch:
            sensor_type = data.get("sensor_type", "camera")
            
            # Route to appropriate ingestion method
            if sensor_type == "camera":
                sensor_record = self.ingest_camera_data(db, data)
            elif sensor_type == "manual":
                sensor_record = self.ingest_manual_data(db, data)
            else:
                sensor_record = self.ingest_sensor_data(db, data)
            
            sensor_records.append(sensor_record)
        
        return sensor_records
    
    def _validate_sensor_data(self, data: Dict, sensor_type: str) -> Dict:
        """Validate and sanitize sensor data."""
        
        required_fields = ["sensor_id", "checkpoint_type", "terminal", "sensor_timestamp"]
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate sensor type
        if sensor_type not in self.sensor_types:
            raise ValueError(f"Unsupported sensor type: {sensor_type}")
        
        # Validate checkpoint type
        if data["checkpoint_type"] not in self.checkpoint_types:
            raise ValueError(f"Unsupported checkpoint type: {data['checkpoint_type']}")
        
        # Validate timestamps
        if isinstance(data["sensor_timestamp"], str):
            try:
                data["sensor_timestamp"] = datetime.fromisoformat(data["sensor_timestamp"])
            except ValueError:
                raise ValueError("Invalid timestamp format")
        
        # Validate numeric fields
        numeric_fields = ["passenger_count", "queue_length_meters", "flow_rate_ppm", "dwell_time_seconds"]
        for field in numeric_fields:
            if field in data and data[field] is not None:
                try:
                    data[field] = float(data[field])
                    if data[field] < 0:
                        raise ValueError(f"Negative value for {field}")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value for {field}")
        
        return data
    
    def _process_camera_data(self, data: Dict) -> Dict:
        """Process camera-specific data with computer vision corrections."""
        
        # Apply camera-specific corrections
        confidence_threshold = self.sensor_types["camera"]["confidence_threshold"]
        
        # Calculate confidence based on lighting, crowd density, etc.
        base_confidence = data.get("confidence", 0.8)
        lighting_factor = self._assess_lighting_conditions(data.get("lighting_level", "good"))
        crowd_factor = self._assess_crowd_density(data.get("passenger_count", 0))
        
        adjusted_confidence = base_confidence * lighting_factor * crowd_factor
        
        # Normalize queue length based on camera angle and height
        raw_length = data.get("queue_length_meters", 0)
        angle_correction = data.get("camera_angle", 0)  # degrees from vertical
        height_correction = data.get("camera_height", 3.0)  # meters
        
        if angle_correction > 0:
            # Adjust for camera angle
            length_factor = 1.0 / (abs(angle_correction) / 90.0 + 0.1)
            raw_length *= length_factor
        
        # Apply normalization factor
        normalized_length = raw_length * self.normalization_rules["queue_length_factors"]["camera"]
        normalized_flow = data.get("flow_rate_ppm", 0) * self.normalization_rules["flow_rate_factors"]["camera"]
        
        return {
            **data,
            "confidence_score": min(1.0, adjusted_confidence),
            "queue_length_meters": normalized_length,
            "flow_rate_ppm": normalized_flow,
            "processing_metadata": {
                "camera_angle": angle_correction,
                "camera_height": height_correction,
                "lighting_level": data.get("lighting_level", "good"),
                "detection_method": "computer_vision"
            }
        }
    
    def _process_manual_data(self, data: Dict) -> Dict:
        """Process manual staff input data."""
        
        # Manual data is typically more accurate but may have delays
        confidence_threshold = self.sensor_types["manual"]["confidence_threshold"]
        
        # Check for common manual input errors
        passenger_count = data.get("passenger_count", 0)
        queue_length = data.get("queue_length_meters", 0)
        
        # Validate consistency between count and length
        if passenger_count > 0 and queue_length > 0:
            density = passenger_count / max(queue_length, 1)
            if density > 5:  # More than 5 people per meter seems unrealistic
                # Adjust queue length based on typical density
                queue_length = passenger_count / 2.5  # Average 2.5 people per meter
        
        # Manual data typically has high confidence but may be delayed
        timestamp_delay = data.get("reporting_delay", 0)
        actual_timestamp = data["sensor_timestamp"] - timedelta(seconds=timestamp_delay)
        
        return {
            **data,
            "confidence_score": confidence_threshold,
            "queue_length_meters": queue_length,
            "sensor_timestamp": actual_timestamp,
            "processing_metadata": {
                "reporting_delay": timestamp_delay,
                "input_method": "manual_staff",
                "validation_applied": True
            }
        }
    
    def _process_infrared_data(self, data: Dict) -> Dict:
        """Process infrared sensor data with temperature corrections."""
        
        # Infrared sensors can be affected by ambient temperature
        ambient_temp = data.get("ambient_temperature", 20.0)  # Celsius
        temp_correction = 1.0
        
        if ambient_temp > 30:  # High temperature can reduce sensitivity
            temp_correction = 0.9
        elif ambient_temp < 5:  # Low temperature can increase noise
            temp_correction = 0.85
        
        # Apply normalization factor
        normalized_count = data.get("passenger_count", 0) * temp_correction
        normalized_length = data.get("queue_length_meters", 0) * temp_correction
        
        return {
            **data,
            "passenger_count": max(0, int(normalized_count)),
            "queue_length_meters": max(0, normalized_length),
            "confidence_score": self.sensor_types["infrared"]["confidence_threshold"] * temp_correction,
            "processing_metadata": {
                "ambient_temperature": ambient_temp,
                "temperature_correction": temp_correction,
                "sensor_type": "infrared_beam"
            }
        }
    
    def _process_weight_sensor_data(self, data: Dict) -> Dict:
        """Process weight sensor data with calibration corrections."""
        
        # Weight sensors need calibration for different passenger profiles
        avg_passenger_weight = data.get("average_passenger_weight", 70.0)  # kg
        calibration_factor = 70.0 / max(avg_passenger_weight, 1.0)
        
        # Weight sensors may count luggage as passengers
        luggage_factor = data.get("luggage_present", False)
        if luggage_factor:
            calibration_factor *= 0.8  # Assume 20% of weight is luggage
        
        # Apply normalization
        normalized_count = data.get("passenger_count", 0) * calibration_factor
        
        return {
            **data,
            "passenger_count": max(0, int(normalized_count)),
            "confidence_score": self.sensor_types["weight_sensor"]["confidence_threshold"] * calibration_factor,
            "processing_metadata": {
                "average_passenger_weight": avg_passenger_weight,
                "calibration_factor": calibration_factor,
                "luggage_present": luggage_factor
            }
        }
    
    def _create_normalized_event(self, db: Session, sensor_data: QueueSensorData, processed_data: Dict) -> QueueEvent:
        """Create normalized queue event from processed sensor data."""
        
        # Generate unique event ID
        event_id = f"EV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate queue metrics
        passenger_count = processed_data["passenger_count"]
        queue_length = processed_data["queue_length_meters"]
        flow_rate = processed_data["flow_rate_ppm"]
        dwell_time = processed_data.get("dwell_time_seconds", 0)
        
        # Calculate density (passengers per square meter)
        # Assume typical queue width of 2 meters
        queue_area = max(queue_length * 2.0, 1.0)  # square meters
        queue_density = passenger_count / queue_area if queue_area > 0 else 0
        
        # Calculate wait time based on flow rate
        average_wait_time = int(passenger_count / max(flow_rate, 0.1)) if flow_rate > 0 else 0
        peak_wait_time = average_wait_time * 1.5  # Assume peak is 50% higher
        
        # Calculate service rate
        service_rate = flow_rate if passenger_count > 0 else 0
        
        # Calculate capacity utilization
        max_capacity = self._get_max_capacity(processed_data["checkpoint_type"])
        capacity_utilization = min(passenger_count / max(max_capacity, 1), 1.0)
        
        # Determine congestion level
        congestion_level = self._calculate_congestion_level(capacity_utilization, average_wait_time)
        
        # Determine trend direction
        trend_direction = self._calculate_trend(db, processed_data)
        
        # Detect anomalies
        anomaly_detected = self._detect_anomaly(processed_data, db)
        
        # Get contributing flights
        contributing_flights = self._get_contributing_flights(db, processed_data)
        
        return QueueEvent(
            event_id=event_id,
            checkpoint_id=processed_data["sensor_id"],
            checkpoint_type=processed_data["checkpoint_type"],
            terminal=processed_data["terminal"],
            gate=processed_data.get("gate"),
            lane_id=processed_data.get("lane_id"),
            current_queue_length=passenger_count,
            queue_density=queue_density,
            average_wait_time=average_wait_time,
            peak_wait_time=peak_wait_time,
            service_rate=service_rate,
            capacity_utilization=capacity_utilization,
            arrival_rate=flow_rate,
            departure_rate=service_rate,
            flow_efficiency=min(service_rate / max(flow_rate, 0.1), 1.0) if flow_rate > 0 else 0,
            congestion_level=congestion_level,
            trend_direction=trend_direction,
            anomaly_detected=anomaly_detected,
            contributing_flights=json.dumps(contributing_flights),
            time_window_minutes=5,
            event_timestamp=processed_data["sensor_timestamp"],
            created_at=datetime.utcnow()
        )
    
    def _assess_lighting_conditions(self, lighting_level: str) -> float:
        """Assess lighting conditions for camera confidence."""
        
        lighting_factors = {
            "excellent": 1.0,
            "good": 0.9,
            "moderate": 0.7,
            "poor": 0.5,
            "dark": 0.3
        }
        
        return lighting_factors.get(lighting_level.lower(), 0.7)
    
    def _assess_crowd_density(self, passenger_count: int) -> float:
        """Assess crowd density impact on detection accuracy."""
        
        if passenger_count < 10:
            return 1.0  # Low density, high confidence
        elif passenger_count < 25:
            return 0.9  # Moderate density
        elif passenger_count < 50:
            return 0.8  # High density
        else:
            return 0.7  # Very high density, lower confidence
    
    def _get_max_capacity(self, checkpoint_type: str) -> int:
        """Get maximum capacity for different checkpoint types."""
        
        capacities = {
            "security": 50,      # Security screening area
            "checkin": 30,       # Check-in counter area
            "boarding": 100,     # Boarding gate area
            "immigration": 40     # Immigration area
        }
        
        return capacities.get(checkpoint_type, 50)
    
    def _calculate_congestion_level(self, utilization: float, wait_time: int) -> str:
        """Calculate congestion level based on utilization and wait time."""
        
        if utilization > 0.8 or wait_time > 20:
            return "critical"
        elif utilization > 0.6 or wait_time > 10:
            return "high"
        elif utilization > 0.4 or wait_time > 5:
            return "medium"
        else:
            return "low"
    
    def _calculate_trend(self, db: Session, current_data: Dict) -> str:
        """Calculate trend direction based on recent data."""
        
        # Get recent events for this checkpoint
        recent_events = db.query(QueueEvent).filter(
            QueueEvent.checkpoint_id == current_data["sensor_id"],
            QueueEvent.event_timestamp >= current_data["sensor_timestamp"] - timedelta(minutes=15)
        ).order_by(QueueEvent.event_timestamp.desc()).limit(3).all()
        
        if len(recent_events) < 2:
            return "stable"
        
        # Compare current with previous
        current_count = current_data["passenger_count"]
        previous_count = recent_events[1].current_queue_length if len(recent_events) > 1 else current_count
        
        if current_count > previous_count * 1.1:
            return "increasing"
        elif current_count < previous_count * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def _detect_anomaly(self, current_data: Dict, db: Session) -> bool:
        """Detect anomalies in current sensor data."""
        
        # Get historical average for this time and checkpoint
        current_time = current_data["sensor_timestamp"]
        hour_of_day = current_time.hour
        day_of_week = current_time.weekday()
        
        historical_avg = db.query(func.avg(QueueEvent.current_queue_length)).filter(
            QueueEvent.checkpoint_id == current_data["sensor_id"],
            func.extract('hour', QueueEvent.event_timestamp) == hour_of_day,
            func.extract('dow', QueueEvent.event_timestamp) == day_of_week
        ).scalar() or 0
        
        current_count = current_data["passenger_count"]
        
        # Check if current is significantly different from historical
        if historical_avg > 0:
            deviation = abs(current_count - historical_avg) / historical_avg
            return deviation > 0.5  # 50% deviation from historical average
        
        return False
    
    def _get_contributing_flights(self, db: Session, data: Dict) -> List[int]:
        """Get flights contributing to current queue."""
        
        checkpoint_time = data["sensor_timestamp"]
        terminal = data["terminal"]
        gate = data.get("gate")
        
        # Get flights departing in next 2 hours from this terminal/gate
        flights = db.query(Flight).filter(
            Flight.scheduled_time >= checkpoint_time,
            Flight.scheduled_time <= checkpoint_time + timedelta(hours=2),
            Flight.terminal == terminal
        )
        
        if gate:
            flights = flights.filter(Flight.gate == gate)
        
        return [flight.id for flight in flights.limit(10).all()]


# Global instance
queue_data_ingestion = QueueDataIngestionEngine()
