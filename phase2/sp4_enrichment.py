"""
SP4 -- Geospatial Enrichment Using the Milan Grid
====================================================
Phase 2, Lab 4. Joins hourly_grid_summary to milano-grid.geojson so
each grid gets real geographic coordinates.

*** KNOWN TRAP -- READ BEFORE RUNNING ***
Every feature in milano-grid.geojson has TWO identifiers:
    - a top-level "id"              -- 0-BASED  (feature id 0 = cell 1)
    - "properties": {"cellId": ...} -- 1-BASED   (this is grid_id)
Joining on the top-level "id" instead of "properties.cellId" produces
a join that reports 100% coverage and errors nowhere, but every single
grid renders on its NEIGHBOUR's polygon. A coverage percentage cannot
catch this -- that's why this script prints actual centroid coordinates
for a geographic spot-check, not just a coverage number.

The GeoJSON is loaded with plain Python (not Spark) -- it's one file,
10,000 features, comfortably fits in memory, and Spark adds nothing here.

Run:
    python sp4_enrichment.py
"""

import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import broadcast, col
from pyspark.sql.types import StructType, StructField, LongType, StringType, DoubleType

from sp2_cleaning import load_raw, clean
from sp3_aggregations import build_hourly_grid_summary

GEOJSON_PATH = "../data/reference/milano-grid.geojson"


def load_milan_grid_lookup(path):
    """Flatten milano-grid.geojson into a grid_id + geometry + centroid
    lookup. Uses properties.cellId, NEVER the top-level 0-based "id" --
    see the trap warning at the top of this file.
    """
    with open(path, "r") as f:
        geojson = json.load(f)

    assert geojson["type"] == "FeatureCollection", "Unexpected GeoJSON top-level type"

    rows = []
    for feature in geojson["features"]:
        # THIS is the line that matters: properties.cellId, not feature["id"]
        grid_id = feature["properties"]["cellId"]
        geometry = feature["geometry"]
        geometry_type = geometry["type"]

        if geometry_type == "Polygon":
            exterior_ring = geometry["coordinates"][0]
        elif geometry_type == "MultiPolygon":
            exterior_ring = geometry["coordinates"][0][0]
        else:
            raise ValueError(f"Unexpected geometry type: {geometry_type}")

        lons = [pt[0] for pt in exterior_ring]
        lats = [pt[1] for pt in exterior_ring]
        centroid_lon = sum(lons) / len(lons)
        centroid_lat = sum(lats) / len(lats)

        rows.append((
            int(grid_id),
            json.dumps(geometry),
            centroid_lon,
            centroid_lat,
        ))

    return rows


if __name__ == "__main__":
    spark = SparkSession.builder.appName("NetworkIntelligence-SP4").getOrCreate()

    lookup_rows = load_milan_grid_lookup(GEOJSON_PATH)
    print(f"Loaded {len(lookup_rows)} grid features from {GEOJSON_PATH}")

    lookup_schema = StructType([
    StructField("grid_id", LongType(), False),
        StructField("geometry_json", StringType(), False),
        StructField("centroid_lon", DoubleType(), False),
        StructField("centroid_lat", DoubleType(), False),
    ])

    # NOTE: we deliberately do NOT use spark.createDataFrame(lookup_rows, ...)
    # here. Converting a Python list directly into a distributed DataFrame
    # spins up a background Python worker process, and on some locked-down
    # Windows/corporate machines that worker cannot connect back to Spark
    # (blocked by firewall/antivirus), causing "Python worker failed to
    # connect back" errors. Writing to a small file and having Spark READ
    # it uses the exact same file-based path that already works for your
    # CSV files -- no Python worker spawn required.
    lookup_jsonl_path = "grid_lookup_tmp.jsonl"
    with open(lookup_jsonl_path, "w") as f:
        for grid_id, geometry_json, centroid_lon, centroid_lat in lookup_rows:
            record = {
                "grid_id": grid_id,
                "geometry_json": geometry_json,
                "centroid_lon": centroid_lon,
                "centroid_lat": centroid_lat,
            }
            f.write(json.dumps(record) + "\n")

    grid_lookup = spark.read.schema(lookup_schema).json(lookup_jsonl_path)
    lookup_count = grid_lookup.count()
    lookup_distinct = grid_lookup.select("grid_id").distinct().count()
    assert lookup_count == lookup_distinct, \
        f"grid_lookup has duplicate grid_id keys: {lookup_count} rows, {lookup_distinct} distinct"
    print(f"Grid lookup: {lookup_count} rows, {lookup_distinct} distinct grid_id -- no duplicate keys")

    raw_df = load_raw(spark)
    clean_network_df, _, _ = clean(raw_df)
    hourly_grid_summary = build_hourly_grid_summary(clean_network_df)

    activity_row_count_before = hourly_grid_summary.count()
    distinct_grids_before = hourly_grid_summary.select("grid_id").distinct().count()

    grid_activity_geo_df = hourly_grid_summary.join(
        broadcast(grid_lookup), on="grid_id", how="left"
    )

    activity_row_count_after = grid_activity_geo_df.count()
    unmatched = grid_activity_geo_df.filter(col("geometry_json").isNull())
    unmatched_grid_ids = [r["grid_id"] for r in unmatched.select("grid_id").distinct().collect()]
    coverage_pct = 100 * (distinct_grids_before - len(unmatched_grid_ids)) / distinct_grids_before

    print("\n--- SP4 Join Validation (numeric) ---")
    print(f"Row count before join:  {activity_row_count_before}")
    print(f"Row count after join:   {activity_row_count_after}")
    print(f"Distinct grids before:  {distinct_grids_before}")
    print(f"Unmatched grid_id list: {unmatched_grid_ids}")
    print(f"Enrichment coverage:    {coverage_pct:.2f}%")

    assert activity_row_count_after == activity_row_count_before, \
        "Row count changed after the left join -- the lookup likely has duplicate keys"
    assert len(unmatched_grid_ids) == 0, f"{len(unmatched_grid_ids)} grids have no matching geometry"
    assert coverage_pct == 100.0, f"Coverage is {coverage_pct:.2f}%, expected 100%"
    print("Numeric checks passed: row count unchanged, 0 unmatched grids, 100% coverage.")

    print("\n--- SP4 Geographic Spot-Check (coverage % alone does NOT prove this) ---")
    spot_check_grids = [1, 2, 5161]
    centroids = (
        grid_lookup.filter(col("grid_id").isin(spot_check_grids))
        .orderBy("grid_id")
        .collect()
    )
    for row in centroids:
        print(f"grid_id={row['grid_id']:5d}  centroid = (lon={row['centroid_lon']:.5f}, lat={row['centroid_lat']:.5f})")
    print("\nCheck by hand: both values should fall inside roughly lat 45.40-45.53, lon 9.04-9.28")
    print("(Milan's real bounding box). grid_id 1 and grid_id 2's centroids should be CLOSE to")
    print("each other (adjacent cells) -- not identical, and not far apart.")

    print("\n--- SP4 Execution Plan Comparison ---")
    print("Standard join plan (no broadcast hint):")
    hourly_grid_summary.join(grid_lookup, on="grid_id", how="left").explain()
    print("\nBroadcast join plan (what we actually used):")
    grid_activity_geo_df.explain()
    print("\nLook for 'BroadcastHashJoin' vs 'SortMergeJoin' in the two plans above --")
    print("broadcast sends the whole 10,000-row lookup to every executor instead of")
    print("shuffling millions of activity rows across the network to match it.")

    grid_activity_geo_df = grid_activity_geo_df.select(
        "timestamp", "grid_id", "sms_in", "sms_out", "call_in", "call_out",
        "internet_activity", "total_activity", "centroid_lon", "centroid_lat", "geometry_json",
    )

    print("\nSample of grid_activity_geo_df:")
    grid_activity_geo_df.orderBy("grid_id", "timestamp").show(5, truncate=60)

    top_hotspots_geo = (
        grid_activity_geo_df.groupBy("grid_id", "centroid_lon", "centroid_lat")
        .sum("total_activity")
        .withColumnRenamed("sum(total_activity)", "total_activity")
        .orderBy(col("total_activity").desc())
        .limit(10)
    )
    print("\nTop 10 high-activity grids with geometry:")
    top_hotspots_geo.show(10, truncate=False)

    spark.stop()