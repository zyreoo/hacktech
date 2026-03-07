# Airport Data Hub (challenge)

**Problem:** Legacy systems don’t talk to each other; every new digital initiative stalls on integration, and there’s no single source of operational truth.

**Challenge:** Build connectors + a canonical data model that normalizes flights, resources, and events into clean APIs any app can use.

This folder contains the DB (SQLite), SQLAlchemy models, Pydantic schemas, CRUD, FastAPI routes, rules-based intelligence, and seed data. Run from repo root:

```bash
python -m airport_data_hub.seed
uvicorn airport_data_hub.main:app --reload
# or: python run_hub.py
```

See repo root **README.md** for API summary and `/overview` usage.
