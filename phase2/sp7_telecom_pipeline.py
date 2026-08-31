"""
SP7 -- The Reusable Spark ETL Job
====================================
Phase 2, Lab 7 (final lab). This is the bridge from exercise scripts
to a production-style component: ONE executable job with configurable
paths, structured logging, and fail-fast behavior on bad input.

CRITICAL: this file does NOT reimplement any transformation logic.
Every rule (cleaning, quarantine, null-to-zero, the country-code ->
grid/hour grain transition, geospatial enrichment) has exactly ONE
definition, already written in SP2/SP3/SP4/SP6, and is only IMPORTED
and CALLED here.

Usage:
    python sp7_telecom_pipeline.py --input-dir ../data/landing \
                                    --output-dir ../data/processed/activity \
                                    --analytics-dir ../data/analytics \
                                    --reference-path ../data/reference/milano-grid.geojson

Exit codes:
    0 = success
    1 = no input files found (fails loudly, never silently)
    2 = any other unhandled error during processing
"""

import argparse
import glob
import logging
import sys
import time
import json

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, LongType

from sp2_cleaning import load_raw as _load_raw_default_dir, clean, RAW_TO_CANONICAL
from sp3_aggregations import build_hourly_grid_summary
from sp4_enrichment import load_milan_grid_lookup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("SP7.telecom_pipeline")

RAW_SCHEMA = StructType([
    StructField("datetime",    StringType(),  True),
    StructField("CellID",      IntegerType(), True),
    StructField("countrycode", IntegerType(), True),
    StructField("smsin",       DoubleType(),  True),
    StructField("smsout",      DoubleType(),  True),
    StructField("callin",      DoubleType(),  True),
    StructField("callout",     DoubleType(),  True),
    StructField("internet",    DoubleType(),  True),
])


def parse_args():
    parser = argparse.ArgumentParser(description="Telecom Network Intelligence Spark ETL job")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--analytics-dir", required=True)
    parser.add_argument("--reference-path", required=True)
    return parser.parse_args()


def read_raw(spark, input_dir):
    file_glob = f"{input_dir}/sms-call-internet-mi-*.csv"
    matching_files = glob.glob(file_glob)

    if len(matching_files) == 0:
        log.error("FAIL-FAST: no files matched %s -- nothing to process", file_glob)
        raise FileNotFoundError(f"No input files found matching {file_glob}")

    log.info("read_raw: found %d input file(s) matching %s", len(matching_files), file_glob)

    df = spark.read.schema(RAW_SCHEMA).option("header", "true").csv(file_glob)
    for raw_name, canonical_name in RAW_TO_CANONICAL.items():
        df = df.withColumnRenamed(raw_name, canonical_name)
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
    lookup_jsonl_path = "sp7_grid_lookup_tmp.jsonl"
    with open(lookup_jsonl_path, "w") as f:
        for grid_id, geometry_json, centroid_lon, centroid_lat in lookup_rows:
            f.write(json.dumps({
                "grid_id": grid_id, "geometry_json": geometry_json,
                "centroid_lon": centroid_lon, "centroid_lat": centroid_lat,
            }) + "\n")
    grid_lookup = spark.read.schema(lookup_schema).json(lookup_jsonl_path)

    from pyspark.sql.functions import broadcast
    return hourly_grid_summary.join(broadcast(grid_lookup), on="grid_id", how="left")


def write_outputs(clean_df, hourly_grid_summary, output_dir, analytics_dir):
    clean_df.write.mode("overwrite").partitionBy("date").parquet(output_dir)
    hourly_grid_summary.write.mode("overwrite").parquet(f"{analytics_dir}/hourly_grid_summary")


def main():
    args = parse_args()
    start_time = time.time()
    log.info("=== Telecom Network Intelligence ETL job starting ===")
    log.info("input_dir=%s output_dir=%s analytics_dir=%s reference_path=%s",
              args.input_dir, args.output_dir, args.analytics_dir, args.reference_path)

    spark = (
        SparkSession.builder
        .appName("NetworkIntelligence-TelecomPipeline")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )

    try:
        raw_df = read_raw(spark, args.input_dir)
        input_rows = raw_df.count()
        log.info("STAGE read_raw: input_rows=%d", input_rows)

        clean_df, rejected_rows, nulls_handled = clean(raw_df)
        log.info("STAGE clean: rejected_rows=%d nulls_handled=%d", rejected_rows, nulls_handled)

        hourly_grid_summary = aggregate(clean_df)
        output_rows = hourly_grid_summary.count()
        log.info("STAGE aggregate: output_rows=%d", output_rows)

        enriched_df = enrich(spark, hourly_grid_summary, args.reference_path)
        log.info("STAGE enrich: enrichment join complete")

        write_outputs(clean_df, hourly_grid_summary, args.output_dir, args.analytics_dir)
        log.info("STAGE write_outputs: wrote %s and %s/hourly_grid_summary",
                  args.output_dir, args.analytics_dir)

        elapsed = time.time() - start_time
        log.info(
            "=== JOB SUMMARY: input_rows=%d rejected_rows=%d nulls_handled=%d "
            "output_rows=%d elapsed_seconds=%.2f status=SUCCESS ===",
            input_rows, rejected_rows, nulls_handled, output_rows, elapsed,
        )
        spark.stop()
        sys.exit(0)

    except FileNotFoundError as e:
        log.error("=== JOB SUMMARY: status=FAILED reason=NO_INPUT_FILES error=%s ===", e)
        spark.stop()
        sys.exit(1)

    except Exception as e:
        elapsed = time.time() - start_time
        log.error("=== JOB SUMMARY: status=FAILED elapsed_seconds=%.2f error=%s ===", elapsed, e)
        spark.stop()
        sys.exit(2)


if __name__ == "__main__":
    main()