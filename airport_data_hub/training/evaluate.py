"""
Evaluation script: load holdout data and trained model, compute metrics.
Run from repo root: python -m airport_data_hub.training.evaluate --data path/to/holdout.csv [--model path]
"""
import argparse
from pathlib import Path

import numpy as np
import joblib

from airport_data_hub.training.train import load_training_data, prepare_features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to holdout CSV")
    parser.add_argument("--model", type=str, default=None, help="Path to joblib model")
    args = parser.parse_args()

    model_path = Path(args.model) if args.model else Path(__file__).resolve().parent.parent / "models" / "delay_model.joblib"
    if not model_path.exists():
        print("No model found at", model_path)
        return

    artifact = joblib.load(model_path)
    model = artifact.get("model", artifact)
    df = load_training_data(args.data)
    X, y = prepare_features(df)

    y_pred = model.predict(X)
    mae = np.mean(np.abs(y - y_pred))
    rmse = np.sqrt(np.mean((y - y_pred) ** 2))
    within_5 = np.mean(np.abs(y - y_pred) <= 5) * 100
    within_10 = np.mean(np.abs(y - y_pred) <= 10) * 100
    print(f"MAE={mae:.2f} min, RMSE={rmse:.2f}")
    print(f"Within 5 min: {within_5:.1f}%, Within 10 min: {within_10:.1f}%")


if __name__ == "__main__":
    main()
