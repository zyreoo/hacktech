"""
Passenger Flow Predictor
------------------------

This module will host the lightweight AI / heuristic models that forecast
queue lengths and wait times at check-in and security 60–120 minutes ahead.

For now it only defines a stub interface that other modules can call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Protocol

from data_hub.models import PassengerFlowPoint


@dataclass
class QueueForecast:
    """Simple forecast output for a single time bucket at a terminal."""

    time: str
    terminal: str
    expected_queue_time: float
    expected_passengers: int
    recommended_open_lanes: int


class PassengerFlowPredictor(Protocol):
    """Contract for any predictor implementation."""

    def forecast(
        self,
        history: Iterable[PassengerFlowPoint],
        horizon_minutes: int = 60,
    ) -> List[QueueForecast]:
        """
        Produce queue forecasts using historical passenger_flow data.

        The initial implementation can be a simple heuristic; later you can
        swap in a more advanced model (e.g. gradient boosting, LSTM, etc.).
        """

