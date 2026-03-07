"""
Build the unified airport operations snapshot for GET /overview.
Combines key data from all hub entities for dashboard and downstream modules.
"""
from collections import Counter
from sqlalchemy.orm import Session

from ..crud import (
    get_flights,
    get_passenger_flows,
    get_runways,
    get_alerts,
    get_resources,
    get_infrastructure_assets,
    get_passenger_services,
    get_digital_identity_statuses,
    get_retail_events,
)
from ..schemas import (
    OverviewResponse,
    FlightResponse,
    PassengerFlowResponse,
    RunwayResponse,
    AlertResponse,
    ResourceResponse,
    InfrastructureAssetResponse,
    PassengerServiceResponse,
    DigitalIdentityStatusResponse,
    RetailEventResponse,
)


def _to_flight_response(f):
    return FlightResponse.model_validate(f)


def _to_passenger_flow_response(pf):
    return PassengerFlowResponse(
        id=pf.id,
        flight_id=pf.flight_id,
        check_in_count=pf.check_in_count,
        security_queue_count=pf.security_queue_count,
        boarding_count=pf.boarding_count,
        predicted_queue_time=pf.predicted_queue_time,
        terminal_zone=pf.terminal_zone,
        timestamp=pf.timestamp,
    )


def _to_runway_response(r):
    return RunwayResponse(
        id=r.id,
        runway_code=r.runway_code,
        status=r.status,
        surface_condition=r.surface_condition,
        contamination_level=r.contamination_level,
        grip_score=r.grip_score,
        hazard_detected=r.hazard_detected,
        hazard_type=r.hazard_type,
        last_inspection_time=r.last_inspection_time,
    )


def _to_alert_response(a):
    return AlertResponse(
        id=a.id,
        alert_type=a.alert_type,
        severity=a.severity,
        source_module=a.source_module,
        message=a.message,
        related_entity_type=a.related_entity_type,
        related_entity_id=a.related_entity_id,
        created_at=a.created_at,
        resolved=a.resolved,
    )


def _to_resource_response(r):
    return ResourceResponse(
        id=r.id,
        resource_name=r.resource_name,
        resource_type=r.resource_type,
        status=r.status,
        assigned_to=r.assigned_to,
        location=r.location,
    )


def _to_infrastructure_response(a):
    return InfrastructureAssetResponse(
        id=a.id,
        asset_name=a.asset_name,
        asset_type=a.asset_type,
        status=a.status,
        network_health=a.network_health,
        tamper_detected=a.tamper_detected,
        location=a.location,
        last_updated=a.last_updated,
    )


def _to_service_response(s):
    return PassengerServiceResponse(
        id=s.id,
        passenger_reference=s.passenger_reference,
        service_type=s.service_type,
        status=s.status,
        request_time=s.request_time,
        completion_time=s.completion_time,
        location=s.location,
    )


def _to_identity_response(i):
    return DigitalIdentityStatusResponse(
        id=i.id,
        passenger_reference=i.passenger_reference,
        verification_status=i.verification_status,
        verification_method=i.verification_method,
        last_verified_at=i.last_verified_at,
        token_reference=i.token_reference,
    )


def _to_retail_response(e):
    return RetailEventResponse(
        id=e.id,
        passenger_reference=e.passenger_reference,
        offer_type=e.offer_type,
        order_status=e.order_status,
        pickup_gate=e.pickup_gate,
        created_at=e.created_at,
    )


def get_overview(db: Session) -> OverviewResponse:
    """Single snapshot of current flights, queues, runways, alerts, resources, infrastructure, services, identity counts, retail."""
    flights = get_flights(db, limit=50)
    flows = get_passenger_flows(db, limit=100)
    runways = get_runways(db)
    alerts = get_alerts(db, resolved=False, limit=50)
    resources = get_resources(db, limit=100)
    assets = get_infrastructure_assets(db)
    services = get_passenger_services(db, limit=50)
    identities = get_digital_identity_statuses(db, limit=500)
    retail = get_retail_events(db, limit=50)

    identity_counts = Counter(i.verification_status for i in identities)

    return OverviewResponse(
        current_flights=[_to_flight_response(f) for f in flights],
        passenger_queues=[_to_passenger_flow_response(pf) for pf in flows],
        runway_conditions=[_to_runway_response(r) for r in runways],
        active_alerts=[_to_alert_response(a) for a in alerts],
        resource_status=[_to_resource_response(r) for r in resources],
        infrastructure_status=[_to_infrastructure_response(a) for a in assets],
        service_requests=[_to_service_response(s) for s in services],
        identity_verification_counts=dict(identity_counts),
        retail_activity=[_to_retail_response(e) for e in retail],
    )
