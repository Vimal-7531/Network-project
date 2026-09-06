from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RISK_PATH = (
    PROJECT_ROOT
    / "data"
    / "analytics"
    / "network_risk_scores"
)

ANOMALY_PATH = (
    PROJECT_ROOT
    / "phase6"
    / "ml"
    / "ml4_output"
    / "network_anomaly_scores.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "phase6"
    / "ml"
    / "ml6_output"
    / "top20_operational_attention_report.csv"
)


def main():
    if not RISK_PATH.exists():
        raise FileNotFoundError(
            f"ML6 risk scores not found: {RISK_PATH}"
        )

    if not ANOMALY_PATH.exists():
        raise FileNotFoundError(
            f"ML4 anomaly scores not found: {ANOMALY_PATH}"
        )

    risk = pd.read_parquet(RISK_PATH)

    anomaly = pd.read_csv(ANOMALY_PATH)

    required_risk_columns = [
        "grid_id",
        "timestamp",
        "risk_score",
        "risk_level",
        "model_version"
    ]

    missing_risk = [
        column
        for column in required_risk_columns
        if column not in risk.columns
    ]

    if missing_risk:
        raise ValueError(
            f"ML6 risk scores are missing columns: {missing_risk}"
        )

    required_anomaly_columns = [
        "grid_id",
        "timestamp",
        "anomaly_score",
        "direction",
        "reason"
    ]

    missing_anomaly = [
        column
        for column in required_anomaly_columns
        if column not in anomaly.columns
    ]

    if missing_anomaly:
        raise ValueError(
            f"ML4 anomaly scores are missing columns: {missing_anomaly}"
        )

    risk["timestamp"] = pd.to_datetime(
        risk["timestamp"]
    )

    anomaly["timestamp"] = pd.to_datetime(
        anomaly["timestamp"]
    )

    anomaly["match_date"] = anomaly["timestamp"].dt.date
    anomaly["match_hour"] = anomaly["timestamp"].dt.hour

    risk["match_date"] = risk["timestamp"].dt.date
    risk["match_hour"] = risk["timestamp"].dt.hour

    anomaly = anomaly[
        [
            "grid_id",
            "match_date",
            "match_hour",
            "anomaly_score",
            "direction",
            "reason"
        ]
    ]

    merged = risk.merge(
        anomaly,
        on=[
            "grid_id",
            "match_date",
            "match_hour"
        ],
        how="left"
    )

    merged["anomaly_score"] = (
        merged["anomaly_score"]
        .fillna(0.0)
    )

    merged["direction"] = (
        merged["direction"]
        .fillna("NO_ANOMALY_RECORD")
    )

    merged["reason"] = (
        merged["reason"]
        .fillna(
            "No ML4 anomaly record is available for this grid and hour."
        )
    )

    merged["attention_score"] = (
        merged["risk_score"].clip(lower=0.0)
        + merged["anomaly_score"].abs().clip(lower=0.0)
    )

    merged = merged.sort_values(
        [
            "attention_score",
            "risk_score",
            "anomaly_score"
        ],
        ascending=False
    )

    top20 = merged.head(20).copy()

    top20.insert(
        0,
        "rank",
        range(1, len(top20) + 1)
    )

    top20["attention_reason"] = top20.apply(
        lambda row: (
            f"Investigate grid {int(row['grid_id'])}: "
            f"predicted activity risk is "
            f"{row['risk_score']:.4f} "
            f"({row['risk_level']}). "
            f"ML4 status is {row['direction']} "
            f"with anomaly score "
            f"{row['anomaly_score']:.4f}. "
            f"{row['reason']}"
        ),
        axis=1
    )

    top20 = top20[
        [
            "rank",
            "grid_id",
            "timestamp",
            "risk_score",
            "risk_level",
            "model_version",
            "direction",
            "anomaly_score",
            "attention_score",
            "attention_reason"
        ]
    ]

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    top20.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(
        f"Top-20 operational attention report created."
    )

    print(
        f"Rows: {len(top20)}"
    )

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print()

    print(
        top20[
            [
                "rank",
                "grid_id",
                "timestamp",
                "risk_score",
                "risk_level",
                "direction",
                "anomaly_score"
            ]
        ].to_string(index=False)
    )

    return 0


if __name__ == "__main__":
    main()