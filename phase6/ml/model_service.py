from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "phase6"
    / "ml"
    / "ml3_output"
    / "logistic_regression_model.joblib"
)

FEATURE_COLUMNS = [
    "avg_activity",
    "activity_growth",
    "active_hours",
    "peak_ratio",
    "variability",
    "internet_share"
]

MODEL_VERSION = "ml3-logistic-regression-v1"


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"ML model artifact not found: {MODEL_PATH}"
        )

    model = joblib.load(MODEL_PATH)

    if not hasattr(model, "predict_proba"):
        raise ValueError(
            "Loaded model does not support probability prediction."
        )

    if hasattr(model, "feature_names_in_"):
        model_features = list(model.feature_names_in_)

        if model_features != FEATURE_COLUMNS:
            raise ValueError(
                f"Model feature mismatch. "
                f"Expected {FEATURE_COLUMNS}, "
                f"found {model_features}"
            )

    return model


model = load_model()


def predict_risk(features):
    missing_features = [
        feature
        for feature in FEATURE_COLUMNS
        if feature not in features
    ]

    if missing_features:
        raise ValueError(
            f"Missing model features: {missing_features}"
        )

    input_data = pd.DataFrame(
        [[features[feature] for feature in FEATURE_COLUMNS]],
        columns=FEATURE_COLUMNS
    )

    risk_score = float(
        model.predict_proba(input_data)[0][1]
    )

    if risk_score >= 0.66:
        risk_level = "HIGH"
    elif risk_score >= 0.33:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "model_version": MODEL_VERSION
    }