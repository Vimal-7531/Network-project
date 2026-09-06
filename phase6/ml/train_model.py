from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lead, when, expr
from pyspark.sql.window import Window
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import pandas as pd
import os
import json
import joblib

PROJECT_ROOT = r"C:\Users\vimalraj.ck\network_project"

FEATURE_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "analytics",
    "network_feature_table"
)

ACTIVITY_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "analytics",
    "hourly_grid_summary"
)

NP3_ALERT_PATH = os.path.join(
    PROJECT_ROOT,
    "phase6",
    "ml",
    "ml3_output",
    "np3_alerts_all_days.csv"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "phase6",
    "ml",
    "ml3_output"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

THRESHOLD = 1186.8269

FEATURE_COLUMNS = [
    "avg_activity",
    "activity_growth",
    "active_hours",
    "peak_ratio",
    "variability",
    "internet_share"
]

spark = (
    SparkSession.builder
    .appName("ML3_Risk_Classifier")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

features = (
    spark.read
    .parquet(FEATURE_PATH)
    .select(
        "grid_id",
        "feature_timestamp",
        *FEATURE_COLUMNS
    )
)

activity = (
    spark.read
    .parquet(ACTIVITY_PATH)
    .select(
        "grid_id",
        "timestamp",
        "total_activity"
    )
    .dropDuplicates(["grid_id", "timestamp"])
)

target_window = (
    Window
    .partitionBy("grid_id")
    .orderBy("timestamp")
)

activity_with_target = (
    activity
    .withColumn(
        "target_timestamp",
        lead("timestamp").over(target_window)
    )
    .withColumn(
        "target_activity",
        lead("total_activity").over(target_window)
    )
)

dataset = (
    features.alias("f")
    .join(
        activity_with_target.alias("a"),
        (
            (col("f.grid_id") == col("a.grid_id"))
            &
            (
                col("a.timestamp")
                == col("f.feature_timestamp")
            )
        ),
        "inner"
    )
    .filter(
        col("a.target_timestamp")
        == col("f.feature_timestamp") + expr("INTERVAL 1 HOUR")
    )
    .withColumn(
        "high_activity_risk",
        when(
            col("a.target_activity") > THRESHOLD,
            1
        ).otherwise(0)
    )
    .select(
        col("f.grid_id").alias("grid_id"),
        col("f.feature_timestamp").alias("feature_timestamp"),
        *[
            col(f"f.{feature}")
            for feature in FEATURE_COLUMNS
        ],
        col("a.target_timestamp").alias("target_timestamp"),
        col("a.target_activity").alias("target_activity"),
        col("high_activity_risk")
    )
    .orderBy("feature_timestamp", "grid_id")
)

pdf = dataset.toPandas()

spark.stop()

if pdf.empty:
    raise ValueError("ML3 dataset is empty.")

pdf["feature_timestamp"] = pd.to_datetime(
    pdf["feature_timestamp"]
)

pdf["target_timestamp"] = pd.to_datetime(
    pdf["target_timestamp"]
)

pdf = pdf.sort_values(
    ["feature_timestamp", "grid_id"]
).reset_index(drop=True)

unique_timestamps = sorted(
    pdf["feature_timestamp"].drop_duplicates()
)

timestamp_split_index = int(
    len(unique_timestamps) * 0.8
)

if timestamp_split_index <= 0 or timestamp_split_index >= len(unique_timestamps):
    raise ValueError("Invalid chronological split.")

train_timestamps = set(
    unique_timestamps[:timestamp_split_index]
)

test_timestamps = set(
    unique_timestamps[timestamp_split_index:]
)

train_df = pdf[
    pdf["feature_timestamp"].isin(train_timestamps)
].copy()

test_df = pdf[
    pdf["feature_timestamp"].isin(test_timestamps)
].copy()

if train_df.empty or test_df.empty:
    raise ValueError("Train or test dataset is empty.")

train_latest = train_df["feature_timestamp"].max()
test_earliest = test_df["feature_timestamp"].min()

if train_latest >= test_earliest:
    raise ValueError(
        "Chronological split validation failed."
    )

X_train = train_df[FEATURE_COLUMNS]
y_train = train_df["high_activity_risk"]

X_test = test_df[FEATURE_COLUMNS]
y_test = test_df["high_activity_risk"]

model = Pipeline(
    [
        ("scaler", StandardScaler()),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced"
            )
        )
    ]
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

precision = precision_score(
    y_test,
    predictions,
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0
)

base_rate = y_test.mean()

train_positive_rate = y_train.mean()
test_positive_rate = y_test.mean()

classifier = model.named_steps["classifier"]

coefficients = classifier.coef_[0]

coefficient_df = pd.DataFrame(
    {
        "feature": FEATURE_COLUMNS,
        "coefficient": coefficients,
        "absolute_coefficient": abs(coefficients)
    }
).sort_values(
    "absolute_coefficient",
    ascending=False
)

comparison_df = test_df[
    [
        "grid_id",
        "feature_timestamp",
        "target_timestamp",
        "high_activity_risk"
    ]
].copy()

comparison_df["ml_prediction"] = predictions

np3_alerts = pd.read_csv(
    NP3_ALERT_PATH
)

if np3_alerts.empty:
    np3_alerts = pd.DataFrame(
        columns=[
            "grid_id",
            "timestamp",
            "alert_type"
        ]
    )

np3_alerts["timestamp"] = pd.to_datetime(
    np3_alerts["timestamp"]
)

np3_alerts["grid_id"] = pd.to_numeric(
    np3_alerts["grid_id"]
)

np3_alerts["np3_positive"] = np3_alerts[
    "alert_type"
].isin(
    [
        "HIGH_ACTIVITY",
        "ACTIVITY_SPIKE"
    ]
)

np3_summary = (
    np3_alerts
    .groupby(
        ["grid_id", "timestamp"],
        as_index=False
    )
    .agg(
        np3_positive=("np3_positive", "max"),
        np3_alert_types=(
            "alert_type",
            lambda x: "|".join(sorted(set(x)))
        )
    )
)

comparison_df = comparison_df.merge(
    np3_summary,
    left_on=["grid_id", "feature_timestamp"],
    right_on=["grid_id", "timestamp"],
    how="left"
)

comparison_df["np3_positive"] = (
    comparison_df["np3_positive"]
    .fillna(False)
    .astype(bool)
)

comparison_df["np3_alert_types"] = (
    comparison_df["np3_alert_types"]
    .fillna("NO_ALERT")
)

comparison_df = comparison_df.drop(
    columns=["timestamp"]
)

comparison_df["agreement"] = (
    comparison_df["ml_prediction"].astype(bool)
    ==
    comparison_df["np3_positive"]
)

comparison_df["disagreement_type"] = "AGREEMENT"

comparison_df.loc[
    (
        (comparison_df["ml_prediction"] == 1)
        &
        (~comparison_df["np3_positive"])
    ),
    "disagreement_type"
] = "ML3_ONLY_RISK"

comparison_df.loc[
    (
        (comparison_df["ml_prediction"] == 0)
        &
        (comparison_df["np3_positive"])
    ),
    "disagreement_type"
] = "NP3_ONLY_ALERT"

comparison_df.loc[
    (
        (comparison_df["ml_prediction"] == 1)
        &
        (comparison_df["np3_positive"])
    ),
    "disagreement_type"
] = "BOTH_RISK"

np3_positive_count = int(
    comparison_df["np3_positive"].sum()
)

ml3_positive_count = int(
    comparison_df["ml_prediction"].sum()
)

both_positive_count = int(
    (
        (comparison_df["ml_prediction"] == 1)
        &
        (comparison_df["np3_positive"])
    ).sum()
)

ml3_only_count = int(
    (
        (comparison_df["ml_prediction"] == 1)
        &
        (~comparison_df["np3_positive"])
    ).sum()
)

np3_only_count = int(
    (
        (comparison_df["ml_prediction"] == 0)
        &
        (comparison_df["np3_positive"])
    ).sum()
)

agreement_count = int(
    comparison_df["agreement"].sum()
)

evaluation = {
    "algorithm": "Logistic Regression",
    "threshold": THRESHOLD,
    "train_rows": int(len(train_df)),
    "test_rows": int(len(test_df)),
    "train_earliest_timestamp": str(
        train_df["feature_timestamp"].min()
    ),
    "train_latest_timestamp": str(
        train_df["feature_timestamp"].max()
    ),
    "test_earliest_timestamp": str(
        test_df["feature_timestamp"].min()
    ),
    "test_latest_timestamp": str(
        test_df["feature_timestamp"].max()
    ),
    "chronological_split_valid": True,
    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "test_base_rate": float(base_rate),
    "train_positive_rate": float(train_positive_rate),
    "test_positive_rate": float(test_positive_rate),
    "positive_test_samples": int(y_test.sum()),
    "negative_test_samples": int((y_test == 0).sum()),
    "total_test_samples": int(len(y_test)),
    "np3_comparison": {
        "np3_positive_definition": [
            "HIGH_ACTIVITY",
            "ACTIVITY_SPIKE"
        ],
        "np3_positive_test_rows": np3_positive_count,
        "ml3_positive_test_rows": ml3_positive_count,
        "both_positive": both_positive_count,
        "ml3_only_risk": ml3_only_count,
        "np3_only_alert": np3_only_count,
        "agreement": agreement_count
    }
}

with open(
    os.path.join(
        OUTPUT_DIR,
        "evaluation.json"
    ),
    "w"
) as f:
    json.dump(
        evaluation,
        f,
        indent=4
    )

coefficient_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "model_coefficients.csv"
    ),
    index=False
)

comparison_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "np3_comparison.csv"
    ),
    index=False
)

train_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "train_dataset.csv"
    ),
    index=False
)

test_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "test_dataset.csv"
    ),
    index=False
)

joblib.dump(
    model,
    os.path.join(
        OUTPUT_DIR,
        "logistic_regression_model.joblib"
    )
)

print("\nML3 — Logistic Regression Risk Classifier")
print("=" * 50)

print("\nTRAIN SET")
print(f"Earliest timestamp: {train_df['feature_timestamp'].min()}")
print(f"Latest timestamp:   {train_df['feature_timestamp'].max()}")
print(f"Rows:                {len(train_df)}")
print(f"Positive rate:       {train_positive_rate:.6f}")

print("\nTEST SET")
print(f"Earliest timestamp: {test_df['feature_timestamp'].min()}")
print(f"Latest timestamp:   {test_df['feature_timestamp'].max()}")
print(f"Rows:                {len(test_df)}")
print(f"Positive rate:       {test_positive_rate:.6f}")

print("\nCHRONOLOGICAL VALIDATION")
print(f"Train latest < Test earliest: {train_latest < test_earliest}")

print("\nMODEL EVALUATION")
print(f"Accuracy:   {accuracy:.6f}")
print(f"Precision:  {precision:.6f}")
print(f"Recall:     {recall:.6f}")
print(f"Base rate:  {base_rate:.6f}")

print("\nCLASS BALANCE")
print(f"Positive test samples: {int(y_test.sum())}")
print(f"Negative test samples: {int((y_test == 0).sum())}")

print("\nMODEL COEFFICIENTS")
print(coefficient_df.to_string(index=False))

print("\nNP3 COMPARISON")
print("NP3 positive = HIGH_ACTIVITY or ACTIVITY_SPIKE")
print(f"ML3 positive:  {ml3_positive_count}")
print(f"NP3 positive:  {np3_positive_count}")
print(f"Both positive: {both_positive_count}")
print(f"ML3 only:      {ml3_only_count}")
print(f"NP3 only:      {np3_only_count}")
print(f"Agreement:     {agreement_count}")

print("\nNP3 DISAGREEMENT SUMMARY")
print(
    comparison_df[
        "disagreement_type"
    ].value_counts()
)

print("\nMODEL OUTPUT")
print(
    os.path.join(
        OUTPUT_DIR,
        "logistic_regression_model.joblib"
    )
)

print("\nOUTPUT DIRECTORY")
print(OUTPUT_DIR)

print("\nML3 training complete.")