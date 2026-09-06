import os
import pandas as pd

from network_alerts import (
    build_grid_hour_table,
    add_within_day_baseline,
    generate_alerts
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "landing")
OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "..",
    "phase6",
    "ml",
    "ml3_output",
    "np3_alerts_all_days.csv"
)

files = [
    "sms-call-internet-mi-2013-11-01.csv",
    "sms-call-internet-mi-2013-11-02.csv",
    "sms-call-internet-mi-2013-11-03.csv",
    "sms-call-internet-mi-2013-11-04.csv",
    "sms-call-internet-mi-2013-11-05.csv",
    "sms-call-internet-mi-2013-11-06.csv",
    "sms-call-internet-mi-2013-11-07.csv"
]

all_alerts = []

for file_name in files:
    input_path = os.path.join(DATA_DIR, file_name)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Missing input file: {input_path}")

    print(f"Processing {file_name}")

    grid_hour = build_grid_hour_table(input_path)
    grid_hour = add_within_day_baseline(grid_hour)
    alerts = generate_alerts(grid_hour)

    if not alerts.empty:
        alerts["source_file"] = file_name
        all_alerts.append(alerts)

if all_alerts:
    combined = pd.concat(all_alerts, ignore_index=True)
else:
    combined = pd.DataFrame()

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

combined.to_csv(OUTPUT_FILE, index=False)

print()
print("NP3 COMBINATION COMPLETE")
print("=" * 40)
print(f"Total alerts: {len(combined)}")
print()
print("Alerts by type:")
print(combined["alert_type"].value_counts().to_string())
print()
print(f"Output:")
print(OUTPUT_FILE)