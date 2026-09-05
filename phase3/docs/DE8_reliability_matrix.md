# DE8 — Network Pipeline Reliability Matrix

## Objective

Define how the Network Operations Predictive Intelligence pipeline handles common data and processing failures.

The pipeline must distinguish between errors that should reject or quarantine individual files and errors that should stop or retry the pipeline.

## Failure Handling Matrix

| Failure                     | Detection Point       | Action              | Pipeline Behaviour                         | Reason                                                |
| --------------------------- | --------------------- | ------------------- | ------------------------------------------ | ----------------------------------------------------- |
| Missing daily CSV           | DE2 ingestion         | FAIL                | Stop pipeline                              | Required operational input is unavailable             |
| Duplicate file              | DE2 ingestion         | WARN / SKIP         | Continue                                   | File was already processed and must not be duplicated |
| Duplicate ingestion attempt | DE2 ingestion         | WARN / SKIP         | Continue                                   | Prevent duplicate raw data                            |
| Malformed timestamp         | DE2 validation        | REJECT / QUARANTINE | Continue with other valid files            | Invalid records cannot be reliably processed          |
| Negative activity value     | DE2 validation        | REJECT / QUARANTINE | Continue with other valid files            | Activity measures cannot be negative                  |
| Missing required column     | DE2 schema validation | REJECT / QUARANTINE | Continue                                   | File does not satisfy the input contract              |
| Unexpected column           | DE2 schema validation | WARN or REJECT      | Continue if non-critical; otherwise reject | Protect against schema drift                          |
| Partially corrupt CSV       | DE2 ingestion         | REJECT / QUARANTINE | Continue                                   | File cannot be trusted                                |
| Empty input                 | DE3 Spark processing  | FAIL                | Stop pipeline                              | No usable data available                              |
| Spark job failure           | DE3                   | RETRY               | Retry task                                 | Temporary processing failures may recover             |
| Validation failure          | DE7 validation        | FAIL                | Stop downstream tasks                      | Invalid analytics must not reach warehouse            |
| Warehouse loading failure   | DE6 / DE7             | RETRY / FAIL        | Retry, then stop                           | Prevent incomplete warehouse state                    |
| Quality check failure       | DE7                   | FAIL                | Stop pipeline                              | Published data does not meet quality requirements     |
| Notification failure        | DE7                   | RETRY               | Retry notification                         | Data pipeline has already completed                   |

## Reliability Controls

### Control 1 — Duplicate Protection

Already implemented by the ingestion layer.

If a daily file has already been processed, the pipeline does not silently ingest it again. The attempt is recorded in the ingestion audit log.

Expected behaviour:

```text
Duplicate file
      ↓
Detect existing raw file
      ↓
SKIP / WARN
      ↓
Write audit record
      ↓
Continue pipeline
```

### Control 2 — Invalid File Rejection

Files failing schema or data-quality validation are routed to the rejected zone instead of being processed as valid data.

Expected behaviour:

```text
Landing file
      ↓
Validation
   ↙       ↘
Valid     Invalid
 ↓          ↓
Raw       Rejected
           ↓
       Audit reason
```

### Control 3 — Pipeline Quality Gate

The DE7 validation and quality-check stages prevent invalid analytics from being loaded or accepted as a successful pipeline run.

Expected behaviour:

```text
Spark processing
      ↓
Validation
      ↓
Load warehouse
      ↓
Quality check
      ↓
PASS → Notify SUCCESS
FAIL → Stop pipeline
```

### Control 4 — Safe Rerun

The pipeline must be safe to rerun after a failure.

A rerun must not:

* duplicate raw files
* duplicate fact rows
* create duplicate grid keys
* corrupt the analytics layer

The warehouse load recreates the warehouse tables from the current analytics output, ensuring the fact table is rebuilt consistently rather than appended blindly.

### Control 5 — Spark Retry

Transient Spark failures should be retried by Airflow before the pipeline is considered failed.

Recommended policy:

* retries: 2
* retry delay: 5 minutes
* downstream tasks run only after Spark succeeds

## Safe Rerun Demonstration

Scenario:

1. Run the pipeline successfully.
2. Confirm the analytics and warehouse row counts.
3. Trigger the same DAG again.
4. Confirm the ingestion layer identifies already-processed files.
5. Confirm the warehouse does not contain duplicate fact records.
6. Confirm the final quality status is successful.

Expected result:

```text
First run
    ↓
SUCCESS
    ↓
Second run
    ↓
Duplicate files detected
    ↓
SKIP / WARN
    ↓
Processing remains consistent
    ↓
SUCCESS
```

## Troubleshooting Map

| Symptom                         | First Module to Investigate | Evidence to Check                      |
| ------------------------------- | --------------------------- | -------------------------------------- |
| File not appearing in raw       | DE2 ingestion               | ingestion_audit.csv                    |
| File rejected                   | DE2 validation              | data/rejected/ and audit log           |
| Spark failure                   | DE3 Spark processing        | Airflow task log                       |
| Validation failure              | DE7 validation              | validation task log                    |
| Warehouse failure               | DE6 warehouse loader        | warehouse task log and SQLite database |
| Incorrect row count             | DE6 / DE7 quality           | source and fact row counts             |
| Duplicate data                  | DE2 / DE6                   | audit log and fact table               |
| Missing AS_OF                   | DE7 quality check           | pipeline_quality_status.csv            |
| Pipeline stops before warehouse | DE7 validation              | Airflow task status                    |
| Notification failure            | DE7 notify                  | Airflow task log                       |

## Observed vs Inferred

During incident investigation, evidence must be separated from assumptions.

### Observed

Examples:

* Airflow task is marked FAILED.
* Specific exception appears in the task log.
* File appears in data/rejected/.
* Audit log contains a REJECTED record.
* Warehouse row count differs from source row count.

### Inferred

Examples:

* The failure may have been caused by insufficient memory.
* The file may have been partially corrupted.
* The Spark failure may be temporary.

Operational changes should be made only after confirming the evidence.

## DE8 Acceptance Criteria

* [x] Failure handling matrix documented
* [x] Duplicate-file behaviour defined
* [x] Invalid-file behaviour defined
* [x] Spark failure behaviour defined
* [x] Safe rerun strategy documented
* [x] Troubleshooting map documented
* [ ] At least three controls demonstrated
* [ ] Safe rerun demonstrated
* [ ] Failure scenarios reflected in the DE7 pipeline status record
