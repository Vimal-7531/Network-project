import argparse
import glob
import json
import logging
import os
import sys
import time

from pyspark.sql import SparkSession
from pyspark.sql.functions import broadcast
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    LongType,
)

sys.path.insert(0, "/mnt/c/Network-project/phase2")

from sp2_cleaning import clean, RAW_TO_CANONICAL
from sp3_aggregations import build_hourly_grid_summary
from sp4_enrichment import load_milan_grid_lookup
from sp3_aggregations import build_top_10_hotspots


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

log = logging.getLogger("DE3.telecom_pipeline")


RAW_SCHEMA = StructType([
    StructField("datetime", StringType(), True),
    StructField("CellID", IntegerType(), True),
    StructField("countrycode", IntegerType(), True),
    StructField("smsin", DoubleType(), True),
    StructField("smsout", DoubleType(), True),
    StructField("callin", DoubleType(), True),
    StructField("callout", DoubleType(), True),
    StructField("internet", DoubleType(), True),
])


def parse_args():
    parser = argparse.ArgumentParser(
        description="DE3 Telecom Network Intelligence Spark Pipeline"
    )

    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--analytics-dir", required=True)
    parser.add_argument("--reference-path", required=True)

    return parser.parse_args()


def read_raw(spark, input_dir):
    file_glob = os.path.join(
        input_dir,
        "sms-call-internet-mi-*.csv",
    )

    matching_files = glob.glob(file_glob)

    if not matching_files:
        raise FileNotFoundError(
            f"No daily activity files found in {input_dir}"
        )

    log.info(
        "read_raw: found %d input file(s)",
        len(matching_files),
    )

    df = (
        spark.read
        .schema(RAW_SCHEMA)
        .option("header", "true")
        .csv(file_glob)
    )

    for raw_name, canonical_name in RAW_TO_CANONICAL.items():
        df = df.withColumnRenamed(
            raw_name,
            canonical_name,
        )

    return df


def aggregate(clean_df):
    return build_hourly_grid_summary(clean_df)


def enrich(spark, hourly_grid_summary, reference_path):
    lookup_rows = load_milan_grid_lookup(reference_path)

    lookup_schema = StructType([
        StructField("grid_id", LongType(), False),
        StructField("geometry_json", StringType(), False),
        StructField("centroid_lon", DoubleType(), False),
        StructField("centroid_lat", DoubleType(), False),
    ])

    temp_dir = os.path.dirname(
        os.path.abspath(reference_path)
    )

    lookup_jsonl_path = os.path.join(
        temp_dir,
        "de3_grid_lookup_tmp.jsonl",
    )

    with open(lookup_jsonl_path, "w") as f:
        for (
            grid_id,
            geometry_json,
            centroid_lon,
            centroid_lat,
        ) in lookup_rows:

            f.write(
                json.dumps({
                    "grid_id": grid_id,
                    "geometry_json": geometry_json,
                    "centroid_lon": centroid_lon,
                    "centroid_lat": centroid_lat,
                })
                + "\n"
            )

    grid_lookup = (
        spark.read
        .schema(lookup_schema)
        .json(lookup_jsonl_path)
    )

    enriched_df = hourly_grid_summary.join(
        broadcast(grid_lookup),
        on="grid_id",
        how="left",
    )

    unmatched = (
        enriched_df
        .filter(enriched_df.geometry_json.isNull())
        .select("grid_id")
        .distinct()
        .count()
    )

    if unmatched > 0:
        raise ValueError(
            f"Geospatial enrichment failed: {unmatched} grid IDs unmatched"
        )

    log.info(
        "enrich: geospatial enrichment successful; lookup_rows=%d",
        len(lookup_rows),
    )

    return enriched_df


def write_outputs(
    clean_df,
    enriched_df,
    output_dir,
    analytics_dir,
):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(analytics_dir, exist_ok=True)

    log.info(
        "write_outputs: writing processed activity to %s",
        output_dir,
    )

    (
        clean_df.write
        .mode("overwrite")
        .partitionBy("date")
        .parquet(output_dir)
    )

    hourly_path = os.path.join(
        analytics_dir,
        "hourly_grid_summary",
    )

    log.info(
        "write_outputs: writing hourly analytics to %s",
        hourly_path,
    )

    (
        enriched_df.write
        .mode("overwrite")
        .parquet(hourly_path)
    )

    dashboard_path = os.path.join(
        analytics_dir,
        "dashboard_summary",
    )

    top_10 = build_top_10_hotspots(
        enriched_df
    )

    (
        top_10.coalesce(1)
        .write
        .mode("overwrite")
        .option("header", "true")
        .csv(dashboard_path)
    )

    log.info(
        "write_outputs: processed and analytics outputs written successfully"
    )


def main(input_dir=None, output_dir=None, analytics_dir=None, reference_path=None):
    if input_dir is None:
        args = parse_args()
        input_dir = args.input_dir
        output_dir = args.output_dir
        analytics_dir = args.analytics_dir
        reference_path = args.reference_path

    start_time = time.time()

    log.info(
        "=== DE3 Spark pipeline starting ==="
    )

    log.info(
        "input_dir=%s output_dir=%s analytics_dir=%s reference_path=%s",
        input_dir,
        output_dir,
        analytics_dir,
        reference_path,
    )

    spark = (
        SparkSession.builder
        .appName("NetworkIntelligence-DE3")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )

    try:
        raw_df = read_raw(
            spark,
            input_dir,
        )

        input_rows = raw_df.count()

        log.info(
            "STAGE read_raw: input_rows=%d",
            input_rows,
        )

        clean_df, rejected_rows, nulls_handled = clean(
            raw_df
        )

        clean_rows = clean_df.count()

        log.info(
            "STAGE clean: clean_rows=%d rejected_rows=%d nulls_handled=%d",
            clean_rows,
            rejected_rows,
            nulls_handled,
        )

        hourly_grid_summary = aggregate(
            clean_df
        )

        hourly_rows = hourly_grid_summary.count()

        log.info(
            "STAGE aggregate: output_rows=%d",
            hourly_rows,
        )

        enriched_df = enrich(
            spark,
            hourly_grid_summary,
            reference_path,
        )

        enriched_rows = enriched_df.count()

        log.info(
            "STAGE enrich: output_rows=%d",
            enriched_rows,
        )

        write_outputs(
            clean_df,
            enriched_df,
            output_dir,
            analytics_dir,
        )

        elapsed = time.time() - start_time

        log.info(
            "=== JOB SUMMARY: input_rows=%d clean_rows=%d "
            "rejected_rows=%d nulls_handled=%d "
            "hourly_rows=%d enriched_rows=%d "
            "elapsed_seconds=%.2f status=SUCCESS ===",
            input_rows,
            clean_rows,
            rejected_rows,
            nulls_handled,
            hourly_rows,
            enriched_rows,
            elapsed,
        )

        spark.stop()

        return 0

    except FileNotFoundError as exc:
        log.error(
            "=== JOB SUMMARY: status=FAILED "
            "reason=NO_INPUT_FILES error=%s ===",
            exc,
        )

        spark.stop()

        return 1

    except Exception as exc:
        elapsed = time.time() - start_time

        log.exception(
            "=== JOB SUMMARY: status=FAILED "
            "elapsed_seconds=%.2f error=%s ===",
            elapsed,
            exc,
        )

        spark.stop()

        return 2


if __name__ == "__main__":
    sys.exit(main())
