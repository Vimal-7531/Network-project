import csv
import os
import sqlite3
from datetime import datetime

from pyspark.sql import SparkSession

PROJECT_ROOT = "/mnt/c/Users/vimalraj.ck/network_project"
ANALYTICS_PATH = f"{PROJECT_ROOT}/data/analytics/hourly_grid_summary"
DATABASE_PATH = f"{PROJECT_ROOT}/data/warehouse/network_analytics.db"
STATUS_PATH = f"{PROJECT_ROOT}/logs/pipeline_quality_status.csv"


def write_pipeline_status(
    status,
    reason,
    rows_in="",
    rows_rejected="",
    nulls_handled="",
    rows_published="",
    as_of_reason=""
):
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)

    header = [
        "run_id",
        "timestamp",
        "overall_status",
        "rows_in",
        "rows_rejected",
        "nulls_handled",
        "rows_published",
        "as_of_reason",
        "reason"
    ]

    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        if rows:
            old_rows = rows[1:]

            with open(STATUS_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)

                for row in old_rows:
                    row = row[:8]

                    while len(row) < 8:
                        row.append("")

                    row.append("")
                    writer.writerow(row)

    else:
        with open(STATUS_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)

    run_timestamp = datetime.now().isoformat(timespec="seconds")

    with open(STATUS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            run_timestamp,
            run_timestamp,
            status,
            rows_in,
            rows_rejected,
            nulls_handled,
            rows_published,
            as_of_reason,
            reason
        ])


def main():
    spark = (
        SparkSession.builder
        .appName("NetworkIntelligence-DE7-QualityCheck")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )

    try:
        df = spark.read.parquet(ANALYTICS_PATH)

        rows_in = df.count()
        rows_rejected = 0
        nulls_handled = 0

        if rows_in == 0:
            raise ValueError("Analytics dataset is empty")

        required_columns = {
            "grid_id",
            "timestamp",
            "total_activity",
            "total_sms",
            "total_calls",
            "internet_activity",
            "internet_share"
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        null_count = df.select(
            "grid_id",
            "timestamp"
        ).where(
            "grid_id IS NULL OR timestamp IS NULL"
        ).count()

        if null_count > 0:
            raise ValueError(
                f"Validation failed: {null_count} rows have null grid_id or timestamp"
            )

        duplicate_count = (
            df.groupBy("grid_id", "timestamp")
            .count()
            .filter("count > 1")
            .count()
        )

        if duplicate_count > 0:
            raise ValueError(
                f"Validation failed: {duplicate_count} duplicate grid/time combinations"
            )

        max_timestamp = df.selectExpr(
            "MAX(timestamp) AS max_timestamp"
        ).collect()[0]["max_timestamp"]

        as_of_reason = (
            max_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if max_timestamp
            else None
        )

        if not os.path.exists(DATABASE_PATH):
            raise FileNotFoundError(
                f"Warehouse database not found: {DATABASE_PATH}"
            )

        conn = sqlite3.connect(DATABASE_PATH)

        try:
            rows_published = conn.execute(
                "SELECT COUNT(*) FROM fact_network_activity"
            ).fetchone()[0]
        finally:
            conn.close()

        write_pipeline_status(
            "SUCCESS",
            "Quality checks passed",
            rows_in,
            rows_rejected,
            nulls_handled,
            rows_published,
            as_of_reason
        )

        print("DE7 quality check passed")
        print(f"Rows in: {rows_in}")
        print(f"Rows rejected: {rows_rejected}")
        print(f"Nulls handled: {nulls_handled}")
        print(f"Rows published: {rows_published}")
        print(f"AS_OF_REASON: {as_of_reason}")
        print(f"Status file: {STATUS_PATH}")

    except Exception as error:
        write_pipeline_status(
            "FAILED",
            str(error)
        )
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    main()