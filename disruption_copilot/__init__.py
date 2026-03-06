"""
Disruption Copilot package.

Hosts the reasoning engine that combines schedules, passenger flow,
machinery status, weather and runway grip into ranked recommendations.
"""

from .engine import DisruptionEngine, Recommendation

__all__ = ["DisruptionEngine", "Recommendation"]

