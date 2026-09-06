from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FEATURE_PATH = (
    PROJECT_ROOT
    / "data"
    / "analytics"
    / "network_feature_table"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "analytics"
    / "network_risk_scores"
)

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


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"ML model artifact not found: {MODEL_PATH}"
        )

    if not FEATURE_PATH.exists():
        raise FileNotFoundError(
            f"ML2 feature table not found: {FEATURE_PATH}"
        )

    model = joblib.load(MODEL_PATH)

    if not hasattr(model, "predict_proba"):
        raise ValueError(
            "Loaded model does not support probability prediction."
        )

    features = pd.read_parquet(FEATURE_PATH)

    if features.empty:
        raise RuntimeError(
            "ML2 feature table is empty. Scoring cannot continue."
        )

    required_columns = [
        "grid_id",
        "feature_timestamp",
        *FEATURE_COLUMNS
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in features.columns
    ]

    if missing_columns:
        raise ValueError(
            f"ML2 feature table is missing columns: {missing_columns}"
        )

    if features[
        ["grid_id", "feature_timestamp"]
    ].duplicated().any():
        raise ValueError(
            "Duplicate grid_id and feature_timestamp records found."
        )

    model_input = features[FEATURE_COLUMNS].copy()

    probabilities = model.predict_proba(model_input)[:, 1]

    risk_scores = pd.DataFrame(
        {
            "grid_id": features["grid_id"].astype(int),
            "timestamp": pd.to_datetime(
                features["feature_timestamp"]
            ),
            "risk_score": probabilities,
            "risk_level": pd.Series(probabilities).map(
                lambda score: (
                    "HIGH"
                    if score >= 0.66
                    else "MEDIUM"
                    if score >= 0.33
                    else "LOW"
                )
            ),
            "model_version": MODEL_VERSION
        }
    )

    if risk_scores[
        ["grid_id", "timestamp"]
    ].duplicated().any():
        raise ValueError(
            "Duplicate records detected in network_risk_scores."
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if OUTPUT_PATH.exists():
        if OUTPUT_PATH.is_dir():
            import shutil
            shutil.rmtree(OUTPUT_PATH)
        else:
            OUTPUT_PATH.unlink()

    risk_scores.to_parquet(
        OUTPUT_PATH,
        index=False
    )

    print(
        f"ML6 scoring completed. "
        f"Rows scored: {len(risk_scores)}"
    )

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print(
        f"Model version: {MODEL_VERSION}"
    )

    print(
        risk_scores["risk_level"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    return 0


if __name__ == "__main__":
    main()