import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/mnt/c/Users/vimalraj.ck/network_project")

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import get_current_context
from phase3.ingestion.de2_ingestion import main as run_ingestion
from phase3.spark.telecom_pipeline import main as run_spark_pipeline
from phase3.validation.de7_validation import main as run_validation
from phase3.warehouse.network_warehouse import main as run_warehouse
from phase3.quality.de7_quality_check import main as run_quality_check, write_pipeline_status
from phase6.ml.features import main as run_ml2_features
from phase6.ml.batch_score import main as run_ml6_scoring


def notify_success():
    print("Network Operations Predictive Intelligence pipeline completed successfully.")
    print("DE2 ingestion completed.")
    print("DE3 Spark processing completed.")
    print("Validation completed.")
    print("SQLite warehouse loaded.")
    print("Quality check completed.")
    print("Pipeline status: SUCCESS")


def record_pipeline_status():
    context = get_current_context()
    ti = context["ti"]
    task_ids = [
        "run_de2_ingestion",
        "run_de3_spark",
        "run_validation",
        "load_warehouse",
        "quality_check",
        "notify"
    ]
    task_states = ti.get_task_states(
        dag_id=ti.dag_id,
        run_ids=[ti.run_id],
        task_ids=task_ids
    )

    failed_tasks = []
    for task_id, state in task_states.items():
        if state != "success":
            failed_tasks.append(f"{task_id}:{state}")

    if failed_tasks:
        write_pipeline_status(
            "FAILED",
            "; ".join(failed_tasks)
        )
    else:
        write_pipeline_status(
            "SUCCESS",
            "Pipeline completed successfully"
        )

def run_de3_with_failure():
    result = run_spark_pipeline(
        input_dir="/mnt/c/Users/vimalraj.ck/network_project/data/raw",
        output_dir="/mnt/c/Users/vimalraj.ck/network_project/data/processed/activity",
        analytics_dir="/mnt/c/Users/vimalraj.ck/network_project/data/analytics",
        reference_path="/mnt/c/Users/vimalraj.ck/network_project/data/reference/milano-grid.geojson",
    )

    if result != 0:
        raise RuntimeError(
            f"DE3 Spark pipeline failed with return code {result}"
        )
with DAG(
    dag_id="de2_distributed_ingestion",
    start_date=datetime(2026, 8, 1),
    schedule=None,
    catchup=False,
    tags=["phase3", "de2", "de3", "de7", "de8"],
) as dag:

    run_de2_ingestion = PythonOperator(
        task_id="run_de2_ingestion",
        python_callable=run_ingestion,
    )

    run_de3_spark = PythonOperator(
        task_id="run_de3_spark",
        python_callable=run_de3_with_failure,
        retries=2,
        retry_delay=timedelta(minutes=5),
    )

    run_ml2_features = PythonOperator(
        task_id="run_ml2_features",
        python_callable=run_ml2_features,
    )

    run_ml6_scoring = PythonOperator(
        task_id="run_ml6_scoring",
        python_callable=run_ml6_scoring,
    )
    run_validation = PythonOperator(
        task_id="run_validation",
        python_callable=run_validation,
    )

    load_warehouse = PythonOperator(
        task_id="load_warehouse",
        python_callable=run_warehouse,
    )

    quality_check = PythonOperator(
        task_id="quality_check",
        python_callable=run_quality_check,
    )

    notify = PythonOperator(
        task_id="notify",
        python_callable=notify_success,
    )

    pipeline_status = PythonOperator(
        task_id="pipeline_status",
        python_callable=record_pipeline_status,
        trigger_rule="all_done",
    )

    run_de2_ingestion >> run_de3_spark >> run_ml2_features >> run_ml6_scoring >> run_validation >> load_warehouse >> quality_check >> notify >> pipeline_status