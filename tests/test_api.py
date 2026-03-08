"""
Comprehensive API tests for Airport Data Hub.
Run from repo root: pytest tests/ -v
"""
import pytest


# ---- Root & docs ----
def test_root_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "overview" in data


# ---- Overview ----
def test_overview_returns_200(client):
    r = client.get("/overview")
    assert r.status_code == 200


def test_overview_has_required_keys(client):
    r = client.get("/overview")
    assert r.status_code == 200
    data = r.json()
    for key in ("current_flights", "active_alerts", "runway_conditions", "resource_status",
                "passenger_queues", "infrastructure_status", "service_requests"):
        assert key in data, f"missing key: {key}"


def test_overview_active_alerts_is_list(client):
    r = client.get("/overview")
    assert r.status_code == 200
    assert isinstance(r.json().get("active_alerts"), list)


def test_overview_current_flights_is_list(client):
    r = client.get("/overview")
    assert r.status_code == 200
    assert isinstance(r.json().get("current_flights"), list)


# ---- AODB ----
def test_aodb_flights_returns_200(client):
    r = client.get("/aodb/flights")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_aodb_overview_returns_200(client):
    r = client.get("/aodb/overview")
    assert r.status_code == 200


# ---- Flights ----
def test_flights_list_returns_200(client):
    r = client.get("/flights")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_flights_list_accepts_skip_limit(client):
    r = client.get("/flights?skip=0&limit=5")
    assert r.status_code == 200
    assert len(r.json()) <= 5


def test_flights_issues_returns_200(client):
    r = client.get("/flights/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_flights_get_by_id_returns_200_when_exists(client):
    # Seed creates flights; get first id from list
    list_r = client.get("/flights?limit=1")
    assert list_r.status_code == 200
    flights = list_r.json()
    if flights:
        fid = flights[0]["id"]
        r = client.get(f"/flights/{fid}")
        assert r.status_code == 200
        assert r.json()["id"] == fid


def test_flights_get_by_id_returns_404_when_not_exists(client):
    r = client.get("/flights/999999")
    assert r.status_code == 404


def test_flights_reassign_accepts_gate(client):
    list_r = client.get("/flights?limit=1")
    assert list_r.status_code == 200
    flights = list_r.json()
    if not flights:
        pytest.skip("no flights from seed")
    fid = flights[0]["id"]
    r = client.patch(f"/flights/{fid}/reassign", json={"gate": "A13", "reconciled_gate": "A13"})
    assert r.status_code == 200
    assert r.json().get("gate") == "A13" or r.json().get("reconciled_gate") == "A13"


# ---- Alerts ----
def test_alerts_list_returns_200(client):
    r = client.get("/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_alerts_list_filter_resolved(client):
    r = client.get("/alerts?resolved=false")
    assert r.status_code == 200
    for a in r.json():
        assert a["resolved"] is False


def test_alerts_issues_returns_200(client):
    r = client.get("/alerts/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_alerts_resolve_returns_200(client):
    list_r = client.get("/alerts?resolved=false&limit=1")
    assert list_r.status_code == 200
    alerts = list_r.json()
    if not alerts:
        pytest.skip("no active alerts")
    aid = alerts[0]["id"]
    r = client.patch(f"/alerts/{aid}/resolve", json={"resolved": True})
    assert r.status_code == 200
    assert r.json()["resolved"] is True


def test_alerts_resolve_404_for_invalid_id(client):
    r = client.patch("/alerts/999999/resolve", json={"resolved": True})
    assert r.status_code == 404


def test_alerts_get_by_id_returns_200_when_exists(client):
    list_r = client.get("/alerts?limit=1")
    assert list_r.status_code == 200
    alerts = list_r.json()
    if alerts:
        aid = alerts[0]["id"]
        r = client.get(f"/alerts/{aid}")
        assert r.status_code == 200
        assert r.json()["id"] == aid


# ---- Runways ----
def test_runways_list_returns_200(client):
    r = client.get("/runways")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_runways_issues_returns_200(client):
    r = client.get("/runways/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_runways_patch_status(client):
    list_r = client.get("/runways")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no runways")
    rid = list_r.json()[0]["id"]
    r = client.patch(f"/runways/{rid}/status", json={"status": "active"})
    assert r.status_code == 200


# ---- Resources ----
def test_resources_list_returns_200(client):
    r = client.get("/resources")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_resources_issues_returns_200(client):
    r = client.get("/resources/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_resources_patch_status(client):
    list_r = client.get("/resources?limit=1")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no resources")
    rid = list_r.json()[0]["id"]
    r = client.patch(f"/resources/{rid}/status", json={"status": "available", "assigned_to": None})
    assert r.status_code == 200


# ---- Passenger flow ----
def test_passenger_flow_list_returns_200(client):
    r = client.get("/passenger-flow")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_passenger_flow_issues_returns_200(client):
    r = client.get("/passenger-flow/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---- Predictions ----
def test_predictions_list_returns_200(client):
    r = client.get("/predictions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_predictions_issues_returns_200(client):
    r = client.get("/predictions/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_predict_post_returns_200(client):
    list_r = client.get("/flights?limit=1")
    assert list_r.status_code == 200
    flights = list_r.json()
    if not flights:
        pytest.skip("no flights")
    fid = flights[0]["id"]
    r = client.post("/predict", json={"flight_id": fid})
    assert r.status_code == 200
    data = r.json()
    assert data["flight_id"] == fid
    assert "predicted_arrival_delay_min" in data
    assert "model_version" in data


def test_predict_returns_404_for_invalid_flight(client):
    r = client.post("/predict", json={"flight_id": 999999})
    assert r.status_code == 404


def test_predictions_for_flight_returns_200(client):
    list_r = client.get("/flights?limit=1")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no flights")
    fid = list_r.json()[0]["id"]
    r = client.get(f"/predictions/flights/{fid}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---- Infrastructure ----
def test_infrastructure_list_returns_200(client):
    r = client.get("/infrastructure")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_infrastructure_issues_returns_200(client):
    r = client.get("/infrastructure/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_infrastructure_patch_status(client):
    list_r = client.get("/infrastructure")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no assets")
    aid = list_r.json()[0]["id"]
    r = client.patch(f"/infrastructure/{aid}/status", json={"status": "operational"})
    assert r.status_code == 200


# ---- Services ----
def test_services_list_returns_200(client):
    r = client.get("/services")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_services_issues_returns_200(client):
    r = client.get("/services/issues")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---- Identity & Retail ----
def test_identity_returns_200(client):
    r = client.get("/identity")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_retail_returns_200(client):
    r = client.get("/retail")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---- Flight updates ----
def test_flight_updates_returns_200(client):
    list_r = client.get("/flights?limit=1")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no flights")
    fid = list_r.json()[0]["id"]
    r = client.get(f"/flights/{fid}/updates")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---- Response shapes (smoke) ----
def test_overview_alert_has_id_and_message(client):
    r = client.get("/overview")
    assert r.status_code == 200
    alerts = r.json().get("active_alerts") or []
    for a in alerts[:3]:
        assert "id" in a
        assert "message" in a
        assert "severity" in a


def test_overview_flight_has_required_fields(client):
    r = client.get("/overview")
    assert r.status_code == 200
    flights = r.json().get("current_flights") or []
    for f in flights[:3]:
        assert "id" in f
        assert "flight_code" in f
        assert "origin" in f
        assert "destination" in f


def test_prediction_response_has_operational_reason_codes(client):
    list_r = client.get("/flights?limit=1")
    if not list_r.json():
        pytest.skip("no flights")
    fid = list_r.json()[0]["id"]
    r = client.post("/predict", json={"flight_id": fid})
    assert r.status_code == 200
    data = r.json()
    assert "reason_codes" in data
    assert "operational_reason_codes" in data or "stale_data_warnings" in data


# ---- Extra coverage ----
def test_alert_get_by_id_404(client):
    r = client.get("/alerts/999999")
    assert r.status_code == 404


def test_runway_get_by_id_returns_200(client):
    list_r = client.get("/runways")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no runways")
    rid = list_r.json()[0]["id"]
    r = client.get(f"/runways/{rid}")
    assert r.status_code == 200
    assert r.json()["id"] == rid


def test_runway_get_by_id_404(client):
    r = client.get("/runways/999999")
    assert r.status_code == 404


def test_resource_get_by_id_returns_200(client):
    list_r = client.get("/resources?limit=1")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no resources")
    rid = list_r.json()[0]["id"]
    r = client.get(f"/resources/{rid}")
    assert r.status_code == 200
    assert r.json()["id"] == rid


def test_resource_get_by_id_404(client):
    r = client.get("/resources/999999")
    assert r.status_code == 404


def test_flight_patch_status(client):
    list_r = client.get("/flights?limit=1")
    assert list_r.status_code == 200
    if not list_r.json():
        pytest.skip("no flights")
    fid = list_r.json()[0]["id"]
    r = client.patch(f"/flights/{fid}/status", json={"status": "delayed"})
    assert r.status_code == 200
    assert r.json().get("status") == "delayed"


def test_overview_resources_is_list(client):
    r = client.get("/overview")
    assert r.status_code == 200
    assert isinstance(r.json().get("resource_status"), list)


def test_predict_response_has_timestamp(client):
    list_r = client.get("/flights?limit=1")
    if not list_r.json():
        pytest.skip("no flights")
    fid = list_r.json()[0]["id"]
    r = client.post("/predict", json={"flight_id": fid})
    assert r.status_code == 200
    assert "prediction_timestamp" in r.json()
