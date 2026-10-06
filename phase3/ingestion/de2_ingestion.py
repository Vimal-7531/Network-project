from pathlib import Path
import csv
import shutil
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[2]

LANDING_DIR = BASE_DIR / "data" / "landing"
RAW_DIR = BASE_DIR / "data" / "raw"
REJECTED_DIR = BASE_DIR / "data" / "rejected"
LOG_DIR = BASE_DIR / "logs"

AUDIT_LOG = LOG_DIR / "ingestion_audit.csv"

REQUIRED_COLUMNS = [
    "datetime",
    "CellID",
    "countrycode",
    "smsin",
    "smsout",
    "callin",
    "callout",
    "internet"
]


def create_directories():
    LANDING_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def create_audit_log():
    if not AUDIT_LOG.exists():
        with open(AUDIT_LOG, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "filename",
                "status",
                "reason"
            ])


def write_audit_log(filename, status, reason):
    with open(AUDIT_LOG, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.now().isoformat(),
            filename,
            status,
            reason
        ])

def validate_file(file_path):
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)

            header = next(reader, None)

            if header is None:
                return False, "Empty file"

            header = [column.strip() for column in header]

            if header != REQUIRED_COLUMNS:
                return False, "Invalid schema"

            row_number = 1

            for row in reader:
                row_number += 1

                if len(row) != len(REQUIRED_COLUMNS):
                    return False, f"Incorrect number of columns at row {row_number}"

                try:
                    datetime.fromisoformat(row[0].strip())
                except ValueError:
                    return False, f"Invalid datetime at row {row_number}"

                for column_index in range(3, 8):
                    try:
                        value = row[column_index].strip()

                        if value == "":
                            continue

                        value = float(value)

                    except ValueError:
                        return False, f"Non-numeric value in {REQUIRED_COLUMNS[column_index]} at row {row_number}"

                    if value < 0:
                        return False, f"Negative value in {REQUIRED_COLUMNS[column_index]} at row {row_number}"

            if row_number == 1:
                return False, "No data rows"

            return True, "Validation passed"

    except Exception as error:
        return False, str(error)

def process_file(file_path):
    raw_destination = RAW_DIR / file_path.name
    rejected_destination = REJECTED_DIR / file_path.name

    if raw_destination.exists():
        write_audit_log(
            file_path.name,
            "SKIPPED",
            "File already exists in raw"
        )

        print(f"SKIPPED: {file_path.name} - Already exists in raw")
        return

    if rejected_destination.exists():
        write_audit_log(
            file_path.name,
            "SKIPPED",
            "File already exists in rejected"
        )

        print(f"SKIPPED: {file_path.name} - Already exists in rejected")
        return

    is_valid, reason = validate_file(file_path)

    if is_valid:
        shutil.copyfile(file_path, raw_destination)

        write_audit_log(
            file_path.name,
            "ACCEPTED",
            reason
        )

        print(f"ACCEPTED: {file_path.name}")

    else:
        shutil.copyfile(file_path, rejected_destination)

        write_audit_log(
            file_path.name,
            "REJECTED",
            reason
        )

        print(f"REJECTED: {file_path.name} - {reason}")


def main():
    create_directories()
    create_audit_log()

    csv_files = list(LANDING_DIR.glob("*.csv"))

    print(f"Found {len(csv_files)} CSV files")

    for file_path in csv_files:
        process_file(file_path)


if __name__ == "__main__":
    main()