import os
import sys
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator

PROJECT_DIR = os.path.expanduser(
    "~/Desktop/Data Engineer/Déploiement des modèles/dataprophet"
)
IMPROVEMENT_THRESHOLD = 0.01  # R² must improve by at least 1%


def evaluate_metrics(**context):
    sys.path.insert(0, PROJECT_DIR)
    import mlflow
    mlflow.set_tracking_uri("http://localhost:5000")
    client = mlflow.tracking.MlflowClient()

    # Metrics of the current production model
    prod_version = client.get_model_version_by_alias("DataProphet", "production")
    prod_run = client.get_run(prod_version.run_id)
    prod_r2 = prod_run.data.metrics.get("r2", 0)

    # Metrics of the most recent retraining run
    runs = client.search_runs(
        experiment_ids=["2"],  # arvores-grenoble-retrain
        order_by=["start_time DESC"],
        max_results=1
    )
    if not runs:
        print("No retraining run found.")
        return "skip_promotion"

    new_r2 = runs[0].data.metrics.get("r2", 0)
    print(f"R² production: {prod_r2:.4f} | R² new: {new_r2:.4f}")

    if new_r2 > prod_r2 + IMPROVEMENT_THRESHOLD:
        print("✓ New model is better — promoting.")
        return "promote_to_production"
    else:
        print("✗ New model does not exceed threshold — skipping.")
        return "skip_promotion"


def promote_to_production(**context):
    import requests
    import mlflow
    mlflow.set_tracking_uri("http://localhost:5000")
    client = mlflow.tracking.MlflowClient()

    # Get the latest version
    versions = client.get_latest_versions("DataProphet")
    latest = sorted(versions, key=lambda v: int(v.version))[-1]

    # Promote in Registry
    client.set_registered_model_alias("DataProphet", "production", latest.version)
    print(f"✓ Version {latest.version} promoted to @production.")

    # Reload model in API without restarting Uvicorn
    try:
        response = requests.post(
            "http://localhost:8000/admin/reload-model", timeout=10
        )
        response.raise_for_status()
        print(f"✓ API reloaded model automatically: {response.json()}")
    except Exception as e:
        print(f"⚠ Model promoted but auto-reload failed: {e}")
        print("  Run manually: curl -X POST http://localhost:8000/admin/reload-model")


def skip_promotion(**context):
    print("Promotion skipped — current production model unchanged.")


with DAG(
    dag_id="dag_deploy",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["dataprophet"],
) as dag:

    t1 = BranchPythonOperator(
        task_id="evaluate_metrics",
        python_callable=evaluate_metrics,
    )

    t2 = PythonOperator(
        task_id="promote_to_production",
        python_callable=promote_to_production,
    )

    t3 = PythonOperator(
        task_id="skip_promotion",
        python_callable=skip_promotion,
    )

    t1 >> [t2, t3]