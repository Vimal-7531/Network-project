"""
SP6 -- Write Processed & Analytics Data
==========================================
Phase 2, Lab 6 (final data-writing lab). Persists Spark outputs to
disk in formats appropriate for each layer, instead of just printing
results that vanish when the script ends.

Storage decisions (the actual learning objective of this lab):
    - clean activity data      -> Parquet, partitioned by date
    - hourly_grid_summary       -> Parquet, NOT partitioned, no geometry
    - dashboard_summary          -> CSV
    - milano-grid.geojson        -> stays in data/reference/, untouched

Run:
    python sp6_write_outputs.py
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum, col

from sp2_cleaning import load_raw, clean
from sp3_aggregations import build_hourly_grid_summary, build_top_10_hotspots

PROCESSED_DIR = "../data/processed/activity"
ANALYTICS_DIR = "../data/analytics/hourly_grid_summary"
DASHBOARD_CSV = "../data/analytics/dashboard_summary.csv"


def get_dir_size_mb(path):
    total_bytes = 0
    for root, _, files in os.walk(path):
        for f in files:
            total_bytes += os.path.getsize(os.path.join(root, f))
    return total_bytes / (1024 * 1024)


if __name__ == "__main__":
    spark = (
    SparkSession.builder
    .appName("NetworkIntelligence-SP6")
    .master("local[2]")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
    )
    spark.conf.set("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")

    raw_df = load_raw(spark)
    clean_df, _, _ = clean(raw_df)
    hourly_grid_summary = build_hourly_grid_summary(clean_df)

    print(f"Writing clean activity data to {PROCESSED_DIR} (Parquet, partitioned by date)...")
    (
        clean_df.write
        .mode("overwrite")
        .partitionBy("date")
        .parquet(PROCESSED_DIR)
    )
    print("Done.")

    print(f"\nWriting hourly_grid_summary to {ANALYTICS_DIR} (Parquet, no partitioning)...")
    (
        hourly_grid_summary.write
        .mode("overwrite")
        .parquet(ANALYTICS_DIR)
    )
    print("Done.")
    assert "geometry_json" not in hourly_grid_summary.columns, \
        "geometry must NOT be duplicated into hourly_grid_summary"

    print(f"\nWriting dashboard summary to {DASHBOARD_CSV} (CSV)...")
    top_10 = build_top_10_hotspots(hourly_grid_summary)
    (
        top_10.coalesce(1).write
        .mode("overwrite")
        .option("header", "true")
        .csv(DASHBOARD_CSV)
    )
    print("Done. (Spark writes CSV output as a folder containing one part file --")
    print(" that's normal Spark behavior, not an error.)")

    print("\n--- SP6 Round-Trip Validation ---")

    original_row_count = hourly_grid_summary.count()
    original_schema = set(hourly_grid_summary.columns)

    reread_summary = spark.read.parquet(ANALYTICS_DIR)
    reread_row_count = reread_summary.count()
    reread_schema = set(reread_summary.columns)

    print(f"Original row count: {original_row_count}")
    print(f"Re-read row count:  {reread_row_count}")
    print(f"Schema matches:     {original_schema == reread_schema}")

    dup_count_after_roundtrip = (
        reread_summary.groupBy("grid_id", "timestamp").count()
        .filter(col("count") > 1).count()
    )
    print(f"Duplicates on (grid_id, timestamp) after round-trip: {dup_count_after_roundtrip}")

    assert original_row_count == reread_row_count, "Round-trip row count mismatch"
    assert original_schema == reread_schema, "Round-trip schema mismatch"
    assert dup_count_after_roundtrip == 0, "Duplicates reappeared after round-trip"
    assert "geometry_json" not in reread_summary.columns, "geometry column present in analytics output"
    print("ALL ROUND-TRIP CHECKS PASSED")

    print(f"\n--- Partition folders under {PROCESSED_DIR} ---")
    partition_folders = [d for d in os.listdir(PROCESSED_DIR) if d.startswith("date=")]
    for folder in sorted(partition_folders):
        print(f"  {folder}")
    print(f"({len(partition_folders)} date partitions found)")

    print("\n--- File Size Comparison: CSV vs Parquet (same hourly_grid_summary data) ---")
    csv_compare_path = "hourly_grid_summary_compare.csv"
    hourly_grid_summary.coalesce(1).write.mode("overwrite").option("header", "true").csv(csv_compare_path)

    csv_size_mb = get_dir_size_mb(csv_compare_path)
    parquet_size_mb = get_dir_size_mb(ANALYTICS_DIR)

    print(f"CSV size (same data):     {csv_size_mb:.2f} MB")
    print(f"Parquet size (same data): {parquet_size_mb:.2f} MB")
    if csv_size_mb > 0:
        print(f"Parquet is {csv_size_mb / parquet_size_mb:.1f}x smaller than CSV")
    print("\nWhy: Parquet is COLUMNAR and binary-encoded, vs CSV's row-by-row plain")
    print("text -- this is why Parquet is standard for processed/analytics layers,")
    print("while CSV stays reserved for small, human-facing outputs.")

    spark.stop()