# Airport Intelligence Platform – AI-Native AODB MVP

Focused on the **AI-Native AODB** hackathon challenge: a predictive, self-healing flight data layer. The **Airport Data Hub** (FastAPI + SQLite) is the central backbone and is being extended step by step.

---

## Quick start

```bash
# From repo root
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Seed the hub DB
python -m airport_data_hub.seed

# Run the Data Hub API
uvicorn airport_data_hub.main:app --reload
# Or: python airport_data_hub/run.py
```

- API: **http://127.0.0.1:8000**
- Docs: **http://127.0.0.1:8000/docs**
- Unified snapshot: **http://127.0.0.1:8000/overview**

DB file: `airport_data_hub/airport_hub.db` (override with env `AIRPORT_HUB_DB`).

---

## Airport Data Hub layout

```
airport_data_hub/
  main.py           # FastAPI app (hub + prediction in one)
  database.py       # SQLAlchemy engine, session, init_db
  models.py         # ORM: Flight, FlightUpdate, PredictionAudit, PassengerFlow, Runways, etc.
  schemas.py        # Pydantic request/response
  crud.py           # Data access + prediction audit CRUD
  seed.py           # Demo data
  prediction/       # Arrival delay: features, inference, config
  training/         # train.py, evaluate.py (model → models/delay_model.joblib)
  routes/           # flights, flight_updates, prediction, aodb, overview, ...
  airport_hub.db    # SQLite (created by seed)
```

---

## AI-Native AODB + Arrival Delay Prediction (single server)

**One process** runs both the Data Hub and arrival delay prediction. No separate prediction service to host.

- **Flight**: schedule + reconciliation fields and **prediction fields** (`predicted_arrival_delay_min`, `prediction_confidence`, `prediction_model_version`, `last_prediction_at`).
- **AODB**: `GET /aodb/flights`, `GET /aodb/flights/{id}`, `GET /aodb/overview`.
- **Prediction** (same server):  
  - `POST /predict` with `{"flight_id": 1}` → runs model (or stub), stores audit in hub DB, updates the flight; returns delay, confidence, reason codes.  
  - `GET /predictions` — recent predictions; `GET /predictions/flights/{id}` — history for a flight.
- **Training** (optional): `python -m airport_data_hub.training.train` [--data csv] [--model ridge|gbm] writes `airport_data_hub/models/delay_model.joblib`. Without a trained model, the hub uses a stub predictor.
