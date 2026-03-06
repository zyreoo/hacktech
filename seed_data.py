#!/usr/bin/env python3
"""
Seed airport.db with sample data.
Run: python seed_data.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "airport.db")


def seed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Airports
    airports = [
        ("LHR", "EGLL", "London Heathrow", "Europe/London", "London", "LON", 0.0, "GB"),
        ("CDG", "LFPG", "Paris Charles de Gaulle", "Europe/Paris", "Paris", "PAR", 1.0, "FR"),
        ("FRA", "EDDF", "Frankfurt Airport", "Europe/Berlin", "Frankfurt", "FRA", 1.0, "DE"),
        ("AMS", "EHAM", "Amsterdam Schiphol", "Europe/Amsterdam", "Amsterdam", "AMS", 1.0, "NL"),
        ("MAD", "LEMD", "Adolfo Suárez Madrid–Barajas", "Europe/Madrid", "Madrid", "MAD", 1.0, "ES"),
        ("FCO", "LIRF", "Rome Fiumicino", "Europe/Rome", "Rome", "ROM", 1.0, "IT"),
        ("BCN", "LEBL", "Barcelona–El Prat", "Europe/Madrid", "Barcelona", "BCN", 1.0, "ES"),
        ("LIS", "LPPT", "Lisbon Portela", "Europe/Lisbon", "Lisbon", "LIS", 0.0, "PT"),
        ("DUB", "EIDW", "Dublin Airport", "Europe/Dublin", "Dublin", "DUB", 0.0, "IE"),
        ("VIE", "LOWW", "Vienna International", "Europe/Vienna", "Vienna", "VIE", 1.0, "AT"),
        ("MUC", "EDDM", "Munich Airport", "Europe/Berlin", "Munich", "MUC", 1.0, "DE"),
        ("ZRH", "LSZH", "Zurich Airport", "Europe/Zurich", "Zurich", "ZRH", 1.0, "CH"),
        ("BRU", "EBBR", "Brussels Airport", "Europe/Brussels", "Brussels", "BRU", 1.0, "BE"),
        ("CPH", "EKCH", "Copenhagen Airport", "Europe/Copenhagen", "Copenhagen", "CPH", 1.0, "DK"),
        ("OSL", "ENGM", "Oslo Gardermoen", "Europe/Oslo", "Oslo", "OSL", 1.0, "NO"),
        ("JFK", "KJFK", "John F. Kennedy International", "America/New_York", "New York", "NYC", -5.0, "US"),
        ("DXB", "OMDB", "Dubai International", "Asia/Dubai", "Dubai", "DXB", 4.0, "AE"),
    ]
    cur.executemany(
        """INSERT OR IGNORE INTO airports
           (IATA, ICAO, AirportName, TimeZone, City_Name, City_IATA, UTC_Offset_Hours, Country_CodeA2)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        airports,
    )

    # Flights (today-style times, mixed statuses)
    flights = [
        ("BA301", "LHR", "CDG", "2025-03-06 07:30:00", "2025-03-06 09:45:00", 180, "A320", "A12", "boarding"),
        ("AF1042", "CDG", "LHR", "2025-03-06 08:00:00", "2025-03-06 08:25:00", 165, "A321", "B7", "scheduled"),
        ("LH902", "FRA", "LHR", "2025-03-06 09:15:00", "2025-03-06 10:20:00", 142, "A319", "A8", "scheduled"),
        ("KL1008", "AMS", "LHR", "2025-03-06 10:00:00", "2025-03-06 10:35:00", 98, "E190", "B22", "delayed"),
        ("IB3166", "MAD", "BCN", "2025-03-06 11:20:00", "2025-03-06 12:15:00", 120, "A320", "D4", "scheduled"),
        ("AZ104", "FCO", "CDG", "2025-03-06 12:45:00", "2025-03-06 14:30:00", 156, "A321", "A3", "scheduled"),
        ("TP448", "LIS", "MAD", "2025-03-06 13:00:00", "2025-03-06 15:10:00", 88, "A320", "C11", "cancelled"),
        ("BA452", "LHR", "FRA", "2025-03-06 14:00:00", "2025-03-06 16:35:00", 95, "A320", "A15", "scheduled"),
        ("VY100", "BCN", "AMS", "2025-03-06 15:30:00", "2025-03-06 17:50:00", 134, "A320", "D8", "scheduled"),
        ("EI164", "DUB", "LHR", "2025-03-06 06:45:00", "2025-03-06 08:10:00", 110, "A320", "B3", "departed"),
        ("EI165", "LHR", "DUB", "2025-03-06 09:00:00", "2025-03-06 10:25:00", 102, "A320", "B5", "scheduled"),
        ("OS451", "VIE", "FRA", "2025-03-06 08:30:00", "2025-03-06 09:45:00", 98, "A321", "A2", "scheduled"),
        ("LX362", "ZRH", "LHR", "2025-03-06 11:00:00", "2025-03-06 11:55:00", 125, "A320", "A18", "scheduled"),
        ("SN2044", "BRU", "CDG", "2025-03-06 10:30:00", "2025-03-06 11:25:00", 85, "A319", "B12", "scheduled"),
        ("SK502", "CPH", "AMS", "2025-03-06 12:00:00", "2025-03-06 13:25:00", 92, "A320", "C2", "scheduled"),
        ("DY1234", "OSL", "BCN", "2025-03-06 13:30:00", "2025-03-06 16:20:00", 178, "B737", "D12", "scheduled"),
        ("BA178", "LHR", "JFK", "2025-03-06 10:30:00", "2025-03-06 13:15:00", 215, "B777", "A1", "scheduled"),
        ("EK2", "DXB", "LHR", "2025-03-06 07:00:00", "2025-03-06 11:50:00", 380, "A380", "B1", "scheduled"),
        ("LH1802", "MUC", "FCO", "2025-03-06 14:30:00", "2025-03-06 15:55:00", 145, "A321", "A6", "scheduled"),
        ("AF1742", "CDG", "MAD", "2025-03-06 15:00:00", "2025-03-06 17:15:00", 168, "A321", "A9", "scheduled"),
        ("IB3420", "BCN", "LIS", "2025-03-06 16:00:00", "2025-03-06 17:35:00", 112, "A320", "D6", "scheduled"),
        ("KL1832", "AMS", "FCO", "2025-03-06 17:00:00", "2025-03-06 19:15:00", 132, "B737", "C14", "scheduled"),
        ("BA712", "LHR", "DUB", "2025-03-06 18:00:00", "2025-03-06 19:20:00", 95, "A319", "B8", "scheduled"),
        ("LX1412", "ZRH", "VIE", "2025-03-06 19:00:00", "2025-03-06 20:10:00", 88, "E190", "A4", "scheduled"),
        ("SK618", "CPH", "OSL", "2025-03-06 20:00:00", "2025-03-06 21:05:00", 105, "A320", "C7", "scheduled"),
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO flights
           (flight_id, origin_airport, destination_airport, departure_time, arrival_time, passengers, aircraft, gate, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        flights,
    )

    # Passenger flow (snapshots for multiple flights)
    passenger_flow = [
        ("BA301", "2025-03-06 06:45:00", "T5", 45, 4, 8.5),
        ("BA301", "2025-03-06 07:00:00", "T5", 62, 5, 6.2),
        ("BA301", "2025-03-06 07:15:00", "T5", 38, 5, 4.0),
        ("LH902", "2025-03-06 08:30:00", "T1", 28, 3, 12.0),
        ("LH902", "2025-03-06 08:45:00", "T1", 55, 4, 9.5),
        ("KL1008", "2025-03-06 09:15:00", "T2", 72, 3, 15.0),
        ("KL1008", "2025-03-06 09:30:00", "T2", 88, 4, 11.2),
        ("IB3166", "2025-03-06 10:40:00", "T4", 41, 6, 5.0),
        ("EI164", "2025-03-06 06:00:00", "T2", 22, 2, 5.5),
        ("EI164", "2025-03-06 06:20:00", "T2", 48, 3, 7.0),
        ("AF1042", "2025-03-06 07:15:00", "T2", 35, 4, 6.0),
        ("AF1042", "2025-03-06 07:30:00", "T2", 58, 4, 8.5),
        ("LX362", "2025-03-06 10:15:00", "T1", 44, 5, 4.5),
        ("LX362", "2025-03-06 10:30:00", "T1", 71, 5, 7.2),
        ("BA178", "2025-03-06 09:00:00", "T5", 95, 6, 12.0),
        ("BA178", "2025-03-06 09:30:00", "T5", 128, 6, 14.5),
        ("BA178", "2025-03-06 10:00:00", "T5", 156, 7, 11.0),
        ("AZ104", "2025-03-06 12:00:00", "T3", 52, 4, 9.0),
        ("VY100", "2025-03-06 14:45:00", "T4", 61, 4, 8.0),
        ("DY1234", "2025-03-06 12:30:00", "T2", 89, 4, 16.0),
        ("DY1234", "2025-03-06 13:00:00", "T2", 112, 5, 13.5),
        ("EK2", "2025-03-06 05:30:00", "T3", 145, 8, 18.0),
        ("EK2", "2025-03-06 06:00:00", "T3", 198, 8, 22.0),
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO passenger_flow
           (flight_id, time, terminal, passengers_arriving_security, open_lanes, queue_time)
           VALUES (?, ?, ?, ?, ?, ?)""",
        passenger_flow,
    )

    # Alerts
    alerts = [
        ("2025-03-06 06:00:00", "security", "T5 North security queue above threshold.", "warning"),
        ("2025-03-06 07:22:00", "flight", "BA301 boarding started at gate A12.", "info"),
        ("2025-03-06 08:15:00", "capacity", "Terminal 2 peak flow; consider opening additional lanes.", "warning"),
        ("2025-03-06 09:00:00", "flight", "KL1008 delayed 45 min — technical check.", "warning"),
        ("2025-03-06 09:30:00", "system", "Baggage system B concourse temporary slowdown.", "info"),
        ("2025-03-06 10:00:00", "flight", "TP448 Lisbon–Madrid cancelled; rebooking offered.", "critical"),
        ("2025-03-06 11:00:00", "security", "All security lanes operational across terminals.", "info"),
        ("2025-03-06 06:15:00", "flight", "EI164 departed on time from gate B3.", "info"),
        ("2025-03-06 07:45:00", "weather", "Light fog expected until 09:00; no impact on operations.", "info"),
        ("2025-03-06 08:00:00", "capacity", "T1 security wait time under 10 min.", "info"),
        ("2025-03-06 09:45:00", "flight", "LH902 now boarding at gate A8.", "info"),
        ("2025-03-06 10:30:00", "security", "Extra lane opened at T5 for BA178.", "info"),
        ("2025-03-06 11:30:00", "system", "Wi‑Fi upgrade completed in T2.", "info"),
        ("2025-03-06 12:00:00", "capacity", "T4 flow normal; queue time 5–7 min.", "info"),
        ("2025-03-06 13:15:00", "flight", "Gate change: AZ104 now at A3 (was A5).", "warning"),
        ("2025-03-06 14:00:00", "maintenance", "Escalator A15–A16 out of service; use lift.", "warning"),
        ("2025-03-06 15:00:00", "flight", "AF1742 check-in closing in 45 min.", "info"),
        ("2025-03-06 16:00:00", "security", "T4 South lane closed for 20 min — staff break.", "warning"),
        ("2025-03-06 17:00:00", "flight", "KL1832 boarding delayed 15 min.", "warning"),
        ("2025-03-06 18:00:00", "capacity", "Evening peak starting; T5 and T2 busiest.", "info"),
        ("2025-03-06 19:00:00", "security", "All terminals operating normally.", "info"),
    ]
    cur.executemany(
        """INSERT INTO alerts (time, type, message, severity) VALUES (?, ?, ?, ?)""",
        alerts,
    )

    conn.commit()


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        seed(conn)
    print("Seed data loaded into airport.db")


if __name__ == "__main__":
    main()
