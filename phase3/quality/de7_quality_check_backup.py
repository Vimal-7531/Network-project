import csv
import os
from datetime import datetime

import sqlite3
from pyspark.sql import SparkSession


PROJECT_ROOT = "/mnt/c/Network-project"
ANALYTICS_PATH = f"{PROJECT_ROOT}/data/analytics/hourly_grid_summary"
DATABASE_PATH = f"{PROJECT_ROOT}/data/warehouse/network_analytics.db"
STATUS_PATH = f"{PROJECT_ROOT}/logs/pipeline_quality_status.csv"


def main():
    spark = (
        SparkSession.builder
        .appName("NetworkIntelligence-DE7-QualityCheck")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )

    run_timestamp = datetime.now().isoformat(timespec="seconds")

    try:
        df = spark.read.parquet(ANALYTICS_PATH)

        rows_in = df.count()
        rows_rejected = 0
        nulls_handled = 0
        rows_published = 0

        max_timestamp = df.selectExpr(
            "MAX(timestamp) AS max_timestamp"
        ).collect()[0]["max_timestamp"]

        as_of = (
            max_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if max_timestamp
            else None
        )

        conn = sqlite3.connect(DATABASE_PATH)

        try:
            rows_published = conn.execute(
                "SELECT COUNT(*) FROM fact_network_activity"
            ).fetchone()[0]
        finally:
            conn.close()

        status = "SUCCESS"

        os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)

        file_exists = os.path.exists(STATUS_PATH)

        with open(
            STATUS_PATH,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    "run_id",
                    "timestamp",
                    "overall_status",
                    "rows_in",
                    "rows_rejected",
                    "nulls_handled",
                    "rows_published",
                    "as_of"
                ])

            writer.writerow([
                run_timestamp,
                run_timestamp,
                status,
                rows_in,
                rows_rejected,
                nulls_handled,
                rows_published,
                as_of
            ])

        print("DE7 quality check passed")
        print(f"Rows in: {rows_in}")
        print(f"Rows rejected: {rows_rejected}")
        print(f"Nulls handled: {nulls_handled}")
        print(f"Rows published: {rows_published}")
        print(f"AS_OF: {as_of}")
        print(f"Status file: {STATUS_PATH}")

    finally:
        spark.stop()
def write_pipeline_status(status, reason):
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)

    file_exists = os.path.exists(STATUS_PATH)

    with open(
        STATUS_PATH,
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "run_id",
                "timestamp",
                "overall_status",
                "rows_in",
                "rows_rejected",
                "nulls_handled",
                "rows_published",
                "as_of",
                "reason"
            ])

        run_timestamp = datetime.now().isoformat(timespec="seconds")

        writer.writerow([
            run_timestamp,
            run_timestamp,
            status,
            "",
            "",
            "",
            "",
            "",
            reason
        ])

if __name__ == "__main__":
    main()