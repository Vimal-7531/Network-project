"""
SP5 -- Performance & Execution Behaviour -- EXPERIMENTS, not a rewrite
==========================================================================
Unlike SP1-SP4, this file does NOT hand you a finished "optimized"
pipeline. Each experiment below prints evidence (an explain() plan, or
a before/after timing). YOU read that evidence and decide what's
actually worth keeping -- some of these will help, some genuinely
won't on a dataset this size running on one local machine.

Run:
    python sp5_performance_experiments.py
Then read the printed output for each experiment before deciding anything.
"""

import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum, broadcast

from sp2_cleaning import load_raw, clean
from sp3_aggregations import build_hourly_grid_summary
from sp4_enrichment import load_milan_grid_lookup, GEOJSON_PATH

import json
from pyspark.sql.types import StructType, StructField, LongType, StringType, DoubleType


def timed(label, fn):
    start = time.time()
    result = fn()
    elapsed = time.time() - start
    print(f"  [{label}] took {elapsed:.2f}s")
    return result, elapsed


if __name__ == "__main__":
    spark = SparkSession.builder.appName("NetworkIntelligence-SP5").getOrCreate()

    raw_df = load_raw(spark)
    clean_df, _, _ = clean(raw_df)
    hourly_grid_summary = build_hourly_grid_summary(clean_df)

    # === EXPERIMENT 1: explain() on a hotspot aggregation ===
    print("\n=== EXPERIMENT 1: explain() on hotspot aggregation ===")
    hotspot_query = hourly_grid_summary.groupBy("grid_id").agg(spark_sum("total_activity"))
    hotspot_query.explain()
    print("Read the plan above: how many Exchange (shuffle) steps do you see?")

    # === EXPERIMENT 2: cache() timing comparison ===
    print("\n=== EXPERIMENT 2: cache() timing comparison ===")
    print("Without cache:")
    _, t1 = timed("run 1 (no cache)", lambda: hourly_grid_summary.groupBy("grid_id").sum("total_activity").count())
    _, t2 = timed("run 2 (no cache)", lambda: hourly_grid_summary.groupBy("grid_id").sum("total_activity").count())

    cached_df = hourly_grid_summary.cache()
    cached_df.count()
    print("With cache:")
    _, t3 = timed("run 1 (cached)", lambda: cached_df.groupBy("grid_id").sum("total_activity").count())
    _, t4 = timed("run 2 (cached)", lambda: cached_df.groupBy("grid_id").sum("total_activity").count())
    print(f"Compare run 2 no-cache ({t2:.2f}s) vs run 2 cached ({t4:.2f}s) -- is there a real difference?")
    cached_df.unpersist()

    # === EXPERIMENT 3: repartition and observe partition counts ===
    print("\n=== EXPERIMENT 3: repartition by date ===")
    print(f"Partitions before repartition: {hourly_grid_summary.rdd.getNumPartitions()}")
    repartitioned = hourly_grid_summary.repartition("date")
    print(f"Partitions after repartition('date'): {repartitioned.rdd.getNumPartitions()}")
    _, t5 = timed("aggregation on repartitioned data", lambda: repartitioned.groupBy("grid_id").sum("total_activity").count())
    print(f"Compare to unrepartitioned run 2 no-cache ({t2:.2f}s) above -- faster, slower, or about the same?")

    # === EXPERIMENT 4: column pruning ===
    print("\n=== EXPERIMENT 4: column pruning ===")
    print("Plan WITHOUT pruning (full table, then group):")
    hourly_grid_summary.groupBy("grid_id").sum("total_activity").explain()
    print("\nPlan WITH pruning (select only needed columns first):")
    pruned = hourly_grid_summary.select("grid_id", "total_activity")
    pruned.groupBy("grid_id").sum("total_activity").explain()
    print("Compare the two plans above -- do you see a difference in what gets scanned?")

    # === EXPERIMENT 5: broadcast vs standard join, SP4's grid lookup ===
    print("\n=== EXPERIMENT 5: broadcast join vs standard join (grid lookup) ===")
    lookup_rows = load_milan_grid_lookup(GEOJSON_PATH)
    lookup_schema = StructType([
        StructField("grid_id", LongType(), False),
        StructField("geometry_json", StringType(), False),
        StructField("centroid_lon", DoubleType(), False),
        StructField("centroid_lat", DoubleType(), False),
    ])
    lookup_path = "grid_lookup_tmp_sp5.jsonl"
    with open(lookup_path, "w") as f:
        for grid_id, geometry_json, centroid_lon, centroid_lat in lookup_rows:
            f.write(json.dumps({
                "grid_id": grid_id, "geometry_json": geometry_json,
                "centroid_lon": centroid_lon, "centroid_lat": centroid_lat,
            }) + "\n")
    grid_lookup = spark.read.schema(lookup_schema).json(lookup_path)

    print("Standard join plan:")
    hourly_grid_summary.join(grid_lookup, on="grid_id", how="left").explain()
    print("\nBroadcast join plan:")
    hourly_grid_summary.join(broadcast(grid_lookup), on="grid_id", how="left").explain()
    print("Look for 'SortMergeJoin' (standard) vs 'BroadcastHashJoin' (broadcast) above.")

    # === EXPERIMENT 6: discussion, not code ===
    print("\n=== EXPERIMENT 6: discussion, not code ===")
    print("Question to think about: this dataset is 7 files, ~15M rows, running")
    print("on ONE local machine (no real cluster). If you repartition into, say,")
    print("200 partitions, each partition holds only ~75,000 rows -- tiny. Spark")
    print("still has to schedule and coordinate 200 separate tasks for that, with")
    print("real overhead per task. On a genuine multi-machine cluster with far")
    print("more data, that overhead is worth it. On one laptop, it usually isn't.")

    print("\n=== Now write EXPERIMENT 7 yourself ===")
    print("Pick your 3 most interesting observations from experiments 1-6 above,")
    print("with the actual number/plan detail that supports each one.")

    spark.stop()