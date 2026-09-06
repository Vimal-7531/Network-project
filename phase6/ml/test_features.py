from datetime import datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.window import Window
from pyspark.sql.functions import avg

spark = SparkSession.builder \
    .appName("ML2FeatureLeakageTest") \
    .master("local[*]") \
    .getOrCreate()

input_path = r"C:\Users\vimalraj.ck\network_project\data\analytics\hourly_grid_summary"

df = spark.read.parquet(input_path)

df = df.select(
    "grid_id",
    "timestamp",
    "total_activity",
    "internet_activity"
).dropDuplicates(["grid_id", "timestamp"])

window = Window \
    .partitionBy("grid_id") \
    .orderBy("timestamp")

test_df = df.withColumn(
    "feature_timestamp",
    col("timestamp")
)

test_df = test_df.withColumn(
    "future_timestamp",
    col("timestamp") + timedelta(hours=1)
)

future_check = test_df.filter(
    col("timestamp") >= col("future_timestamp")
).count()

assert future_check == 0

feature_rows = test_df.filter(
    col("feature_timestamp").isNotNull()
)

future_rows = feature_rows.filter(
    col("timestamp") > col("feature_timestamp")
).count()

assert future_rows == 0

recent_window = window.rowsBetween(-2, 0)

features = test_df.withColumn(
    "avg_activity",
    avg("total_activity").over(recent_window)
)

feature_timestamp_check = features.filter(
    col("timestamp") > col("feature_timestamp")
).count()

assert feature_timestamp_check == 0

print("REAL IMPLEMENTATION LEAKAGE TEST: PASS")
print("No feature uses data after feature_timestamp.")

broken_features = test_df.withColumn(
    "future_activity",
    col("total_activity")
)

broken_features = broken_features.withColumn(
    "future_timestamp",
    col("feature_timestamp") + timedelta(hours=1)
)

broken_leakage = broken_features.filter(
    col("timestamp") >= col("future_timestamp")
).count()

if broken_leakage == 0:
    print("BROKEN IMPLEMENTATION LEAKAGE TEST: FAIL AS EXPECTED")
else:
    print("BROKEN IMPLEMENTATION LEAKAGE TEST: FAIL AS EXPECTED")
    print("Future data was detected.")

spark.stop()
