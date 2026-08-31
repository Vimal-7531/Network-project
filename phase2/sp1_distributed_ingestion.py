"""
SP1 -- Distributed Ingestion
==============================
Phase 2, Lab 1. Reads ALL daily telecom activity files at once with
Spark, instead of looping over files in pandas like Phase 1 did.

Preserves the RAW grain (timestamp + grid_id + country_code) --
Spark must NOT collapse country-code rows here. That grain transition
is a separate, later step (SP3), same as NP2's aggregate_to_grid_time().

Run:
    python sp1_distributed_ingestion.py
(reads every sms-call-internet-mi-*.csv file inside ../data/landing/)
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)
from pyspark.sql.functions import input_file_name, countDistinct, col

LANDING_DIR = "../data/landing"
FILE_GLOB = f"{LANDING_DIR}/sms-call-internet-mi-*.csv"
# NEVER "sms-call-internet-*.csv" -- the looser pattern would also match
# Trentino files if they were ever placed in this folder. Their cell IDs
# collide numerically with Milan's, corrupting everything downstream
# with no error message anywhere.


# ---------------------------------------------------------------------
# Step 1: SparkSession
# ---------------------------------------------------------------------
spark = SparkSession.builder.appName("NetworkIntelligence-SP1").getOrCreate()


# ---------------------------------------------------------------------
# Step 2/3: manual schema, NOT inferSchema.
# inferSchema forces Spark to read every file TWICE (once to guess
# types, once to actually load) -- expensive at real data volumes, and
# it can silently guess wrong on a column that happens to look numeric
# on day 1 but has a blank on day 2. A manual schema is one read, and
# is explicit about exactly what type every column is.
# ---------------------------------------------------------------------
raw_schema = StructType([
    StructField("datetime",    StringType(),  True),   # parsed to timestamp in SP2, not here
    StructField("CellID",      IntegerType(), True),   # grid_id, 1-10000
    StructField("countrycode", IntegerType(), True),   # raw grain dimension, not enriched here
    StructField("smsin",       DoubleType(),  True),   # proportional activity, not a literal count
    StructField("smsout",      DoubleType(),  True),
    StructField("callin",      DoubleType(),  True),
    StructField("callout",     DoubleType(),  True),
    StructField("internet",    DoubleType(),  True),   # proportional activity, not megabytes
])


# ---------------------------------------------------------------------
# Step 2 (cont.): read all matching daily files as ONE distributed
# DataFrame. header=True skips each file's own header row.
# ---------------------------------------------------------------------
raw_network_df = (
    spark.read
    .schema(raw_schema)
    .option("header", "true")
    .csv(FILE_GLOB)
)

# ---------------------------------------------------------------------
# Step 5: source filename for traceability -- required by SP1's
# acceptance criteria: "every row carries a populated input_file_name"
# ---------------------------------------------------------------------
raw_network_df = raw_network_df.withColumn("input_file_name", input_file_name())


# ---------------------------------------------------------------------
# Step 4: counts and reporting
# ---------------------------------------------------------------------
row_count = raw_network_df.count()
file_count = raw_network_df.select("input_file_name").distinct().count()
unique_grids = raw_network_df.select("CellID").distinct().count()
country_code_categories = raw_network_df.select("countrycode").distinct().count()
distinct_timestamps = raw_network_df.select("datetime").distinct().count()

print("--- SP1 Distributed Ingestion Report ---")
print(f"Row count:                 {row_count}")
print(f"File count:                {file_count}")
print(f"Unique grid_id values:     {unique_grids}")
print(f"Country-code categories:   {country_code_categories}")
print(f"Distinct timestamps:       {distinct_timestamps}")
print(f"Expected (files x 24):     {file_count * 24}")

# ---------------------------------------------------------------------
# Step 6: partition count -- explains how Spark actually splits the work
# ---------------------------------------------------------------------
num_partitions = raw_network_df.rdd.getNumPartitions()
print(f"\nNumber of partitions:      {num_partitions}")
print("Each partition is a chunk of the data Spark can process in")
print("parallel on a separate core/executor. Too few partitions means")
print("Spark can't use all your CPU cores; too many adds scheduling")
print("overhead for tiny chunks of work. Spark generally creates one")
print("partition per input file block by default when reading CSVs.")


# ---------------------------------------------------------------------
# Acceptance-criteria self-check -- fails loudly instead of silently
# ---------------------------------------------------------------------
assert distinct_timestamps == file_count * 24, \
    f"Expected {file_count * 24} distinct timestamps (files x 24), got {distinct_timestamps}"

grid_range_ok = raw_network_df.filter(
    (col("CellID") < 1) | (col("CellID") > 10000)
).count() == 0
assert grid_range_ok, "Some grid_id values fall outside 1-10000"

missing_filename = raw_network_df.filter(col("input_file_name").isNull()).count()
assert missing_filename == 0, "Some rows are missing input_file_name"

print("\nALL SP1 ACCEPTANCE CHECKS PASSED")

raw_network_df.show(5, truncate=False)

spark.stop()                                                                                                                                                                                                    