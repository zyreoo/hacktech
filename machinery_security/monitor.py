"""
Machinery & Cyber-Physical Security
-----------------------------------

This module will monitor heavy machinery (jet bridges, baggage belts, etc.)
alongside basic network / OT sensor signals and raise anomalies.
"""

from dataclasses import dataclass
from typing import Literal


Severity = Literal["info", "warning", "critical"]


@dataclass
class MachineryAlert:
    """Security or health alert for a single piece of machinery."""

    machinery_id: str
    time: str
    message: str
    severity: Severity


class MachineryMonitor:
    """Placeholder monitor that will consume raw telemetry streams."""

    def check(self) -> list[MachineryAlert]:
        """
        Inspect telemetry and return any active alerts.

        An initial version can implement simple threshold rules on sensor
        values before moving to anomaly detection models.
        """

        return []

