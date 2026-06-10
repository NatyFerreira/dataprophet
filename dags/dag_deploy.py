import os
import sys
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator

PROJECT_DIR = os.path.expanduser(
    "~/Desktop/Data Engineer/Déploiement des modèles/dataprophet"
)
IMPROVEMENT_THRESHOLD = 0.01  # R² deve melhorar pelo menos 1%

def evaluate_metrics(**context):
    sys.path.insert(0, PROJECT_DIR)
    import mlflow
    mlflow.set_tracking_uri("http://localhost:5000")
    client = mlflow.tracking.MlflowClient()

    # Métricas do modelo em production
    prod_version = client.get_model_version_by_alias("DataProphet", "production")
    prod_run = client.get_run(prod_version.run_id)
    prod_r2 = prod_run.data.metrics.get("r2", 0)

    # Métricas do run mais recente
    runs = client.search_runs(
        experiment_ids=["1"],
        order_by=["start_time DESC"],
        max_results=1
    )
    if not runs:
        print("Nenhum run encontrado.")
        return "skip_promotion"

    new_r2 = runs[0].data.metrics.get("r2", 0)
    print(f"R² production: {prod_r2:.4f} | R² novo: {new_r2:.4f}")

    if new_r2 > prod_r2 + IMPROVEMENT_THRESHOLD:
        print("✓ Novo modelo é melhor — promovendo.")
        return "promote_to_production"
    else:
        print("✗ Novo modelo não supera o threshold — pulando.")
        return "skip_promotion"

def promote_to_production(**context):
    import mlflow
    mlflow.set_tracking_uri("http://localhost:5000")
    client = mlflow.tracking.MlflowClient()

    # Pega a versão mais recente
    versions = client.get_latest_versions("DataProphet")
    latest = sorted(versions, key=lambda v: int(v.version))[-1]

    client.set_registered_model_alias("DataProphet", "production", latest.version)
    print(f"✓ Versão {latest.version} promovida para @production.")

def skip_promotion(**context):
    print("Promoção ignorada — modelo atual em production mantido.")

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

    t1