"""
Airport Intelligence Platform - Data Hub API.
Single source of truth for airport operations; all modules plug into this backbone.

Run from repo root:  uvicorn airport_data_hub.main:app --reload
Or from any dir:     python airport_data_hub/run.py   (or  python -m airport_data_hub.run)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from .database import init_db
from .routes import (
    flights, flight_updates, runways, resources, alerts, infrastructure, 
    passenger_flow, services, identity, retail, overview, aodb, prediction,
    passenger_journey, passenger_intelligence, retail_intelligence, passenger_insights,
    infrastructure_monitoring
)
from .prediction import inference
from .services.synthetic import start_synthetic_feeder, stop_synthetic_feeder


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed with demo data when DB is empty so the dashboard and synthetic generator have something to show.
    from .seed import seed
    seed()
    model_path = Path(__file__).parent / "models" / "delay_model.joblib"
    inference.load_model(model_path)
    # Start synthetic data generator in the background so the dashboard always feels live.
    start_synthetic_feeder()
    yield
    # no shutdown needed for SQLite; stop background synthetic feeder
    stop_synthetic_feeder()


app = FastAPI(
    title="Airport Intelligence Platform - Data Hub",
    description="Central data backbone for airport operations. Supports hazard detection, runway grip, machinery security, disruption copilot, resource planning, passenger flow, AODB, satisfaction, navigation, retail, identity.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights.router)
app.include_router(flight_updates.router)
app.include_router(runways.router)
app.include_router(resources.router)
app.include_router(alerts.router)
app.include_router(infrastructure.router)
app.include_router(passenger_flow.router)
app.include_router(services.router)
app.include_router(identity.router)
app.include_router(retail.router)
app.include_router(overview.router)
app.include_router(aodb.router)
app.include_router(prediction.router)
app.include_router(passenger_journey.router)
app.include_router(passenger_intelligence.router)
app.include_router(retail_intelligence.router)
app.include_router(passenger_insights.router)
app.include_router(passenger_flow.router)
app.include_router(infrastructure_monitoring.router)


@app.get("/")
def root():
    return {
        "message": "Airport Intelligence Platform - Data Hub API (AODB + Prediction + Passenger Services + Infrastructure Monitoring + Enhanced Passenger Flow)",
        "docs": "/docs",
        "overview": "/overview",
        "aodb": "/aodb/flights, /aodb/overview",
        "passenger_flow": "/passenger-flow/dashboard/comprehensive",
        "infrastructure_monitoring": "/infrastructure-monitoring/assets",
        "predict": "POST /predict, GET /predictions, GET /predictions/flights/{id}",
        "passenger_journey": "/passenger-journey/*",
        "passenger_intelligence": "/passenger-intelligence/*",
        "retail_intelligence": "/retail-intelligence/*",
        "passenger_insights": "/passenger-insights/*",
        "infrastructure_monitoring": "/infrastructure-monitoring/*",
    }
