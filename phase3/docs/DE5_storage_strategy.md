# DE5 — Storage Strategy & Data Zones

## 1. Objective

Define the storage strategy for the Network Operations & Predictive Intelligence pipeline.

The pipeline separates data into raw, processed, and analytics zones.

## 2. Data Zones

| Zone | Data | Format | Purpose |
|---|---|---|---|
| Raw | Original daily telecom CSV files | CSV | Immutable source data and auditability |
| Processed | Cleaned network activity | Parquet | Efficient storage and distributed processing |
| Analytics | Hourly grid summaries | Parquet | Efficient analytical querying |
| Analytics | Dashboard summary | CSV | Simple consumption by dashboard/API |
| Reference | Milan grid geometry | GeoJSON | Static geographic reference data |

## 3. Raw Zone

Location:

data/raw/

Format:

CSV

The raw zone contains the original daily telecom activity files.

Example:

sms-call-internet-mi-2013-11-01.csv

The raw data should remain unchanged after successful ingestion.

Benefits:

- Preserves the original source
- Supports auditing
- Allows reprocessing
- Makes ingestion failures easier to investigate
- Provides a reliable source for downstream processing

## 4. Processed Zone

Location:

data/processed/activity/

Format:

Parquet

The processed zone contains cleaned and standardized activity data.

The data includes canonical fields such as:

- timestamp
- grid_id
- country_code
- sms_in
- sms_out
- call_in
- call_out
- internet_activity
- total_sms
- total_calls
- total_activity

Parquet is preferred because it is columnar and efficient for Spark processing.

The processed activity is partitioned by date.

## 5. Analytics Zone

Location:

data/analytics/

Primary format:

Parquet

The hourly grid analytics output contains aggregated network activity by grid and hourly interval.

It contains derived measures such as:

- total_sms
- total_calls
- internet_activity
- total_activity
- internet_share

Parquet provides efficient analytical reads and avoids repeatedly scanning unnecessary columns.

## 6. Dashboard Output

The dashboard summary is stored as CSV because it is a small, simple consumption-oriented output.

Location:

data/analytics/dashboard_summary/

This output can easily be consumed by lightweight applications or inspected manually.

## 7. Reference Data

Location:

data/reference/

The Milan grid geometry is stored as GeoJSON.

File:

milano-grid.geojson

This is static reference data rather than generated pipeline output.

The geographic join uses:

properties.cellId → grid_id

The top-level GeoJSON id must not be used because it is zero-based while properties.cellId is one-based.

## 8. Why Different Formats Are Used

### CSV

Best suited for:

- Source files
- Human inspection
- Simple interchange

Limitations:

- Larger storage size
- Slower analytical reads
- No columnar optimization
- Requires schema interpretation

### Parquet

Best suited for:

- Processed data
- Analytics
- Spark workloads

Advantages:

- Columnar storage
- Efficient reads
- Compression
- Schema preservation
- Good Spark integration

### GeoJSON

Best suited for:

- Geographic reference data
- Polygon geometry
- Browser/map consumption

## 9. Storage Flow

Raw CSV
    |
    v
data/raw/
    |
    v
PySpark cleaning
    |
    v
data/processed/activity/
    |
    v
PySpark aggregation
    |
    v
data/analytics/
    |
    +---- hourly_grid_summary/
    |
    +---- dashboard_summary/

Static reference:
data/reference/milano-grid.geojson

## 10. Data Zone Rules

1. Raw data is preserved and should not be modified.
2. Processing logic reads from the raw zone.
3. Cleaned activity is written to the processed zone.
4. Aggregated data is written to the analytics zone.
5. Reference GeoJSON remains separate from generated outputs.
6. Analytics outputs should only be published after successful processing.
7. Downstream consumers should use processed or analytics data rather than raw files.

## 11. Final Storage Decision

The project uses a simple three-zone storage architecture:

Raw → CSV
Processed → Parquet
Analytics → Parquet

CSV is retained where human-readable interchange is useful, while Parquet is used for Spark processing and analytical workloads.

GeoJSON remains a separate reference-data format for geographic enrichment.