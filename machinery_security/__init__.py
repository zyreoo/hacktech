"""
Machinery & Cyber-Physical Security package.

Monitors heavy machinery and basic OT/network signals for anomalies.
"""

from .monitor import MachineryAlert, MachineryMonitor, Severity

__all__ = ["MachineryAlert", "MachineryMonitor", "Severity"]

