"""Config for arrival delay prediction (model path under hub)."""
import os
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = HUB_ROOT / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "delay_model.joblib"
MODEL_VERSION = os.environ.get("ARRIVAL_DELAY_MODEL_VERSION", "v1.0.0-baseline")
REASON_CODES_TOP_K = int(os.environ.get("REASON_CODES_TOP_K", "5"))

# Feature freshness & self-healing (TODO: move to env/settings in production)
MAX_UPDATE_AGE_HOURS = float(os.environ.get("PREDICTION_MAX_UPDATE_AGE_HOURS", "2.0"))
MIN_INPUT_QUALITY_FOR_ML = float(os.environ.get("PREDICTION_MIN_INPUT_QUALITY_FOR_ML", "0.3"))
REQUIRED_FEATURES_FOR_ML = ["scheduled_departure", "scheduled_arrival", "origin", "destination", "airline"]

# Training
RANDOM_STATE = 42
TEST_SIZE = 0.2
VALIDATION_SIZE = 0.1
