"""
Training script for arrival delay prediction (v1 baseline).
Saves joblib to airport_data_hub/models/delay_model.joblib.
Run from repo root: python -m airport_data_hub.training.train [--data path] [--model ridge|gbm]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from airport_data_hub.prediction.config import MODELS_DIR, RANDOM_STATE, TEST_SIZE, MODEL_VERSION

FEATURE_NAMES = [
    "hours_until_scheduled_departure",
    "delay_at_origin_min",
    "hour_of_day",
    "day_of_week",
    "airline_enc",
    "origin_enc",
    "destination_enc",
    "reported_status_enc",
]


def load_training_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    for col in ["airline_enc", "origin_enc", "destination_enc", "reported_status_enc"]:
        if col not in df.columns:
            base = col.replace("_enc", "")
            if base in df.columns:
                df[col] = df[base].astype(str).map(lambda x: hash(x) % 10000 / 10000.0)
            else:
                df[col] = 0.0
    X = df[[c for c in FEATURE_NAMES if c in df.columns]]
    for c in FEATURE_NAMES:
        if c not in X.columns:
            X[c] = 0.0
    X = X[FEATURE_NAMES].fillna(0).values
    y = df["arrival_delay_min"].values if "arrival_delay_min" in df.columns else np.zeros(len(df))
    return X, y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default=None, help="Path to training CSV (optional)")
    parser.add_argument("--model", type=str, default="ridge", choices=["ridge", "gbm"])
    parser.add_argument("--out", type=str, default=None, help="Output path for joblib")
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else MODELS_DIR / "delay_model.joblib"

    if args.data and Path(args.data).exists():
        df = load_training_data(args.data)
        X, y = prepare_features(df)
    else:
        n = 500
        np.random.seed(RANDOM_STATE)
        X = np.random.randn(n, len(FEATURE_NAMES)).astype(np.float32)
        X[:, 1] = np.clip(X[:, 1], -30, 120)
        y = 0.9 * X[:, 1] + 0.1 * X[:, 0] + np.random.randn(n) * 5
        y = np.clip(y, -30, 180)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    if args.model == "ridge":
        model = Ridge(alpha=1.0, random_state=RANDOM_STATE)
    else:
        model = GradientBoostingRegressor(n_estimators=50, max_depth=4, random_state=RANDOM_STATE)

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    print(f"MAE={mae:.2f} min, RMSE={rmse:.2f}, R2={r2:.3f}")

    artifact = {"model": model, "feature_names": FEATURE_NAMES, "version": MODEL_VERSION}
    joblib.dump(artifact, out_path)
    print(f"Saved model to {out_path}")


if __name__ == "__main__":
    main()
