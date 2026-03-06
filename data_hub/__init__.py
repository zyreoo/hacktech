"""
Data Hub
--------

Canonical access layer around the underlying airport.db.

This package owns the core domain models (airports, flights, passenger flow,
alerts) and is the place to add repository/DAO-style helpers later.
"""

from . import models  # re-export for convenience

__all__ = ["models"]

