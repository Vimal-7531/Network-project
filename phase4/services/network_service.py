import ast
import csv
import re
import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd

from fastapi import HTTPException
from phase6.ml.model_service import predict_risk

PROJECT_ROOT = Path(r"C:\Users\vimalraj.ck\network_project")
ANOMALY_PATH = PROJECT_ROOT / "phase6" / "ml" / "ml4_output" / "network_anomaly_scores.csv"
ACTIVITY_PATH = PROJECT_ROOT / "data" / "analytics" / "hourly_grid_summary"
PIPELINE_STATUS_PATH = (
    PROJECT_ROOT / "logs" / "pipeline_quality_status.csv"
)
DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "warehouse"
    / "network_analytics.db"
)

def get_pipeline_status():
    if not PIPELINE_STATUS_PATH.exists():
        raise RuntimeError(
            f"Pipeline status file not found: {PIPELINE_STATUS_PATH}"
        )

    with open(
        PIPELINE_STATUS_PATH,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise RuntimeError("Pipeline status file is empty")

    valid_rows = [
        row for row in rows
        if row.get("timestamp")
    ]

    if not valid_rows:
        raise RuntimeError("No valid pipeline status records found")

    latest_row = max(
        valid_rows,
        key=lambda row: row["timestamp"]
    )

    run_id = latest_row.get("run_id") or "unknown"

    try:
        run_timestamp = datetime.fromisoformat(
            latest_row["timestamp"]
        )
    except ValueError as exc:
        raise RuntimeError(
            "Invalid pipeline run timestamp"
        ) from exc

    overall_status = (
        latest_row.get("overall_status") or "UNKNOWN"
    ).upper()

    task_status = {}

    reason_value = latest_row.get("reason") or ""

    match = re.search(
        r"(\{.*\})\s*$",
        reason_value
    )

    if match:
        try:
            parsed = ast.literal_eval(match.group(1))

            if isinstance(parsed, dict):
                task_status = {
                    str(key): (
                        None if value is None
                        else str(value)
                    )
                    for key, value in parsed.items()
                }
        except (ValueError, SyntaxError):
            task_status = {}

    def parse_int(value):
        if value in (None, ""):
            return None
        return int(value)

    rows_in = parse_int(
        latest_row.get("rows_in")
    )

    rows_rejected = parse_int(
        latest_row.get("rows_rejected")
    )

    nulls_handled = parse_int(
        latest_row.get("nulls_handled")
    )

    rows_published = parse_int(
        latest_row.get("rows_published")
    )

    as_of = None

    latest_as_of_value = (
        latest_row.get("as_of_reason") or ""
    ).strip()

    if latest_as_of_value:
        try:
            as_of = datetime.fromisoformat(
                latest_as_of_value
            )
        except ValueError:
            as_of = None

    if as_of is None:
        successful_rows = [
            row
            for row in valid_rows
            if (
                (row.get("overall_status") or "").upper()
                == "SUCCESS"
                and (row.get("as_of_reason") or "").strip()
            )
        ]

        if successful_rows:
            latest_success = max(
                successful_rows,
                key=lambda row: row["timestamp"]
            )

            try:
                as_of = datetime.fromisoformat(
                    latest_success["as_of_reason"]
                )
            except ValueError:
                as_of = None

    healthy = overall_status == "SUCCESS"

    reasons = []

    if not healthy:
        reasons.append(
            f"Latest pipeline run status is {overall_status}"
        )

        failed_tasks = [
            key
            for key, value in task_status.items()
            if value not in (None, "success")
        ]

        if failed_tasks:
            reasons.append(
                "Failed or incomplete tasks: "
                + ", ".join(failed_tasks)
            )
    freshness_hours = None

    if as_of is not None:
        freshness_hours = (
            datetime.now() - as_of
        ).total_seconds() / 3600

    if not healthy:
        freshness_indicator = "STALE_OR_UNHEALTHY"
    elif freshness_hours is None:
        freshness_indicator = "UNKNOWN"
    elif freshness_hours <= 24:
        freshness_indicator = "FRESH"
    else:
        freshness_indicator = "STALE"

    return {
        "healthy": healthy,
        "reasons": reasons,
        "run_id": run_id,
        "run_timestamp": run_timestamp,
        "overall_status": overall_status,
        "task_status": task_status,
        "rows_in": rows_in,
        "rows_rejected": rows_rejected,
        "nulls_handled": nulls_handled,
        "rows_published": rows_published,
        "as_of": as_of,
        "freshness_hours": freshness_hours,
        "freshness_indicator": freshness_indicator
    }
def get_latest_as_of():
    if not DATABASE_PATH.exists():
        raise RuntimeError(
            f"Warehouse database not found: {DATABASE_PATH}"
        )

    conn = None

    try:
        conn = sqlite3.connect(DATABASE_PATH)

        row = conn.execute(
            """
            SELECT MAX(timestamp)
            FROM dim_time
            """
        ).fetchone()

        if row is None or row[0] is None:
            raise RuntimeError(
                "No analytics data available"
            )

        return datetime.fromisoformat(row[0])

    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Warehouse query failed: {exc}"
        ) from exc

    finally:
        if conn is not None:
            conn.close()


def get_network_summary(as_of=None):
    if not DATABASE_PATH.exists():
        raise RuntimeError(
            f"Warehouse database not found: {DATABASE_PATH}"
        )

    conn = None

    try:
        conn = sqlite3.connect(DATABASE_PATH)

        if as_of is None:
            row = conn.execute(
                """
                SELECT MAX(t.timestamp)
                FROM fact_network_activity f
                JOIN dim_time t
                    ON f.time_key = t.time_key
                """
            ).fetchone()

            if row is None or row[0] is None:
                raise RuntimeError(
                    "No analytics data available"
                )

            effective_as_of = datetime.fromisoformat(row[0])

        else:
            effective_as_of = as_of

        timestamp_value = effective_as_of.strftime("%Y-%m-%d %H:%M:%S")
        summary = conn.execute(
            """
            SELECT
                COALESCE(SUM(f.total_activity), 0),
                COUNT(DISTINCT f.grid_id)
            FROM fact_network_activity f
            JOIN dim_time t
                ON f.time_key = t.time_key
            WHERE t.timestamp = ?
            """,
            (timestamp_value,)
        ).fetchone()

        if summary is None:
            raise RuntimeError(
                "Unable to calculate network summary"
            )

        total_activity = float(summary[0])
        active_grids = int(summary[1])

        peak_row = conn.execute(
            """
            SELECT t.hour
            FROM fact_network_activity f
            JOIN dim_time t
                ON f.time_key = t.time_key
            WHERE t.timestamp = ?
            GROUP BY t.hour
            ORDER BY SUM(f.total_activity) DESC
            LIMIT 1
            """,
            (timestamp_value,)
        ).fetchone()

        if peak_row is None:
            raise RuntimeError(
                "Unable to determine peak hour"
            )

        peak_hour = int(peak_row[0])

        top_grid_row = conn.execute(
            """
            SELECT f.grid_id
            FROM fact_network_activity f
            JOIN dim_time t
                ON f.time_key = t.time_key
            WHERE t.timestamp = ?
            GROUP BY f.grid_id
            ORDER BY SUM(f.total_activity) DESC
            LIMIT 1
            """,
            (timestamp_value,)
        ).fetchone()

        if top_grid_row is None:
            raise RuntimeError(
                "Unable to determine top grid"
            )

        top_grid = int(top_grid_row[0])

        return {
            "total_activity": total_activity,
            "active_grids": active_grids,
            "peak_hour": peak_hour,
            "top_grid": top_grid,
            "as_of": effective_as_of
        }

    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Warehouse query failed: {exc}"
        ) from exc

    finally:
        if conn is not None:
            conn.close()


def get_grid_activity(
    grid_id,
    date=None,
    hour=None,
    as_of=None
):
    if grid_id < 1 or grid_id > 10000:
        raise LookupError(
            f"Grid {grid_id} does not exist"
        )

    if not DATABASE_PATH.exists():
        raise RuntimeError(
            f"Warehouse database not found: {DATABASE_PATH}"
        )

    conn = None

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row

        grid_exists = conn.execute(
            """
            SELECT 1
            FROM dim_grid
            WHERE grid_id = ?
            """,
            (grid_id,)
        ).fetchone()

        if grid_exists is None:
            raise LookupError(
                f"Grid {grid_id} does not exist"
            )

        if as_of is None:
            row = conn.execute(
                """
                SELECT MAX(t.timestamp)
                FROM fact_network_activity f
                JOIN dim_time t
                    ON f.time_key = t.time_key
                WHERE f.grid_id = ?
                """,
                (grid_id,)
            ).fetchone()

            if row is None or row[0] is None:
                raise RuntimeError(
                    "No analytics data available"
                )

            effective_as_of = datetime.fromisoformat(row[0])

        else:
            effective_as_of = (
                datetime.fromisoformat(as_of)
                if isinstance(as_of, str)
                else as_of
            )

        if date is None and hour is None and as_of is None:
            rows = conn.execute(
                """
                SELECT
                    t.timestamp,
                    f.sms_in,
                    f.sms_out,
                    f.call_in,
                    f.call_out,
                    f.internet_activity,
                    f.total_activity
                FROM fact_network_activity f
                JOIN dim_time t
                    ON f.time_key = t.time_key
                WHERE f.grid_id = ?
                  AND t.timestamp <= ?
                ORDER BY t.timestamp DESC
                LIMIT 24
                """,
                (
                    grid_id,
                    effective_as_of.isoformat()
                )
            ).fetchall()

            rows = list(reversed(rows))

        else:
            query = """
                SELECT
                    t.timestamp,
                    f.sms_in,
                    f.sms_out,
                    f.call_in,
                    f.call_out,
                    f.internet_activity,
                    f.total_activity
                FROM fact_network_activity f
                JOIN dim_time t
                    ON f.time_key = t.time_key
                WHERE f.grid_id = ?
                  AND t.timestamp <= ?
            """

            params = [
                grid_id,
                effective_as_of.isoformat()
            ]

            if date is not None:
                query += " AND t.date = ?"
                params.append(date)

            if hour is not None:
                query += " AND t.hour = ?"
                params.append(hour)

            if as_of is not None:
                query += " AND t.timestamp = ?"
                params.append(
                    effective_as_of.isoformat()
                )

            query += " ORDER BY t.timestamp"

            rows = conn.execute(
                query,
                params
            ).fetchall()

        return [
            {
                "timestamp": datetime.fromisoformat(
                    row["timestamp"]
                ),
                "sms_in": float(row["sms_in"]),
                "sms_out": float(row["sms_out"]),
                "call_in": float(row["call_in"]),
                "call_out": float(row["call_out"]),
                "internet_activity": float(
                    row["internet_activity"]
                ),
                "total_activity": float(
                    row["total_activity"]
                )
            }
            for row in rows
        ]

    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Warehouse query failed: {exc}"
        ) from exc

    finally:
        if conn is not None:
            conn.close()

def find_alert_file():
    candidates = [
        PROJECT_ROOT / "data" / "analytics" / "network_alerts.csv",
        PROJECT_ROOT / "data" / "analytics" / "network_alerts.json",
        PROJECT_ROOT / "phase3" / "analytics" / "network_alerts.csv",
        PROJECT_ROOT / "phase3" / "analytics" / "network_alerts.json",
        PROJECT_ROOT / "data" / "network_alerts.csv",
        PROJECT_ROOT / "data" / "network_alerts.json"
    ]

    for path in candidates:
        if path.exists():
            return path

    for path in PROJECT_ROOT.rglob("network_alerts.csv"):
        return path

    for path in PROJECT_ROOT.rglob("network_alerts.json"):
        return path

    return None


def load_np3_alerts():
    alert_file = find_alert_file()

    if alert_file is None:
        raise RuntimeError(
            "NP3 alert output not found"
        )

    try:
        if alert_file.suffix.lower() == ".csv":
            with open(
                alert_file,
                "r",
                encoding="utf-8",
                newline=""
            ) as file:
                return list(csv.DictReader(file))

        with open(
            alert_file,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            if "data" in data:
                return data["data"]

            if "alerts" in data:
                return data["alerts"]

        if isinstance(data, list):
            return data

        raise RuntimeError(
            "Invalid NP3 alert output format"
        )

    except (OSError, json.JSONDecodeError, csv.Error) as exc:
        raise RuntimeError(
            f"Unable to read NP3 alert output: {exc}"
        ) from exc


def normalize_alert(row):
    alert_type = str(
        row.get("alert_type", "")
    ).strip()

    severity_map = {
        "HIGH_ACTIVITY": "HIGH",
        "ACTIVITY_SPIKE": "MEDIUM",
        "ACTIVITY_DROP": "LOW"
    }

    severity = severity_map.get(
        alert_type,
        "MEDIUM"
    )

    timestamp = datetime.fromisoformat(
        str(row["timestamp"]).replace("Z", "")
    )

    return {
        "grid_id": int(row["grid_id"]),
        "timestamp": timestamp,
        "alert_type": alert_type,
        "current_activity": float(
            row["current_activity"]
        ),
        "baseline_activity": float(
            row["baseline_activity"]
        ),
        "severity": severity,
        "reason": str(row["reason"]),
        "risk_score": None,
        "risk_level": None,
        "model_version": None
    }


def load_ml6_risk_scores():
    risk_path = (
        PROJECT_ROOT
        / "data"
        / "analytics"
        / "network_risk_scores"
    )

    if not risk_path.exists():
        raise RuntimeError(
            f"ML6 risk scores not found: {risk_path}"
        )

    risk = pd.read_parquet(risk_path)

    required_columns = [
        "grid_id",
        "timestamp",
        "risk_score",
        "risk_level",
        "model_version"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in risk.columns
    ]

    if missing_columns:
        raise RuntimeError(
            f"ML6 risk scores are missing columns: {missing_columns}"
        )

    risk["timestamp"] = pd.to_datetime(
        risk["timestamp"]
    )

    if risk.duplicated(
        subset=["grid_id", "timestamp"]
    ).any():
        raise RuntimeError(
            "ML6 risk scores contain duplicate grid/timestamp records."
        )

    return risk

def get_network_alerts(
    limit=50,
    severity=None,
    as_of=None
):
    effective_as_of = (
        as_of
        if as_of is not None
        else get_latest_as_of()
    )

    alerts = [
        normalize_alert(row)
        for row in load_np3_alerts()
    ]
    risk_scores = load_ml6_risk_scores()

    risk_map = {
        (
            int(row["grid_id"]),
            pd.Timestamp(row["timestamp"]).date(),
            pd.Timestamp(row["timestamp"]).hour
        ): row
        for _, row in risk_scores.iterrows()
    }
    alerts = [
        alert
        for alert in alerts
        if alert["timestamp"] <= effective_as_of
    ]
    for alert in alerts:
        alert_timestamp = pd.Timestamp(
            alert["timestamp"]
        )

        risk = risk_map.get(
            (
                int(alert["grid_id"]),
                alert_timestamp.date(),
                alert_timestamp.hour
            )
        )

        if risk is not None:
            alert["risk_score"] = float(
                risk["risk_score"]
            )
            alert["risk_level"] = str(
                risk["risk_level"]
            )
            alert["model_version"] = str(
                risk["model_version"]
            )
    if severity is not None:
        alerts = [
            alert
            for alert in alerts
            if alert["severity"].upper()
            == severity.upper()
        ]

    severity_order = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    alerts.sort(
        key=lambda x: (
            x["timestamp"],
            severity_order.get(
                x["severity"],
                0
            ),
            x["grid_id"],
            x["alert_type"]
        ),
        reverse=True
    )

    for alert in alerts:
        risk = risk_map.get(
            (
                int(alert["grid_id"]),
                pd.Timestamp(alert["timestamp"])
            )
        )

    if risk is not None:
        alert["risk_score"] = float(
            risk["risk_score"]
        )
        alert["risk_level"] = str(
            risk["risk_level"]
        )
        alert["model_version"] = str(
            risk["model_version"]
        )
    else:
        alert["risk_score"] = None
        alert["risk_level"] = None
        alert["model_version"] = None

    return {
        "as_of": effective_as_of,
        "data": alerts[:limit]
    }


def get_network_hotspots(
    limit=50,
    severity=None,
    as_of=None
):
    effective_as_of = (
        as_of
        if as_of is not None
        else get_latest_as_of()
    )

    timestamp_value = effective_as_of.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    if not DATABASE_PATH.exists():
        raise RuntimeError(
            f"Warehouse database not found: {DATABASE_PATH}"
        )

    conn = None

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                f.grid_id,
                t.timestamp,
                f.total_activity
            FROM fact_network_activity f
            JOIN dim_time t
                ON f.time_key = t.time_key
            WHERE t.timestamp = ?
            ORDER BY
                f.total_activity DESC,
                f.grid_id ASC
            LIMIT ?
            """,
            (
                timestamp_value,
                limit
            )
        ).fetchall()

        alerts = load_np3_alerts()

        risk_scores = load_ml6_risk_scores()

        risk_map = {
            (
                int(row["grid_id"]),
                pd.Timestamp(row["timestamp"]).date(),
                pd.Timestamp(row["timestamp"]).hour
            ): row
            for _, row in risk_scores.iterrows()
        }

        alert_map = {}

        for row in alerts:
            normalized = normalize_alert(row)

            if (
                normalized["timestamp"]
                == effective_as_of
            ):
                alert_map[
                    normalized["grid_id"]
                ] = normalized

        data = []

        for row in rows:
            grid_id = int(row["grid_id"])

            alert = alert_map.get(grid_id)

            if (
                severity is not None
                and (
                    alert is None
                    or alert["severity"].upper()
                    != severity.upper()
                )
            ):
                continue

            data.append(
                {
                    "grid_id": grid_id,
                    "timestamp": datetime.fromisoformat(
                        row["timestamp"]
                    ),
                    "total_activity": float(
                        row["total_activity"]
                    ),
                    "status": (
                        alert["severity"]
                        if alert
                        else "NORMAL"
                    ),
                    "reason": (
                        alert["reason"]
                        if alert
                        else "Highest activity for the selected hour."
                    ),
                    "risk_score": (
                        float(
                            risk_map[
                                (
                                    grid_id,
                                    pd.Timestamp(row["timestamp"]).date(),
                                    pd.Timestamp(row["timestamp"]).hour
                                )
                            ]["risk_score"]
                        )
                        if (
                            grid_id,
                            pd.Timestamp(row["timestamp"]).date(),
                            pd.Timestamp(row["timestamp"]).hour
                        ) in risk_map
                        else None
                    ),
                    "risk_level": (
                        str(
                            risk_map[
                                (
                                    grid_id,
                                    pd.Timestamp(row["timestamp"]).date(),
                                    pd.Timestamp(row["timestamp"]).hour
                                )
                            ]["risk_level"]
                        )
                        if (
                            grid_id,
                            pd.Timestamp(row["timestamp"]).date(),
                            pd.Timestamp(row["timestamp"]).hour
                        ) in risk_map
                        else None
                    ),
                    "model_version": (
                        str(
                            risk_map[
                                (
                                    grid_id,
                                    pd.Timestamp(row["timestamp"]).date(),
                                    pd.Timestamp(row["timestamp"]).hour
                                )
                            ]["model_version"]
                        )
                        if (
                            grid_id,
                            pd.Timestamp(row["timestamp"]).date(),
                            pd.Timestamp(row["timestamp"]).hour
                        ) in risk_map
                        else None
                    )
                }
            )

            if len(data) >= limit:
                break

        return {
            "as_of": effective_as_of,
            "data": data
        }

    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Warehouse query failed: {exc}"
        ) from exc

    finally:
        if conn is not None:
            conn.close()

def get_grid_location(grid_id: int):
    if grid_id < 1 or grid_id > 10000:
        raise LookupError(f"Grid {grid_id} not found")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            """
            SELECT
                grid_id,
                centroid_lat,
                centroid_lon,
                geometry_reference
            FROM dim_grid
            WHERE grid_id = ?
            """,
            (grid_id,)
        ).fetchone()

        if row is None:
            raise LookupError(f"Grid {grid_id} not found")

        return {
            "grid_id": row["grid_id"],
            "centroid_lat": row["centroid_lat"],
            "centroid_lon": row["centroid_lon"],
            "geometry_reference": row["geometry_reference"]
        }

    finally:
        conn.close()
def predict_network_risk(request):
    feature_path = PROJECT_ROOT / "data" / "analytics" / "network_feature_table"

    feature_timestamp = pd.Timestamp(request.timestamp)

    features = pd.read_parquet(
        feature_path,
        filters=[
            ("grid_id", "==", request.grid_id),
            ("feature_timestamp", "==", feature_timestamp)
        ]
    )

    if features.empty:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No ML2 feature record found for grid {request.grid_id} "
                f"at timestamp {request.timestamp}"
            )
        )

    if len(features) > 1:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Multiple ML2 feature records found for grid "
                f"{request.grid_id} at timestamp {request.timestamp}"
            )
        )
    activity = pd.read_parquet(
    ACTIVITY_PATH,
    filters=[
        ("grid_id", "==", request.grid_id),
        ("timestamp", "==", feature_timestamp)
    ]
    )

    if activity.empty:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No source activity record found for grid "
                f"{request.grid_id} at timestamp {request.timestamp}"
            )
        )

    if len(activity) > 1:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Multiple source activity records found for grid "
                f"{request.grid_id} at timestamp {request.timestamp}"
            )
        )

    actual_activity = float(activity.iloc[0]["total_activity"])

    if abs(request.total_activity - actual_activity) > 0.0001:
        raise HTTPException(
            status_code=422,
            detail=(
                f"total_activity does not match the source value. "
                f"Expected {actual_activity}, "
                f"received {request.total_activity}"
            )
        )


    feature_row = features.iloc[0]
    
    model_features = {
        "avg_activity": float(feature_row["avg_activity"]),
        "activity_growth": float(feature_row["activity_growth"]),
        "active_hours": float(feature_row["active_hours"]),
        "peak_ratio": float(feature_row["peak_ratio"]),
        "variability": float(feature_row["variability"]),
        "internet_share": float(feature_row["internet_share"])
    }

    prediction = predict_risk(model_features)

    anomaly_scores = pd.read_csv(ANOMALY_PATH)

    anomaly_scores["timestamp"] = pd.to_datetime(
        anomaly_scores["timestamp"]
    )

    target_date = feature_timestamp.date()
    target_hour = feature_timestamp.hour

    anomaly_match = anomaly_scores[
        (anomaly_scores["grid_id"] == request.grid_id)
        &
        (anomaly_scores["timestamp"].dt.date == target_date)
        &
        (anomaly_scores["timestamp"].dt.hour == target_hour)
    ]

    if anomaly_match.empty:
        anomaly_note = (
            "No ML4 anomaly record is available for this grid and hour."
        )
    else:
        anomaly_row = anomaly_match.iloc[0]

        anomaly_note = (
            f"ML4 anomaly status: {anomaly_row['direction']}. "
            f"Anomaly score: {float(anomaly_row['anomaly_score']):.4f}. "
            f"{anomaly_row['reason']}."
        )

    return {
        "risk_score": prediction["risk_score"],
        "risk_level": prediction["risk_level"],
        "model_version": prediction["model_version"],
        "explanation_note": (
            f"ML3 risk prediction generated using features at "
            f"{request.timestamp}. "
            f"{anomaly_note}"
        )
    }