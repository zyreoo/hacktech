"""
Dashboard / UI package.

Backend surface that powers the operational dashboard showing
flights, queues, gates, runway grip and machinery alerts.
"""

from .api import DashboardSnapshot, get_dashboard_snapshot

__all__ = ["DashboardSnapshot", "get_dashboard_snapshot"]

