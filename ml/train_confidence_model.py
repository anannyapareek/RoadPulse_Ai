"""
ml/train_confidence_model.py

Trains the RandomForest confidence model from labeled incident history
and saves it to ml/confidence_model.joblib.

Requires a view `incident_training_view` in the DB (defined in
migrations/schema_updates.sql). The view selects only CONFIRMED/REJECTED
incidents so there's a clear ground-truth label.

Run manually or on a schedule as more labeled data accumulates:
    python ml/train_confidence_model.py
"""

import os
import sys
import sqlite3
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# Resolve paths relative to this file's location
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("ROADPULSE_DB_PATH", os.path.join(_HERE, "..", "instance", "roadpulse.db"))
MODEL_OUT = os.path.join(_HERE, "confidence_model.joblib")
MIN_ROWS = 50  # minimum labeled rows before training is meaningful

FEATURE_COLUMNS = [
    "base_score",
    "gps_accuracy_factor",
    "duplicate_factor",
    "device_trust_score",
    "hour_of_day",
    "image_validation_passed",
    "incident_type_code",
]
TARGET_COLUMN = "confirmed_valid"  # 1.0 if the report was later confirmed, else 0.0


def load_training_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT {', '.join(FEATURE_COLUMNS)}, {TARGET_COLUMN}
        FROM incident_training_view
        WHERE {TARGET_COLUMN} IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def train():
    df = load_training_data()
    print(f"Loaded {len(df)} labeled rows from {DB_PATH}")

    if len(df) < MIN_ROWS:
        print(
            f"⚠️  Only {len(df)} labeled rows found -- need at least {MIN_ROWS} before training "
            "a meaningful model. Keep using the legacy formula fallback until more incidents "
            "are confirmed/rejected."
        )
        sys.exit(0)

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"Validation MAE: {mae:.4f}  ({len(X_test)} held-out rows)")

    # Feature importance for quick sanity check
    importances = sorted(zip(FEATURE_COLUMNS, model.feature_importances_), key=lambda x: x[1], reverse=True)
    print("Feature importances:")
    for feat, imp in importances:
        print(f"  {feat:30s} {imp:.4f}")

    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    joblib.dump(model, MODEL_OUT)
    print(f"✅ Saved model to {MODEL_OUT}")
    print("   Reload with: from app.utils.scoring import reload_model; reload_model()")


if __name__ == "__main__":
    train()
