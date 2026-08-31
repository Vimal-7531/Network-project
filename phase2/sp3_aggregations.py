"""
SP3 -- Network Activity Aggregations
=======================================
Phase 2, Lab 3. Runs sp2_cleaning's clean() first, then does the
country-code -> grid/hour GRAIN TRANSITION -- the single most
important step in the whole project.

Produces hourly_grid_summary: the canonical table everything
downstream (API, ML, dashboard) reads from. Exactly one row per
grid_id + timestamp. country_code does NOT appear in it.

Run:
    python sp3_aggregations.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, sum as spark_sum, avg as spark_avg, max as spark_max,
    row_number, rank
)
from pyspark.sql.window import Window

from sp2_cleaning import load_raw, clean, ACTIVITY_COLS


def build_hourly_grid_summary(clean_df):
    """Step 1: collapse country_code rows to one row per grid_id + timestamp
    by SUMMING the five activity measures. country_code is intentionally
    dropped here -- it belongs to the raw/canonical layer only.
    """
    hourly_grid_summary = (
        clean_df
        .groupBy("grid_id", "timestamp", "date", "hour", "day_of_week")
        .agg(*[spark_sum(c).alias(c) for c in ACTIVITY_COLS])
    )

    # Step 2: total SMS activity, total call activity, total_activity
    hourly_grid_summary = (
        hourly_grid_summary
        .withColumn("total_sms", col("sms_in") + col("sms_out"))
        .withColumn("total_calls", col("call_in") + col("call_out"))
        .withColumn(
            "total_activity",
            col("sms_in") + col("sms_out") + col("call_in") + col("call_out") + col("internet_activity"),
        )
        # internet share -- what fraction of this grid/hour's activity is internet
        .withColumn("internet_share", col("internet_activity") / col("total_activity"))
    )

    # REQUIRED assertion, must be in the code, not just eyeballed once
    dup_count = (
        hourly_grid_summary
        .groupBy("grid_id", "timestamp")
        .count()
        .filter(col("count") > 1)
        .count()
    )
    assert dup_count == 0, \
        f"hourly_grid_summary has {dup_count} duplicate (grid_id, timestamp) combinations"
    assert "country_code" not in hourly_grid_summary.columns, \
        "country_code leaked into hourly_grid_summary -- grain transition is broken"

    return hourly_grid_summary


def build_daily_traffic_summary(hourly_grid_summary):
    """Daily activity per grid -- sum total_activity across all hours of each date."""
    return (
        hourly_grid_summary
        .groupBy("grid_id", "date")
        .agg(
            spark_sum("total_activity").alias("daily_total_activity"),
            spark_avg("total_activity").alias("daily_avg_hourly_activity"),
        )
    )


def build_top_10_hotspots(hourly_grid_summary):
    """Top 10 grids by total activity across the ENTIRE loaded period.
    Uses 'high-activity grids' / 'hotspots' language -- never 'congestion',
    since this dataset has no capacity/utilization data to justify that word.
    """
    return (
        hourly_grid_summary
        .groupBy("grid_id")
        .agg(spark_sum("total_activity").alias("total_activity"))
        .orderBy(col("total_activity").desc())
        .limit(10)
    )


def compute_peak_activity_hour(hourly_grid_summary):
    """The single hour (0-23) with the highest total activity, summed
    across all grids and all days loaded.
    """
    return (
        hourly_grid_summary
        .groupBy("hour")
        .agg(spark_sum("total_activity").alias("total_activity"))
        .orderBy(col("total_activity").desc())
        .first()
    )


if __name__ == "__main__":
    spark = SparkSession.builder.appName("NetworkIntelligence-SP3").getOrCreate()

    raw_df = load_raw(spark)
    clean_network_df, _, _ = clean(raw_df)
    clean_count = clean_network_df.count()

    hourly_grid_summary = build_hourly_grid_summary(clean_network_df)
    summary_count = hourly_grid_summary.count()

    daily_traffic_summary = build_daily_traffic_summary(hourly_grid_summary)
    top_10 = build_top_10_hotspots(hourly_grid_summary)
    peak_hour_row = compute_peak_activity_hour(hourly_grid_summary)

    n_files = clean_network_df.select("date").distinct().count()
    max_expected_rows = n_files * 24 * 10000

    print("--- SP3 Aggregation Report ---")
    print(f"clean_network_df row count:      {clean_count}")
    print(f"hourly_grid_summary row count:   {summary_count}")
    print(f"Max allowed (days x 24 x 10000): {max_expected_rows}")

    assert summary_count < clean_count, \
        "hourly_grid_summary must have strictly fewer rows than clean_network_df"
    assert summary_count <= max_expected_rows, \
        f"hourly_grid_summary has {summary_count} rows, exceeds max {max_expected_rows}"
    assert "country_code" not in hourly_grid_summary.columns, \
        "country_code must not appear in hourly_grid_summary"
    print("\nALL SP3 ACCEPTANCE CHECKS PASSED (row count, max size, no country_code)")

    print("\nTop 10 high-activity grids (whole period):")
    top_10.show(10, truncate=False)

    print(f"\nPeak activity hour (whole period): hour={peak_hour_row['hour']}, "
          f"total_activity={peak_hour_row['total_activity']:.2f}")

    print("\nSample of hourly_grid_summary:")
    hourly_grid_summary.orderBy("grid_id", "timestamp").show(5, truncate=False)

    print("\nSample of daily_traffic_summary:")
    daily_traffic_summary.orderBy("grid_id", "date").show(5, truncate=False)

    spark.stop()