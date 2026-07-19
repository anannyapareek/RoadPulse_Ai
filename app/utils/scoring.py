"""
app/utils/scoring.py

Confidence scoring for RoadPulse AI incidents.
Replaces the old hard-coded formula:
    base_score * gps_accuracy_factor * duplicate_factor
with a trained RandomForest model, while keeping the same public
function signatures so callers in app.py don't break.

If no trained model is found on disk, this falls back to the original
formula automatically -- so nothing breaks before a model is trained.
"""

import os
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "confidence_model.joblib")

_model = None

# Feature order must match the training script (train_confidence_model.py)
_feature_order = [
    "base_score",
    "gps_accuracy_factor",
    "duplicate_factor",
    "device_trust_score",
    "hour_of_day",
    "image_validation_passed",   # 1.0 / 0.0
    "incident_type_code",        # pre-encoded integer, see encode_incident_type()
]

INCIDENT_TYPE_CODES = {
    "pothole": 0,
    "accident": 1,
    "flooding": 2,
    "debris": 3,
    "signal_outage": 4,
    "congestion": 5,
    "crack": 6,
    "other": 7,
}


def encode_incident_type(incident_type: str) -> int:
    return INCIDENT_TYPE_CODES.get((incident_type or "other").lower(), INCIDENT_TYPE_CODES["other"])


def _load_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        import joblib
        _model = joblib.load(MODEL_PATH)
    return _model


def _legacy_formula(base_score: float, gps_accuracy_factor: float, duplicate_factor: float) -> float:
    """Original formula, kept as a safe fallback."""
    return base_score * gps_accuracy_factor * duplicate_factor


def _features_to_vector(features: dict) -> "np.ndarray":
    row = [features.get(name, 0.0) for name in _feature_order]
    return np.array(row, dtype=float).reshape(1, -1)


def predict_confidence(features: dict) -> float:
    """
    Predict a confidence score in [0, 1] for an incident report.

    features dict expected keys (missing keys default to 0.0):
        base_score, gps_accuracy_factor, duplicate_factor,
        device_trust_score, hour_of_day, image_validation_passed,
        incident_type_code  (use encode_incident_type() to build this)

    Returns a float confidence score. Falls back to the legacy formula
    if no trained model is available yet.
    """
    model = _load_model()

    if model is None:
        return float(np.clip(
            _legacy_formula(
                features.get("base_score", 1.0),
                features.get("gps_accuracy_factor", 1.0),
                features.get("duplicate_factor", 1.0),
            ),
            0.0, 1.0
        ))

    x = _features_to_vector(features)
    # RandomForestRegressor -> predict() gives continuous score directly.
    # If you trained a RandomForestClassifier instead, swap to predict_proba()[:, 1].
    score = model.predict(x)[0]
    return float(np.clip(score, 0.0, 1.0))


def reload_model():
    """Call after retraining so the running Flask process picks up the new model."""
    global _model
    _model = None
    return _load_model()


# ──────────────────────────────────────────────────────────────────
# Legacy compatibility shim: the original app.py calls compute_confidence()
# with (gemini_confidence, gps_accuracy, is_duplicate). We keep that
# signature working so app.py does not need to change.
# ──────────────────────────────────────────────────────────────────

def _gps_accuracy_factor(gps_accuracy: float) -> float:
    return max(0.5, min(1.0, 100.0 / max(gps_accuracy, 1.0)))


def compute_confidence(
    gemini_confidence: float,
    gps_accuracy: float = 25.0,
    is_duplicate: bool = False,
    device_id: str = None,
    incident_type: str = "other"
) -> float:
    """
    Compute final confidence score for an incident report.

    Wraps predict_confidence() with the original call signature so
    existing callers in app.py work without modification.

    When a trained RF model exists, it also incorporates device trust score,
    time-of-day, and image_validation_passed; these default gracefully.
    """
    from datetime import datetime

    gps_factor = _gps_accuracy_factor(gps_accuracy)
    dup_factor = 0.7 if is_duplicate else 1.0

    trust_score = 0.5
    if device_id:
        try:
            from app.utils.trust_score import get_trust_score
            trust_score = get_trust_score(device_id)
        except Exception:
            pass

    features = {
        "base_score": float(np.clip(gemini_confidence, 0.0, 1.0)),
        "gps_accuracy_factor": gps_factor,
        "duplicate_factor": dup_factor,
        "device_trust_score": trust_score,
        "hour_of_day": datetime.utcnow().hour,
        "image_validation_passed": 1.0,  # called only after Gemini accepted the image
        "incident_type_code": encode_incident_type(incident_type),
    }
    return predict_confidence(features)


def get_severity_ordinal(severity: str) -> int:
    """Get numeric ordinal for severity level (for sorting)."""
    severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    return severity_map.get(severity.lower(), 0)


def get_severity_color(severity: str) -> str:
    """Get color code for severity level (for UI display)."""
    color_map = {
        "low": "#FFC107",
        "medium": "#FF9800",
        "high": "#F44336",
        "critical": "#C62828",
    }
    return color_map.get(severity.lower(), "#9E9E9E")
