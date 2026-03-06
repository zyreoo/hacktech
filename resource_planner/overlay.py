"""
Resource Planner Overlay
------------------------

This package will back a drag-and-drop planning board for:
- gates and stands
- desks and check-in islands
- staff allocations

The first real implementation can expose simple in-memory plans that are
later reconciled with the canonical data hub.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Assignment:
    """Planned assignment of a resource (gate, stand, desk, staff) to a flight."""

    flight_id: str
    resource_type: str  # e.g. "gate", "stand", "desk", "staff"
    resource_id: str
    from_time: str
    to_time: str
    comment: Optional[str] = None


class ConflictDetector:
    """Placeholder for conflict-detection logic between assignments."""

    def find_conflicts(self, assignments: list[Assignment]) -> list[Assignment]:
        """Return assignments that are in conflict with each other."""
        return []

