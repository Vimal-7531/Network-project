"""
SP2 (cont.) -- Pandas vs Spark Comparison Test
=================================================
Proves the Spark cleaning logic in sp2_cleaning.py is semantically
equivalent to the pandas UsageProcessor from Phase 1.

Run:
    python sp2_pandas_spark_comparison.py ../data/landing/sms-call-internet-mi-2013-11-01.csv
"""

import sys
import os

# Point Python at the phase1 folder so we can import usage_processor.py from it.
# IMPORTANT: this folder name must match your actual Phase 1 folder name exactly.
PHASE1_FOLDER_NAME = "phase1"   # <-- change this if your folder is named differently

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", PHASE1_FOLDER_NAME))

from usage_processor import UsageProcessor  # noqa: E402  (NOT phase1.usage_processor)

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
from pyspark.sql.functions import sum as spark_sum, col
from sp2_cleaning import RAW_TO_CANONICAL, clean, ACTIVITY_COLS  # noqa: E402


def run_pandas_side(path):
    proc = UsageProcessor(path)
    proc.load_data()
    proc.clean_data()
    proc.derive_time_features()
    proc.aggregate_to_grid_time()
    proc.derive_activity_features()
    total_activity_sum = proc.grid_time_df["total_activity"].sum()
    row_count = len(proc.grid_time_df)
    return row_count, total_activity_sum


def run_spark_side(spark, path):
    raw_schema = StructType([
        StructField("datetime",    StringType(),  True),
        StructField("CellID",      IntegerType(), True),
        StructField("countrycode", IntegerType(), True),
        StructField("smsin",       DoubleType(),  True),
        StructField("smsout",      DoubleType(),  True),
        StructField("callin",      DoubleType(),  True),
        StructField("callout",     DoubleType(),  True),
        StructField("internet",    DoubleType(),  True),
    ])
    df = spark.read.schema(raw_schema).option("header", "true").csv(path)
    for raw_name, canonical_name in RAW_TO_CANONICAL.items():
        df = df.withColumnRenamed(raw_name, canonical_name)

    clean_df, _, _ = clean(df)

    grid_time = (
        clean_df.groupBy("grid_id", "timestamp")
        .agg(*[spark_sum(c).alias(c) for c in ACTIVITY_COLS])
    )
    grid_time = grid_time.withColumn(
        "total_activity",
        col("sms_in") + col("sms_out") + col("call_in") + col("call_out") + col("internet_activity"),
    )

    row_count = grid_time.count()
    total_activity_sum = grid_time.agg(spark_sum("total_activity")).collect()[0][0]
    return row_count, total_activity_sum


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sp2_pandas_spark_comparison.py <path_to_one_daily_csv>")
        sys.exit(1)

    path = sys.argv[1]

    pandas_rows, pandas_total = run_pandas_side(path)

    spark = SparkSession.builder.appName("NetworkIntelligence-SP2-Comparison").getOrCreate()
    spark_rows, spark_total = run_spark_side(spark, path)

    print("\n--- Pandas vs Spark Comparison (same single day) ---")
    print(f"Pandas grid/hour row count: {pandas_rows}")
    print(f"Spark  grid/hour row count: {spark_rows}")
    print(f"Pandas total_activity sum:  {pandas_total:.4f}")
    print(f"Spark  total_activity sum:  {spark_total:.4f}")

    assert pandas_rows == spark_rows, \
        f"Row count mismatch: pandas={pandas_rows} spark={spark_rows}"
    assert abs(pandas_total - spark_total) < 0.01, \
        f"total_activity mismatch: pandas={pandas_total} spark={spark_total}"

    print("\nPANDAS vs SPARK COMPARISON TEST PASSED -- results are equivalent")

    spark.stop()