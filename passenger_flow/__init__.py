"""
Passenger Flow Predictor package.

Owns logic for modelling and forecasting passenger queues at check-in
and security using canonical data from the Data Hub.
"""

from .predictor import PassengerFlowPredictor, QueueForecast

__all__ = ["PassengerFlowPredictor", "QueueForecast"]

