"""
NP3 -- Rule-Based Network Activity Alert Generator
=====================================================
Phase 1, Lab 3 (last lab of Phase 1).

Starts from the grid/hour analytics table (same grain as NP2's
aggregate_to_grid_time() output -- one row per grid_id + hour).

IMPORTANT -- read before changing anything:
We only have ONE day of data, so the baseline for each grid MUST be a
WITHIN-DAY baseline: the median total_activity across that grid's own
24 hours, excluding the hour being evaluated. A per-grid-per-hour-of-day
baseline is NOT possible yet -- each such bucket would hold exactly one
observation (today's value), so every deviation would be zero and all
three rules would silently return nothing. That richer baseline needs
multiple days of data and belongs to ML4, later in the project.

Run:
    python network_alerts.py ../data/landing/sms-call-internet-mi-2013-11-01.csv
"""

import sys
import numpy as np
import pandas as pd

# =======================================================================
# THRESHOLDS -- approve or adjust every one of these against your own
# data before treating this lab as done. These are starting points,
# not fixed truths.
# =======================================================================
HIGH_ACTIVITY_MULTIPLIER = 2.0   # current > baseline * this  -> HIGH_ACTIVITY
ACTIVITY_DROP_FRACTION   = 0.25   # current < baseline * this  -> ACTIVITY_DROP
SPIKE_MULTIPLIER         = 2.0   # current > previous_hour * this -> ACTIVITY_SPIKE
FLOOR_PERCENTILE         = 0.25  # activity floor = this percentile of total_activity


# ---------------------------------------------------------------------
# Step 1: rebuild the grid/hour analytics table (same grain as NP2)
# ---------------------------------------------------------------------
def build_grid_hour_table(path: str) -> pd.DataFrame:
    RAW_TO_CANONICAL = {
        "datetime": "timestamp", "CellID": "grid_id", "countrycode": "country_code",
        "smsin": "sms_in", "smsout": "sms_out", "callin": "call_in",
        "callout": "call_out", "internet": "internet_activity",
    }
    activity_cols = ["sms_in", "sms_out", "call_in", "call_out", "internet_activity"]

    df = pd.read_csv(path).rename(columns=RAW_TO_CANONICAL)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["grid_id", "timestamp"])          # never default missing keys
    df = df[~(df[activity_cols] < 0).any(axis=1)]              # drop negative activity rows
    df[activity_cols] = df[activity_cols].fillna(0)            # curated null-to-zero rule
    df["hour"] = df["timestamp"].dt.hour

    grid_hour = (
        df.groupby(["grid_id", "timestamp", "hour"], as_index=False)[activity_cols]
        .sum()
    )
    grid_hour["total_activity"] = grid_hour[activity_cols].sum(axis=1)

    assert grid_hour.duplicated(subset=["grid_id", "timestamp"]).sum() == 0, \
        "grid/hour table has duplicates -- aggregation is broken"

    return grid_hour[["grid_id", "timestamp", "hour", "total_activity"]]


# ---------------------------------------------------------------------
# Step 2: within-day baseline -- leave-one-out median per grid
# ---------------------------------------------------------------------
def add_within_day_baseline(grid_hour: pd.DataFrame, bucket_cols=None) -> pd.DataFrame:
    if bucket_cols is None:
        bucket_cols = ["grid_id"]

    grid_hour = grid_hour.sort_values(bucket_cols + ["timestamp"]).reset_index(drop=True)

    baselines = []

    for _, group in grid_hour.groupby(bucket_cols, sort=True):
        values = group["total_activity"].to_numpy()

        for i in range(len(values)):
            other_values = np.delete(values, i)

            if len(other_values) == 0:
                baselines.append(np.nan)
            else:
                baselines.append(np.median(other_values))

    grid_hour["baseline_activity"] = baselines
    return grid_hour
# ---------------------------------------------------------------------
# Step 3 & 4: activity floor + the three rules
# ---------------------------------------------------------------------
def generate_alerts(grid_hour: pd.DataFrame) -> pd.DataFrame:
    floor = grid_hour["total_activity"].quantile(FLOOR_PERCENTILE)
    print(f"Activity floor ({FLOOR_PERCENTILE:.0%} percentile of total_activity): {floor:.4f}")
    print("Grids/hours below this floor are excluded from HIGH_ACTIVITY / ACTIVITY_DROP")
    print("because a tiny baseline makes the ratio meaningless (e.g. 0.01 -> 0.05 looks")
    print("like a 5x spike but is operationally irrelevant).\n")

    grid_hour = grid_hour.sort_values(["grid_id", "hour"]).reset_index(drop=True)
    grid_hour["prev_hour_activity"] = grid_hour.groupby("grid_id")["total_activity"].shift(1)

    alerts = []
    for row in grid_hour.itertuples(index=False):
        current = row.total_activity
        baseline = row.baseline_activity

        # HIGH_ACTIVITY -- current materially above this grid's own baseline
        if baseline >= floor and current > baseline * HIGH_ACTIVITY_MULTIPLIER:
            alerts.append({
                "grid_id": row.grid_id, "timestamp": row.timestamp,
                "alert_type": "HIGH_ACTIVITY",
                "current_activity": round(current, 4), "baseline_activity": round(baseline, 4),
                "reason": (f"HIGH_ACTIVITY: current activity {current:.2f} is more than "
                           f"{HIGH_ACTIVITY_MULTIPLIER}x this grid's within-day baseline of {baseline:.2f}"),
            })

        # ACTIVITY_DROP -- current materially below this grid's own baseline
        if baseline >= floor and current < baseline * ACTIVITY_DROP_FRACTION:
            alerts.append({
                "grid_id": row.grid_id, "timestamp": row.timestamp,
                "alert_type": "ACTIVITY_DROP",
                "current_activity": round(current, 4), "baseline_activity": round(baseline, 4),
                "reason": (f"ACTIVITY_DROP: current activity {current:.2f} is below "
                           f"{ACTIVITY_DROP_FRACTION}x this grid's within-day baseline of {baseline:.2f}"),
            })

        # ACTIVITY_SPIKE -- sharp rise vs the immediately preceding hour
        prev = row.prev_hour_activity
        if pd.notna(prev) and prev >= floor and current > prev * SPIKE_MULTIPLIER:
            alerts.append({
                "grid_id": row.grid_id, "timestamp": row.timestamp,
                "alert_type": "ACTIVITY_SPIKE",
                "current_activity": round(current, 4), "baseline_activity": round(prev, 4),
                "reason": (f"ACTIVITY_SPIKE: current activity {current:.2f} is more than "
                           f"{SPIKE_MULTIPLIER}x the immediately preceding hour's {prev:.2f}"),
            })

    return pd.DataFrame(alerts)


# ---------------------------------------------------------------------
# Step 7: operational summary
# ---------------------------------------------------------------------
def print_summary(alerts: pd.DataFrame, total_grid_hours: int):
    print("--- Alert Summary ---")
    print("Alerts by type:")
    print(alerts["alert_type"].value_counts().to_string())

    print("\nTop 10 grids by alert count:")
    print(alerts["grid_id"].value_counts().head(10).to_string())

    pct = 100 * len(alerts) / total_grid_hours
    print(f"\n{len(alerts)} alerts out of {total_grid_hours} grid/hours ({pct:.2f}%) alerted.")
    if pct > 5:
        print("WARNING: over 5% of all grid/hours alerted -- thresholds are likely too")
        print("sensitive and should be revised before treating this lab as done.")


# ---------------------------------------------------------------------
# Step 8: written limitation statement (required deliverable)
# ---------------------------------------------------------------------
LIMITATION_STATEMENT = """
--- Limitation Statement ---
This within-day baseline cannot distinguish "this grid is always quiet
at 03:00" from "this grid's activity has genuinely dropped" -- it has
no concept of what a normal hour-of-day looks like, because it only
has one day of data to compare against. A grid that is naturally quiet
overnight will look identical, from this baseline's point of view, to
a grid experiencing a real outage overnight. A per-hour-of-day baseline
(comparing each hour only to that same hour on other days) would fix
this, but requires multiple days of historical data -- that richer
baseline is built later, at ML4.

These alerts are a request to investigate, not a diagnosis. This
dataset measures communication activity only; it says nothing about
network capacity, so an alert here should never be described as
"network congestion" without additional, separate evidence.
"""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python network_alerts.py <path_to_daily_csv>")
        sys.exit(1)

    path = sys.argv[1]

    grid_hour = build_grid_hour_table(path)
    grid_hour = add_within_day_baseline(grid_hour)
    alerts = generate_alerts(grid_hour)

    alerts.to_csv("network_alerts.csv", index=False)
    print(f"Wrote {len(alerts)} alerts to network_alerts.csv\n")

    print_summary(alerts, total_grid_hours=len(grid_hour))
    print(LIMITATION_STATEMENT)