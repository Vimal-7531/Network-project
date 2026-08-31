"""
SP2 -- Cleaning & Standardization
====================================
Phase 2, Lab 2. Ports NP2's pandas cleaning rules into Spark, running
across ALL loaded daily files at once (not just one file like NP2 did).

Run:
    python sp2_cleaning.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
from pyspark.sql.functions import (
    col, to_timestamp, to_date, hour, date_format, when, lit, input_file_name
)

LANDING_DIR = "../data/landing"
FILE_GLOB = f"{LANDING_DIR}/sms-call-internet-mi-*.csv"

ACTIVITY_COLS = ["sms_in", "sms_out", "call_in", "call_out", "internet_activity"]

RAW_TO_CANONICAL = {
    "datetime": "timestamp",
    "CellID": "grid_id",
    "countrycode": "country_code",
    "smsin": "sms_in",
    "smsout": "sms_out",
    "callin": "call_in",
    "callout": "call_out",
    "internet": "internet_activity",
}

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


def load_raw(spark):
    df = spark.read.schema(raw_schema).option("header", "true").csv(FILE_GLOB)
    for raw_name, canonical_name in RAW_TO_CANONICAL.items():
        df = df.withColumnRenamed(raw_name, canonical_name)
    return df


def clean(df):
    n_before = df.count()

    df = df.withColumn("timestamp", to_timestamp(col("timestamp")))

    # FIX: NULL < 0 evaluates to NULL in Spark, not False -- a plain
    # "col(c) < 0" check silently treats every null activity value as
    # neither pass nor fail, and such rows vanish from BOTH the keep
    # and reject filters. isNotNull() first prevents that.
    negative_condition = lit(False)
    for c in ACTIVITY_COLS:
        negative_condition = negative_condition | (col(c).isNotNull() & (col(c) < 0))

    reject_condition = col("grid_id").isNull() | col("timestamp").isNull() | negative_condition

    rejected_count = df.filter(reject_condition).count()
    df = df.filter(~reject_condition)

    nulls_before = 0
    for c in ACTIVITY_COLS:
        nulls_before += df.filter(col(c).isNull()).count()

    for c in ACTIVITY_COLS:
        df = df.withColumn(c, when(col(c).isNull(), 0.0).otherwise(col(c)))

    df = (
        df.withColumn("date", to_date(col("timestamp")))
          .withColumn("hour", hour(col("timestamp")))
          .withColumn("day_of_week", date_format(col("timestamp"), "EEEE"))
    )

    df = (
        df.withColumn("total_sms", col("sms_in") + col("sms_out"))
          .withColumn("total_calls", col("call_in") + col("call_out"))
          .withColumn("total_activity", col("total_sms") + col("total_calls") + col("internet_activity"))
    )

    n_after = df.count()
    print(f"clean(): {n_before} rows -> {rejected_count} rejected -> {n_after} rows remain")
    print(f"clean(): {nulls_before} activity-nulls set to 0 by the curated-layer rule")

    return df, rejected_count, nulls_before


if __name__ == "__main__":
    spark = SparkSession.builder.appName("NetworkIntelligence-SP2").getOrCreate()

    raw_df = load_raw(spark)
    clean_network_df, rejected_count, nulls_handled = clean(raw_df)

    file_count = load_raw(spark).withColumn("f", input_file_name()).select("f").distinct().count()
    distinct_timestamps_after = clean_network_df.select("timestamp").distinct().count()
    expected = file_count * 24

    print("\n--- SP2 Cleaning Report ---")
    print(f"Rejected rows:              {rejected_count}")
    print(f"Activity nulls handled:     {nulls_handled}")
    print(f"Distinct timestamps after:  {distinct_timestamps_after} (expected {expected})")
    print(f"Columns present: {clean_network_df.columns}")

    assert distinct_timestamps_after == expected, \
        f"Expected {expected} distinct timestamps after cleaning, got {distinct_timestamps_after}"
    for c in ACTIVITY_COLS:
        assert c in clean_network_df.columns, f"Individual measure {c} missing after cleaning"
    print("\nALL SP2 ACCEPTANCE CHECKS PASSED (row/timestamp/column checks)")

    clean_network_df.show(5, truncate=False)

    spark.stop()