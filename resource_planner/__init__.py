"""
Resource Planner Overlay package.

Provides structures and services for planning gates, stands, desks,
and staff allocations on top of the canonical data hub.
"""

from .overlay import Assignment, ConflictDetector

__all__ = ["Assignment", "ConflictDetector"]

