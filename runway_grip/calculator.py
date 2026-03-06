"""
Runway Grip Calculator
----------------------

This module will ingest sensor and camera feeds to estimate a simple
runway grip / friction score (e.g. dry, wet, standing water, slush, ice).
The score can then be exposed to the dashboard and alerting layer.
"""

from dataclasses import dataclass


@dataclass
class GripReading:
    """Single grip reading for a runway at a given time."""

    runway_id: str
    time: str
    grip_score: float  # 0.0 (no grip) .. 1.0 (ideal dry runway)
    condition: str  # e.g. "dry", "wet", "water", "slush", "ice"


class GripCalculator:
    """Placeholder calculator for runway grip derived from raw sensors."""

    def compute(self) -> GripReading:
        """
        Compute and return a synthetic grip reading.

        Replace this with real sensor fusion logic once data sources exist.
        """

        return GripReading(
            runway_id="RWY-09L",
            time="1970-01-01T00:00:00Z",
            grip_score=1.0,
            condition="dry",
        )

