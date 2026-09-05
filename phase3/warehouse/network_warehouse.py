import os
import json
import sqlite3
from pyspark.sql import SparkSession


PROJECT_ROOT = "/mnt/c/Network-project"
HOURLY_SUMMARY_PATH = f"{PROJECT_ROOT}/data/analytics/hourly_grid_summary"
GEOJSON_PATH = f"{PROJECT_ROOT}/data/reference/milano-grid.geojson"
DATABASE_PATH = f"{PROJECT_ROOT}/data/warehouse/network_analytics.db"


def create_spark():
    return (
        SparkSession.builder
        .appName("NetworkIntelligence-DE6")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def create_schema(conn):
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript("""
        DROP TABLE IF EXISTS fact_network_activity;
        DROP TABLE IF EXISTS dim_time;
        DROP TABLE IF EXISTS dim_grid;

        CREATE TABLE dim_time (
            time_key INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL UNIQUE,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL,
            day_of_week TEXT NOT NULL
        );

        CREATE TABLE dim_grid (
            grid_id INTEGER PRIMARY KEY,
            centroid_lat REAL,
            centroid_lon REAL,
            geometry_reference TEXT
        );

        CREATE TABLE fact_network_activity (
            activity_key INTEGER PRIMARY KEY AUTOINCREMENT,
            grid_id INTEGER NOT NULL,
            time_key INTEGER NOT NULL,
            sms_in REAL,
            sms_out REAL,
            call_in REAL,
            call_out REAL,
            internet_activity REAL,
            total_sms REAL,
            total_calls REAL,
            total_activity REAL,
            internet_share REAL,
            FOREIGN KEY (grid_id) REFERENCES dim_grid(grid_id),
            FOREIGN KEY (time_key) REFERENCES dim_time(time_key)
        );

        CREATE INDEX idx_fact_grid_time
        ON fact_network_activity(grid_id, time_key);

        CREATE INDEX idx_fact_time
        ON fact_network_activity(time_key);
    """)


def load_dim_grid(conn):
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    rows = []

    for feature in geojson["features"]:
        properties = feature.get("properties", {})
        grid_id = properties.get("cellId")

        if grid_id is None:
            continue

        geometry = feature.get("geometry")

        geometry_reference = json.dumps({
            "source": "milano-grid.geojson",
            "cellId": grid_id,
            "geometry_type": geometry.get("type") if geometry else None
        })

        coordinates = geometry.get("coordinates") if geometry else None

        centroid_lon = None
        centroid_lat = None

        if geometry and geometry.get("type") == "Polygon":
            ring = coordinates[0]

            lons = [point[0] for point in ring]
            lats = [point[1] for point in ring]

            centroid_lon = sum(lons) / len(lons)
            centroid_lat = sum(lats) / len(lats)

        rows.append(
            (
                int(grid_id),
                centroid_lat,
                centroid_lon,
                geometry_reference
            )
        )

    conn.executemany(
        """
        INSERT INTO dim_grid
        (
            grid_id,
            centroid_lat,
            centroid_lon,
            geometry_reference
        )
        VALUES (?, ?, ?, ?)
        """,
        rows
    )

    print(f"dim_grid rows loaded: {len(rows)}")


def load_dim_time(conn, df):
    rows = []

    for row in df.select(
        "timestamp",
        "date",
        "hour",
        "day_of_week"
    ).distinct().orderBy("timestamp").toLocalIterator():

        rows.append(
            (
                row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                row["date"].strftime("%Y-%m-%d"),
                int(row["hour"]),
                row["day_of_week"]
            )
        )

    conn.executemany(
        """
        INSERT INTO dim_time
        (
            timestamp,
            date,
            hour,
            day_of_week
        )
        VALUES (?, ?, ?, ?)
        """,
        rows
    )

    print(f"dim_time rows loaded: {len(rows)}")


def load_fact(conn, df):
    time_lookup = {
        row[1]: row[0]
        for row in conn.execute(
            "SELECT time_key, timestamp FROM dim_time"
        ).fetchall()
    }

    batch = []
    total = 0

    columns = [
        "grid_id",
        "timestamp",
        "sms_in",
        "sms_out",
        "call_in",
        "call_out",
        "internet_activity",
        "total_sms",
        "total_calls",
        "total_activity",
        "internet_share"
    ]

    for row in df.select(*columns).toLocalIterator():

        timestamp = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        time_key = time_lookup[timestamp]

        batch.append(
            (
                int(row["grid_id"]),
                time_key,
                float(row["sms_in"]),
                float(row["sms_out"]),
                float(row["call_in"]),
                float(row["call_out"]),
                float(row["internet_activity"]),
                float(row["total_sms"]),
                float(row["total_calls"]),
                float(row["total_activity"]),
                float(row["internet_share"])
            )
        )

        if len(batch) >= 5000:
            conn.executemany(
                """
                INSERT INTO fact_network_activity
                (
                    grid_id,
                    time_key,
                    sms_in,
                    sms_out,
                    call_in,
                    call_out,
                    internet_activity,
                    total_sms,
                    total_calls,
                    total_activity,
                    internet_share
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch
            )

            total += len(batch)
            batch = []

            if total % 100000 == 0:
                print(f"Fact rows loaded: {total}")

    if batch:
        conn.executemany(
            """
            INSERT INTO fact_network_activity
            (
                grid_id,
                time_key,
                sms_in,
                sms_out,
                call_in,
                call_out,
                internet_activity,
                total_sms,
                total_calls,
                total_activity,
                internet_share
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch
        )

        total += len(batch)

    print(f"fact_network_activity rows loaded: {total}")


def validate(conn, source_row_count):
    fact_count = conn.execute(
        "SELECT COUNT(*) FROM fact_network_activity"
    ).fetchone()[0]

    grid_count = conn.execute(
        "SELECT COUNT(*) FROM dim_grid"
    ).fetchone()[0]

    distinct_grid_count = conn.execute(
        "SELECT COUNT(DISTINCT grid_id) FROM fact_network_activity"
    ).fetchone()[0]

    duplicate_grid_keys = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT grid_id
            FROM dim_grid
            GROUP BY grid_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    geometry_columns = conn.execute(
        "PRAGMA table_info(fact_network_activity)"
    ).fetchall()

    geometry_present = any(
        "geometry" in column[1].lower()
        for column in geometry_columns
    )

    aggregate = conn.execute(
        """
        SELECT
            COUNT(*) AS rows,
            SUM(total_sms) AS total_sms,
            SUM(total_calls) AS total_calls,
            SUM(internet_activity) AS internet_activity,
            SUM(total_activity) AS total_activity
        FROM fact_network_activity
        """
    ).fetchone()

    print()
    print("DE6 VALIDATION")
    print("=" * 50)
    print(f"Source hourly_grid_summary rows : {source_row_count}")
    print(f"Fact rows                       : {fact_count}")
    print(f"dim_grid rows                   : {grid_count}")
    print(f"Distinct fact grid IDs          : {distinct_grid_count}")
    print(f"Duplicate dim_grid keys         : {duplicate_grid_keys}")
    print(f"Geometry in fact table          : {geometry_present}")
    print()
    print("Fact aggregate:")
    print(f"Rows                            : {aggregate[0]}")
    print(f"Total SMS                       : {aggregate[1]}")
    print(f"Total calls                     : {aggregate[2]}")
    print(f"Internet activity               : {aggregate[3]}")
    print(f"Total activity                  : {aggregate[4]}")
    print("=" * 50)

    if fact_count != source_row_count:
        raise ValueError("Fact row count does not match source row count")

    if grid_count != distinct_grid_count:
        raise ValueError("dim_grid row count does not match distinct fact grids")

    if duplicate_grid_keys != 0:
        raise ValueError("Duplicate grid keys found")

    if geometry_present:
        raise ValueError("Geometry column found in fact table")

    print("DE6 validation PASSED")


def main():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    spark = create_spark()

    try:
        print("Reading hourly_grid_summary...")
        df = spark.read.parquet(HOURLY_SUMMARY_PATH)

        source_row_count = df.count()

        print(f"Source rows: {source_row_count}")

        conn = sqlite3.connect(DATABASE_PATH)

        try:
            conn.execute("BEGIN")

            create_schema(conn)
            load_dim_grid(conn)
            load_dim_time(conn, df)
            load_fact(conn, df)

            conn.commit()

            validate(conn, source_row_count)

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    finally:
        spark.stop()


if __name__ == "__main__":
    main()