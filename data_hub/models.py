from dataclasses import dataclass
from typing import Optional


@dataclass
class Airport:
    """Canonical view of an airport record backed by the airports table."""

    iata: str
    icao: Optional[str]
    name: str
    timezone: Optional[str]
    city_name: Optional[str]
    city_iata: Optional[str]
    utc_offset_hours: Optional[float]
    country_code_a2: Optional[str]


@dataclass
class Flight:
    """Lightweight flight snapshot from the flights table."""

    flight_id: str
    origin_airport: str
    destination_airport: str
    departure_time: str
    arrival_time: str
    passengers: int
    aircraft: Optional[str]
    gate: Optional[str]
    status: str


@dataclass
class PassengerFlowPoint:
    """Single time bucket of passenger_flow data for a flight."""

    flight_id: str
    time: str
    terminal: Optional[str]
    passengers_arriving_security: int
    open_lanes: int
    queue_time: float


@dataclass
class Alert:
    """Operational alert originating from the alerts table."""

    alert_id: int
    time: str
    type: str
    message: str
    severity: str

