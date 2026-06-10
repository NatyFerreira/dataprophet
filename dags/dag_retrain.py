import os
import sys
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_DIR = os.path.expanduser(
    "~/Desktop/Data Engineer/Déploiement des modèles/dataprophet"
)

def run_retrain(**context):
    sys.path.insert(0, os.path.expanduser(PROJECT_DIR))
    import mlflow
    mlflow.set_tracking_uri("http://localhost:5000")

    # Conta runs antes
    client = mlflow.tracking.MlflowClient()
    runs_before = client.search_runs(experiment_ids=["2"])
    n_before = len(runs_before)

    # Executa retrain
    import retrain
    retrain.retrain()

    # Verifica novo run
    runs_after = client.search_runs(experiment_ids=["2"])
    n_after = len(runs_after)

    if n_after > n_before:
        print(f"✓ Novo run registrado no MLflow ({n_after - n_before} novo(s)).")
    else:
        raise ValueError("Nenhum novo run detectado no MLflow após retraining.")

with DAG(
    dag_id="dag_retrain",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["dataprophet"],
) as dag:

    t1 = PythonOperator(
        task_id="run_retrain",
        python_callable=run_retrain,
    )