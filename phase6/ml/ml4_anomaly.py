import os
import sys
import glob
import pandas as pd

sys.path.append(r"C:\Users\vimalraj.ck\network_project\phase1")

from network_alerts import build_grid_hour_table, add_within_day_baseline


PROJECT_ROOT = r"C:\Users\vimalraj.ck\network_project"
LANDING_DIR = os.path.join(PROJECT_ROOT, "data", "landing")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "phase6", "ml", "ml4_output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "network_anomaly_scores.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_all_days():
    files = sorted(
        glob.glob(os.path.join(LANDING_DIR, "sms-call-internet-mi-*.csv"))
    )

    if not files:
        raise FileNotFoundError(
            f"No daily CSV files found in {LANDING_DIR}"
        )

    tables = []

    for path in files:
        table = build_grid_hour_table(path)
        tables.append(table)

    combined = pd.concat(tables, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["grid_id", "timestamp"]
    )

    return combined


def calculate_anomaly_scores(grid_hour):
    grid_hour = grid_hour.sort_values(
        ["grid_id", "hour", "timestamp"]
    ).reset_index(drop=True)

    grid_hour = add_within_day_baseline(
        grid_hour,
        bucket_cols=["grid_id", "hour"]
    )

    grid_hour["deviation"] = (
        grid_hour["total_activity"] -
        grid_hour["baseline_activity"]
    )

    grid_hour["anomaly_score"] = 0.0

    valid_baseline = grid_hour["baseline_activity"] > 0

    grid_hour.loc[valid_baseline, "anomaly_score"] = (
        grid_hour.loc[valid_baseline, "deviation"] /
        grid_hour.loc[valid_baseline, "baseline_activity"]
    )

    grid_hour["direction"] = "NORMAL"

    grid_hour.loc[
        grid_hour["anomaly_score"] >= 0.50,
        "direction"
    ] = "HIGH"

    grid_hour.loc[
        grid_hour["anomaly_score"] <= -0.50,
        "direction"
    ] = "LOW"

    grid_hour.loc[
        grid_hour["baseline_activity"].isna(),
        "direction"
    ] = "NO_BASELINE"

    def build_reason(row):
        if pd.isna(row["baseline_activity"]):
            return "No historical baseline available for this grid and hour"

        if row["baseline_activity"] <= 0:
            return "Historical baseline is zero or negative"

        score = row["anomaly_score"]

        if score > 0:
            return (
                f"Activity is {score * 100:.2f}% above the "
                f"historical median for grid {int(row['grid_id'])} "
                f"at hour {int(row['hour']):02d}:00"
            )

        if score < 0:
            return (
                f"Activity is {abs(score) * 100:.2f}% below the "
                f"historical median for grid {int(row['grid_id'])} "
                f"at hour {int(row['hour']):02d}:00"
            )

        return "Activity matches the historical baseline"

    grid_hour["reason"] = grid_hour.apply(build_reason, axis=1)

    return grid_hour[
        [
            "grid_id",
            "timestamp",
            "hour",
            "total_activity",
            "baseline_activity",
            "deviation",
            "anomaly_score",
            "direction",
            "reason"
        ]
    ]


def print_summary(scores):
    print("\nML4 — Anomaly Baseline")
    print("=" * 50)

    print("\nDATE RANGE")
    print(f"Earliest: {scores['timestamp'].min()}")
    print(f"Latest:   {scores['timestamp'].max()}")

    print("\nDIRECTION")
    print(scores["direction"].value_counts().to_string())

    print("\nANOMALY SCORE SUMMARY")
    print(scores["anomaly_score"].describe().to_string())

    print("\nTOP 10 HIGH ANOMALIES")
    print(
        scores[
            scores["direction"] == "HIGH"
        ]
        .sort_values("anomaly_score", ascending=False)
        [
            [
                "grid_id",
                "timestamp",
                "hour",
                "total_activity",
                "baseline_activity",
                "anomaly_score"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nTOP 10 LOW ANOMALIES")
    print(
        scores[
            scores["direction"] == "LOW"
        ]
        .sort_values("anomaly_score")
        [
            [
                "grid_id",
                "timestamp",
                "hour",
                "total_activity",
                "baseline_activity",
                "anomaly_score"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    grid_hour = load_all_days()

    print(f"Loaded grid-hour rows: {len(grid_hour)}")
    print(
        f"Unique dates: "
        f"{grid_hour['timestamp'].dt.date.nunique()}"
    )

    bucket_counts = (
        grid_hour
        .groupby(["grid_id", "hour"])["timestamp"]
        .nunique()
    )

    print("\nHOUR-OF-DAY BASELINE VALIDATION")
    print(f"Minimum observations per bucket: {bucket_counts.min()}")
    print(f"Maximum observations per bucket: {bucket_counts.max()}")
    print(f"Average observations per bucket: {bucket_counts.mean():.2f}")

    if bucket_counts.min() <= 1:
        raise ValueError(
            "Hour-of-day baseline contains buckets with only one day of history."
        )

    scores = calculate_anomaly_scores(grid_hour)

    scores.to_csv(OUTPUT_PATH, index=False)

    print_summary(scores)

    print(f"\nWrote {len(scores)} anomaly scores to:")
    print(OUTPUT_PATH)