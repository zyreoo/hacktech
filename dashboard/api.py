"""
Dashboard / UI API Surface
--------------------------

This module is the thin backend surface that a future UI (web, native, or
control-room wall display) can speak to. For now it only defines function
signatures and simple types for the different panels on the dashboard.
"""

from dataclasses import dataclass
from typing import List

from data_hub.models import Airport, Flight, Alert


@dataclass
class DashboardSnapshot:
    """Minimal aggregated state for the main dashboard view."""

    flights: List[Flight]
    alerts: List[Alert]
    airports: List[Airport]


def get_dashboard_snapshot() -> DashboardSnapshot:
    """
    Return a synthetic snapshot for the dashboard.

    Later this can pull live objects from the data hub and the
    Disruption Copilot recommendation engine.
    """

    return DashboardSnapshot(flights=[], alerts=[], airports=[])

