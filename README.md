# DataProphet — Grenoble Urban Trees

MLOps API for predicting the planting year of urban trees in Grenoble.  
Model: RandomForestRegressor trained on 31,670 trees (R² = 0.70).

---

## Architecture

```
dataprophet/
├── main.py              # FastAPI server (prediction + metrics + feedback)
├── schemas.py           # Pydantic schemas (ArvoreFeatures, HelpData)
├── metrics.py           # Prometheus metrics (Counter, Histogram)
├── train.py             # Model training + MLflow logging
├── retrain.py           # Automated retraining with model promotion
├── dags/                # Airflow DAGs (Day 4)
│   ├── dag_preprocessing.py   # Validate & prepare help_data/ feedback
│   ├── dag_retrain.py         # Trigger retrain.py via Airflow
│   ├── dag_deploy.py          # Conditional model promotion (BranchPythonOperator)
│   └── dag_mlops_weekly.py    # Master DAG — runs every Monday at 6am
├── help_data/           # User feedback (JSON files)
├── data/                # Processed datasets (retrain_dataset.csv)
├── prometheus.yml       # Prometheus scraping configuration
├── docker-compose.yml   # MLflow Server
├── environment.yml      # Conda dependencies
└── README.md
```

---

## Stack

| Component | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Model | scikit-learn 1.2.2 (RandomForest) |
| Experiment Tracking | MLflow 3.13 |
| Model Registry | MLflow Registry (alias `production`) |
| Metrics | prometheus-client |
| Monitoring | Prometheus 3.12 + Grafana 13 |
| Orchestration | Apache Airflow 2.9.1 |
| Environment | conda Python 3.11 |

---

## Installation

```bash
# 1. Create and activate the environment
conda env create -f environment.yml
conda activate dataprophet

# 2. Install additional dependencies
pip install mlflow prometheus-client apache-airflow==2.9.1
```

---

## Starting the services

### 1. MLflow Tracking Server
```bash
mlflow server --host 0.0.0.0 --port 5000 &
```

### 2. Train and register the model
```bash
python train.py --n_estimators 100 --max_depth 15
```
Then promote to production in the MLflow UI (`http://localhost:5000`):  
Models → DataProphet → Version 1 → Aliases → Add → `production`

### 3. FastAPI
```bash
uvicorn main:app --reload --port 8000
```

### 4. Prometheus
```bash
prometheus --config.file=prometheus.yml --web.listen-address=":9090" &
```

### 5. Grafana
```bash
grafana server --homepath /opt/homebrew/share/grafana &
```
Access: `http://localhost:3000` (admin/admin)

### 6. Airflow
```bash
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
airflow standalone
```
Access: `http://localhost:8080` (admin / see terminal output for password)

---

## Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/health` | API health check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/predict` | Predict planting year |
| POST | `/api/helpdata` | Submit user feedback |

---

## Prediction

```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "genre_bota": "Prunus",
    "espece": "serrulata",
    "stadededeveloppement": "Arbre jeune",
    "hauteurarbre": "Moins de 10 m",
    "typenature": "Libre",
    "latitude": 45.167,
    "longitude": 5.740
  }'
```

Response:
```json
{
  "annee_predite": 2007.24,
  "annee_arrondie": 2007
}
```

---

## Feedback (closing the MLOps loop)

```bash
curl -X POST http://localhost:8000/api/helpdata \
  -H "Content-Type: application/json" \
  -d '{
    "genre_bota": "Prunus",
    "espece": "serrulata",
    "stadededeveloppement": "Arbre jeune",
    "hauteurarbre": "Moins de 10 m",
    "typenature": "Libre",
    "latitude": 45.167,
    "longitude": 5.740,
    "label_correct": "stable"
  }'
```

JSON files are saved to `help_data/` and consumed by `dag_preprocessing` on the next Airflow run.

---

## Automated MLOps Pipeline (Airflow)

The weekly pipeline runs every Monday at 6am (`0 6 * * 1`) via `dag_mlops_weekly`:

```
dag_preprocessing → dag_retrain → dag_deploy
```

| DAG | What it does |
|---|---|
| `dag_preprocessing` | Reads `help_data/` JSONs, validates, saves `data/retrain_dataset.csv` |
| `dag_retrain` | Calls `retrain.py`, verifies new MLflow run registered |
| `dag_deploy` | Compares R² of new model vs production; promotes if improvement > 1% |
| `dag_mlops_weekly` | Master DAG — chains the 3 above with `TriggerDagRunOperator` |

To trigger manually:
1. Open `http://localhost:8080`
2. Search DAGs by tag `dataprophet`
3. Click ▶ on `dag_mlops_weekly`

---

## Monitoring

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` → dashboard **DataProphet — Monitoring Production**
  - Panel 1: Prediction volume per minute
  - Panel 2: Average prediction latency (s)
  - Panel 3: Prediction distribution by decade

---

## Model performance

| Version | n_estimators | max_depth | MAE | R² |
|---|---|---|---|---|
| v1 (production) | 100 | 15 | 6.49 years | 0.70 |
| v2 | 50 | 10 | 8.54 years | 0.59 |
