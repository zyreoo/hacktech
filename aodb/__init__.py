"""
AI-native Airport Operational Database (AODB) package.

Provides a reconciled, possibly predicted view of flight data
on top of the raw airport.db schedule.
"""

from .core import AODBFacade, AODBFlightView

__all__ = ["AODBFacade", "AODBFlightView"]

