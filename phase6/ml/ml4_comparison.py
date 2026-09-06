import os
import pandas as pd

PROJECT_ROOT = r"C:\Users\vimalraj.ck\network_project"

ML4_PATH = os.path.join(
    PROJECT_ROOT,
    "phase6",
    "ml",
    "ml4_output",
    "network_anomaly_scores.csv"
)

ML3_PATH = os.path.join(
    PROJECT_ROOT,
    "phase6",
    "ml",
    "ml3_output",
    "test_dataset.csv"
)

NP3_PATH = os.path.join(
    PROJECT_ROOT,
    "phase6",
    "ml",
    "ml3_output",
    "np3_alerts_all_days.csv"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "phase6",
    "ml",
    "ml4_output"
)

OUTPUT_PATH = os.path.join(
    OUTPUT_DIR,
    "three_way_comparison.csv"
)

def load_ml4():
    df = pd.read_csv(
        ML4_PATH,
        parse_dates=["timestamp"]
    )

    df["ml4_positive"] = df["direction"].isin(
        ["HIGH", "LOW"]
    )

    return df[
        [
            "grid_id",
            "timestamp",
            "total_activity",
            "baseline_activity",
            "deviation",
            "anomaly_score",
            "direction",
            "reason",
            "ml4_positive"
        ]
    ]

def load_ml3():
    df = pd.read_csv(
        ML3_PATH,
        parse_dates=[
            "feature_timestamp",
            "target_timestamp"
        ]
    )

    df["ml3_positive"] = (
        df["high_activity_risk"] == 1
    )

    return df[
        [
            "grid_id",
            "feature_timestamp",
            "target_timestamp",
            "high_activity_risk",
            "ml3_positive"
        ]
    ]

def load_np3():
    df = pd.read_csv(
        NP3_PATH,
        parse_dates=["timestamp"]
    )

    df = df[
        df["alert_type"].isin(
            [
                "HIGH_ACTIVITY",
                "ACTIVITY_SPIKE"
            ]
        )
    ].copy()

    df["np3_positive"] = True

    df = df[
        [
            "grid_id",
            "timestamp",
            "alert_type",
            "np3_positive"
        ]
    ]

    df = df.drop_duplicates(
        subset=["grid_id", "timestamp"]
    )

    return df

def compare():
    ml4 = load_ml4()
    ml3 = load_ml3()
    np3 = load_np3()

    comparison = ml3.merge(
        ml4,
        left_on=[
            "grid_id",
            "feature_timestamp"
        ],
        right_on=[
            "grid_id",
            "timestamp"
        ],
        how="left"
    )

    comparison = comparison.merge(
        np3,
        left_on=[
            "grid_id",
            "feature_timestamp"
        ],
        right_on=[
            "grid_id",
            "timestamp"
        ],
        how="left",
        suffixes=("", "_np3")
    )

    comparison["ml4_positive"] = (
        comparison["ml4_positive"]
        .fillna(False)
        .astype(bool)
    )

    comparison["np3_positive"] = (
        comparison["np3_positive"]
        .fillna(False)
        .astype(bool)
    )

    comparison["three_way_result"] = "ALL_NEGATIVE"

    comparison.loc[
        comparison["ml4_positive"]
        & ~comparison["ml3_positive"]
        & ~comparison["np3_positive"],
        "three_way_result"
    ] = "ML4_ONLY"

    comparison.loc[
        ~comparison["ml4_positive"]
        & comparison["ml3_positive"]
        & ~comparison["np3_positive"],
        "three_way_result"
    ] = "ML3_ONLY"

    comparison.loc[
        ~comparison["ml4_positive"]
        & ~comparison["ml3_positive"]
        & comparison["np3_positive"],
        "three_way_result"
    ] = "NP3_ONLY"

    comparison.loc[
        comparison["ml4_positive"]
        & comparison["ml3_positive"]
        & ~comparison["np3_positive"],
        "three_way_result"
    ] = "ML4_ML3"

    comparison.loc[
        comparison["ml4_positive"]
        & ~comparison["ml3_positive"]
        & comparison["np3_positive"],
        "three_way_result"
    ] = "ML4_NP3"

    comparison.loc[
        ~comparison["ml4_positive"]
        & comparison["ml3_positive"]
        & comparison["np3_positive"],
        "three_way_result"
    ] = "ML3_NP3"

    comparison.loc[
        comparison["ml4_positive"]
        & comparison["ml3_positive"]
        & comparison["np3_positive"],
        "three_way_result"
    ] = "ALL_THREE"

    comparison.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print("\nML4 — Three-Way Comparison")
    print("=" * 50)

    print("\nCOMPARISON PERIOD")
    print(
        f"Earliest: "
        f"{comparison['feature_timestamp'].min()}"
    )
    print(
        f"Latest:   "
        f"{comparison['feature_timestamp'].max()}"
    )

    print("\nRESULT COUNTS")
    print(
        comparison["three_way_result"]
        .value_counts()
        .to_string()
    )

    print("\nPOSITIVE COUNTS")
    print(
        f"ML4 positive: "
        f"{comparison['ml4_positive'].sum()}"
    )

    print(
        f"ML3 positive: "
        f"{comparison['ml3_positive'].sum()}"
    )

    print(
        f"NP3 positive: "
        f"{comparison['np3_positive'].sum()}"
    )

    print("\nTOP HIGH ANOMALIES")

    high = comparison[
        comparison["direction"] == "HIGH"
    ].sort_values(
        "anomaly_score",
        ascending=False
    )

    print(
        high[
            [
                "grid_id",
                "feature_timestamp",
                "total_activity",
                "baseline_activity",
                "anomaly_score",
                "ml3_positive",
                "np3_positive",
                "three_way_result"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nTOP LOW ANOMALIES")

    low = comparison[
        comparison["direction"] == "LOW"
    ].sort_values(
        "anomaly_score"
    )

    print(
        low[
            [
                "grid_id",
                "feature_timestamp",
                "total_activity",
                "baseline_activity",
                "anomaly_score",
                "ml3_positive",
                "np3_positive",
                "three_way_result"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nOUTPUT")
    print(OUTPUT_PATH)

if __name__ == "__main__":
    compare()