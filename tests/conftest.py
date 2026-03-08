"""
Pytest configuration and fixtures for Airport Data Hub API tests.
Set TESTING and a dedicated test DB before any app imports.
"""
import os
import tempfile

import pytest

# Must run before any import that loads database.py
os.environ["TESTING"] = "1"
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_test_db = os.path.join(_tests_dir, "airport_hub_test.db")
if os.path.exists(_test_db):
    try:
        os.remove(_test_db)
    except OSError:
        pass
os.environ["AIRPORT_HUB_DB"] = _test_db

from fastapi.testclient import TestClient

from airport_data_hub.database import init_db
from airport_data_hub.main import app
from airport_data_hub.seed import seed

# Ensure tables and seed data exist before any request
init_db()
seed()


def get_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def client():
    return get_client()
