"""
Disruption Copilot
------------------

Cross-module reasoning engine that combines:
- flight schedules
- passenger flow forecasts
- machinery and sensor status
- weather and runway grip

to suggest ranked operational actions during disruption.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Recommendation:
    """Single recommended operational action with a simple score."""

    title: str
    description: str
    score: float  # higher is more urgent/valuable


class DisruptionEngine:
    """Placeholder engine that will eventually orchestrate the other modules."""

    def recommend_actions(self) -> List[Recommendation]:
        """
        Return a ranked list of recommendations.

        The first implementation can be rules-based; later you can promote
        this to a full AI planner.
        """

        return []

