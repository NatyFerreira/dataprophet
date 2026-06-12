# DataProphet — Grenoble Urban Trees

MLOps API for predicting the planting year of urban trees in Grenoble.  
Model: RandomForestRegressor trained on 31,670 trees (R² = 0.70).

---

## Architecture

```
dataprophet/
├── main.py                    # FastAPI app (prediction + metrics + feedback + model reload)
├── schemas.py                 # Pydantic schemas (ArvoreFeatures, HelpData)
├── metrics.py                 # Prometheus metrics (Counter, Histogram)
├── train.py                   # Model training + MLflow logging
├── retrain.py                 # Automated retraining with model promotion
├── compute_kpi.py             # Business KPI — API success rate on feedback data
├── analyse_retraining.md      # Before/after retraining analysis
├── tool_choices.md            # Tool justification document
├── dags/                      # Airflow DAGs (Day 4)
│   ├── dag_preprocessing.py   # Validate & prepare help_data/ feedback
│   ├── dag_retrain.py         # Trigger retrain.py via Airflow
│   ├── dag_deploy.py          # Conditional promotion + auto reload via /admin/reload-model
│   └── dag_mlops_weekly.py    # Master DAG — runs every Monday at 6am
├── prometheus.yml             # Prometheus scraping configuration
├── docker-compose.yml         # All services (MLflow, Prometheus, Grafana)
├── environment.yml            # Conda dependencies
└── README.md
```

---

## Stack

| Component | Technology |
|---|---|
| API server | Uvicorn 0.29 (ASGI) |
| API framework | FastAPI 0.111 |
| Model | scikit-learn 1.2.2 (RandomForest) |
| Experiment Tracking | MLflow 3.13 |
| Model Registry | MLflow Registry (alias `production`) |
| Metrics | prometheus-client 0.25 |
| Monitoring | Prometheus 3.12 + Grafana 13 |
| Orchestration | Apache Airflow 2.9.1 |
| Environment | conda Python 3.11 |

> **Note on Uvicorn:** Uvicorn is the ASGI server that runs FastAPI on port 8000.
> The model is loaded once at startup via `lifespan()`.
> After a model promotion, `dag_deploy` automatically calls `POST /admin/reload-model`
> — the new model is loaded in memory **without restarting Uvicorn (zero downtime)**.

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

### 3. Uvicorn / FastAPI
```bash
uvicorn main:app --reload --port 8000
```
The app loads `models:/DataProphet@production` from MLflow at startup.  
To reload a newly promoted model without restart:
```bash
curl -X POST http://localhost:8000/admin/reload-model
```

### 4. Prometheus
```bash
prometheus --config.file=/absolute/path/to/prometheus.yml --web.listen-address=":9090" &
```
> Use absolute path — Prometheus does not expand `~` in `--config.file`.

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
| GET | `/health` | API health check — returns `modelo_carregado: true/false` |
| GET | `/metrics` | Prometheus metrics endpoint |
| POST | `/api/predict` | Predict planting year |
| POST | `/api/helpdata` | Submit user feedback |
| POST | `/admin/reload-model` | Reload model from MLflow Registry — no Uvicorn restart needed |

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

## Model Reload (zero downtime)

After `dag_deploy` promotes a new model, it automatically calls:

```bash
curl -X POST http://localhost:8000/admin/reload-model
```

Response:
```json
{
  "status": "ok",
  "message": "Modelo recarregado com sucesso: models:/DataProphet@production"
}
```

The new model is loaded in memory — Uvicorn keeps running, no downtime.

---

## Business KPI (Level 3)

```bash
python compute_kpi.py
```

Reads `help_data/` JSONs, calls `/api/predict` on each, prints success rate.  
Console output only — does not require Prometheus or Grafana.

---

## Automated MLOps Pipeline (Airflow)

The weekly pipeline runs every Monday at 6am (`0 6 * * 1`) via `dag_mlops_weekly`:

```
dag_preprocessing → dag_retrain → dag_deploy
```

| DAG | What it does |
|---|---|
| `dag_preprocessing` | Reads `help_data/` JSONs, validates, saves `data/retrain_dataset.csv` |
| `dag_retrain` | Calls `retrain.py`, verifies new MLflow run registered in `arvores-grenoble-retrain` |
| `dag_deploy` | Compares R² vs production; if better → promotes + calls `/admin/reload-model` automatically |
| `dag_mlops_weekly` | Master DAG — chains the 3 above with `TriggerDagRunOperator` |

To trigger manually:
1. Open `http://localhost:8080`
2. Search DAGs by tag `dataprophet`
3. Click ▶ on `dag_mlops_weekly`

---

## Monitoring

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` → dashboard **DataProphet — Monitoring Production**

| Level | Panel | Metric | Alert | Threshold |
|---|---|---|---|---|
| 1 — System | Latency P95 | `histogram_quantile(0.95, rate(...bucket[5m]))` | P95 Latency degraded | > 200ms for 2 min |
| 1 — System | Average Latency | `rate(...sum[1m]) / rate(...count[1m])` | High Latency | > 1s for 2 min |
| 1 — System | Request rate | `rate(predictions_total[5m])` | — | — |
| 2 — Model | Prediction volume | `dataprophet_predictions_total` | Prediction volume set to zero | rate = 0 for 5 min |
| 2 — Model | Label distribution | `dataprophet_predictions_total` (pie) | — | — |
| 3 — Business | API success rate | `compute_kpi.py` (console) | — | manual |

All alert thresholds are based on **SmartRetail SLA requirements**:
- P95 latency < 200ms
- API availability ≥ 99% uptime
- Intervention: `POST /admin/reload-model` — no Uvicorn restart required

---

## Model performance

| Version | n_estimators | max_depth | MAE | R² | Status |
|---|---|---|---|---|---|
| v1 | 100 | 15 | 6.49 years | 0.70 | **@production** |
| v2 | 50 | 10 | 8.54 years | 0.59 | — |

See `analyse_retraining.md` for the full before/after retraining analysis.
