"""
app/utils/xai.py

Explainable AI (XAI) layer for the confidence model.
Uses SHAP TreeExplainer on top of the RandomForest from scoring.py
to produce a per-feature breakdown, which gets combined with the
existing Gemini plain-English explanation.
"""

import numpy as np

from app.utils.scoring import _load_model, _features_to_vector, _feature_order

_explainer = None


def _get_explainer():
    global _explainer
    if _explainer is None:
        model = _load_model()
        if model is None:
            return None
        try:
            import shap
            _explainer = shap.TreeExplainer(model)
        except ImportError:
            return None
    return _explainer


def explain_confidence(features: dict, top_n: int = 4) -> dict:
    """
    Returns a structured explanation:
    {
        "available": bool,
        "top_factors": [
            {"feature": "device_trust_score", "impact": 0.12, "direction": "increased"},
            ...
        ]
    }

    "available" is False if no trained model exists yet (legacy formula in use),
    in which case there is nothing to run SHAP against.
    """
    explainer = _get_explainer()
    if explainer is None:
        return {
            "available": False,
            "top_factors": [],
            "note": "No trained model yet; using legacy formula. SHAP will activate after first training run.",
        }

    x = _features_to_vector(features)
    shap_values = explainer.shap_values(x)

    # RandomForestRegressor returns a 2-D array from TreeExplainer; flatten to 1-D
    if hasattr(shap_values, "__len__") and len(shap_values) > 0:
        sv = np.array(shap_values)
        if sv.ndim == 3:
            sv = sv[0][0]  # (n_estimators, n_samples, n_features) -> (n_features,)
        elif sv.ndim == 2:
            sv = sv[0]     # (n_samples, n_features) -> (n_features,)
    else:
        sv = np.array(shap_values)

    ranked = sorted(
        zip(_feature_order, sv),
        key=lambda pair: abs(pair[1]),
        reverse=True,
    )[:top_n]

    top_factors = [
        {
            "feature": name,
            "impact": round(float(value), 4),
            "direction": "increased" if value > 0 else "decreased",
        }
        for name, value in ranked
    ]

    return {"available": True, "top_factors": top_factors}


def combine_with_gemini_reason(shap_explanation: dict, gemini_text: str) -> dict:
    """
    Merges the SHAP structured breakdown with the existing Gemini
    plain-English reasoning into a single response object for
    the admin/audit view.
    """
    return {
        "plain_english": gemini_text,
        "feature_breakdown": shap_explanation.get("top_factors", []),
        "model_backed": shap_explanation.get("available", False),
    }
