import os
import json
import glob
import pandas as pd
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

HELP_DATA_DIR = os.path.expanduser(
    "~/Desktop/Data Engineer/Déploiement des modèles/dataprophet/help_data"
)
OUTPUT_PATH = os.path.expanduser(
    "~/Desktop/Data Engineer/Déploiement des modèles/dataprophet/data/retrain_dataset.csv"
)

REQUIRED_FIELDS = ["genre_bota", "espece", "stadededeveloppement",
                   "hauteurarbre", "latitude", "longitude", "label_correct"]

def load_and_validate(**context):
    files = glob.glob(os.path.join(HELP_DATA_DIR, "*.json"))
    if not files:
        print("No files found in help_data/. Pipeline stopped.")
        context["ti"].xcom_push(key="valid_records", value=[])
        return

    valid, rejected = [], 0
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
        if all(k in data for k in REQUIRED_FIELDS):
            valid.append(data)
        else:
            print(f"Rejected: {f}")
            rejected += 1

    print(f"Valid: {len(valid)} | Rejected: {rejected}")
    context["ti"].xcom_push(key="valid_records", value=valid)

def prepare_dataset(**context):
    records = context["ti"].xcom_pull(key="valid_records", task_ids="load_and_validate")
    if not records:
        print("No valid records to process.")
        return

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset saved to {OUTPUT_PATH} with {len(df)} rows.")

with DAG(
    dag_id="dag_preprocessing",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["dataprophet"],
) as dag:

    t1 = PythonOperator(
        task_id="load_and_validate",
        python_callable=load_and_validate,
    )

    t2 = PythonOperator(
        task_id="prepare_dataset",
        python_callable=prepare_dataset,
    )

    t1 >> t2
