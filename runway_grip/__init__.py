"""
Runway Grip package.

Responsible for ingesting sensor/camera data and producing a simple
runway grip score that can feed dashboards and alerts.
"""

from .calculator import GripCalculator, GripReading

__all__ = ["GripCalculator", "GripReading"]

