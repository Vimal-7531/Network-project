from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    avg,
    col,
    count,
    max as spark_max,
    stddev,
    sum as spark_sum,
    when
)
from pyspark.sql.window import Window
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

input_path = PROJECT_ROOT / "data" / "analytics" / "hourly_grid_summary"
output_path = PROJECT_ROOT / "data" / "analytics" / "network_feature_table"
def main():
    spark = (
        SparkSession.builder
        .appName("NetworkActivityFeatures")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )



    df = spark.read.parquet(str(input_path))

    df = df.select(
        "grid_id",
        "timestamp",
        "total_activity",
        "internet_activity"
    )

    df = df.dropDuplicates(["grid_id", "timestamp"])

    order_window = Window \
        .partitionBy("grid_id") \
        .orderBy("timestamp")

    recent_window = order_window.rowsBetween(-2, 0)

    baseline_window = order_window.rowsBetween(-5, -3)

    df = df.withColumn(
        "recent_count",
        count("total_activity").over(recent_window)
    )

    df = df.withColumn(
        "baseline_count",
        count("total_activity").over(baseline_window)
    )

    df = df.withColumn(
        "recent_avg",
        avg("total_activity").over(recent_window)
    )

    df = df.withColumn(
        "baseline_avg",
        avg("total_activity").over(baseline_window)
    )

    df = df.withColumn(
        "recent_peak",
        spark_max("total_activity").over(recent_window)
    )

    df = df.withColumn(
        "active_hours",
        spark_sum(
            when(col("total_activity") > 0, 1).otherwise(0)
        ).over(recent_window)
    )

    df = df.withColumn(
        "recent_stddev",
        stddev("total_activity").over(recent_window)
    )

    df = df.withColumn(
        "recent_internet",
        spark_sum("internet_activity").over(recent_window)
    )

    df = df.withColumn(
        "recent_total",
        spark_sum("total_activity").over(recent_window)
    )

    features = df.filter(
        (col("recent_count") == 3) &
        (col("baseline_count") == 3)
    ).select(
        "grid_id",
        col("timestamp").alias("feature_timestamp"),
        col("recent_avg").alias("avg_activity"),
        when(
            col("baseline_avg") > 0,
            (col("recent_avg") - col("baseline_avg")) / col("baseline_avg")
        ).otherwise(0.0).alias("activity_growth"),
        col("active_hours"),
        when(
            col("recent_avg") > 0,
            col("recent_peak") / col("recent_avg")
        ).otherwise(0.0).alias("peak_ratio"),
        when(
            col("recent_stddev").isNotNull(),
            col("recent_stddev")
        ).otherwise(0.0).alias("variability"),
        when(
            col("recent_total") > 0,
            col("recent_internet") / col("recent_total")
        ).otherwise(0.0).alias("internet_share")
    )

    features = features.orderBy(
        "grid_id",
        "feature_timestamp"
    )

    features.write \
        .mode("overwrite") \
        .parquet(str(output_path))

    print("ML2 feature table created successfully")
    print(f"Output path: {output_path}")
    print("Feature count:", features.count())

    features.printSchema()
    features.show(20, truncate=False)

    spark.stop()
    return 0

if __name__ == "__main__":
    main()