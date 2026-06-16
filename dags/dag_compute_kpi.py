from datetime import datetime
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator


def trigger_compute_kpi(**context):
    """Calls the /admin/compute-kpi endpoint from FastAPI to recalculate
    the Business KPI (Level 3) and update Prometheus Gauges."""
    try:
        response = requests.post(
            "http://localhost:8000/admin/compute-kpi", timeout=10
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ Level 3 KPI recalculated: {data}")
    except Exception as e:
        print(f"⚠ Failed to recalculate KPI: {e}")
        raise


with DAG(
    dag_id="dag_compute_kpi",
    start_date=datetime(2024, 1, 1),
    schedule_interval="*/15 * * * *",  # every 15 minutes
    catchup=False,
    tags=["dataprophet"],
) as dag:

    t1 = PythonOperator(
        task_id="trigger_compute_kpi",
        python_callable=trigger_compute_kpi,
    )
