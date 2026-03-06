"""
AI-Native AODB
--------------

Predictive, self-healing layer on top of the raw flight schedule in
airport.db. This is where you can later:
- reconcile conflicting inputs from different systems
- infer missing times (ETA, ETD)
- track confidence levels per field
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AODBFlightView:
    """Canonical, possibly predicted view of a single flight."""

    flight_id: str
    origin_airport: str
    destination_airport: str
    scheduled_departure: str
    scheduled_arrival: str
    predicted_departure: Optional[str] = None
    predicted_arrival: Optional[str] = None
    data_conflict: bool = False


class AODBFacade:
    """Facade for querying and reconciling flights across data sources."""

    def get_flight(self, flight_id: str) -> Optional[AODBFlightView]:
        """Return a synthetic view for the given flight_id."""
        return None

