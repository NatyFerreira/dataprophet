# SmartRetail — Churn Prediction MLOps Pipeline

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Airflow](https://img.shields.io/badge/Apache_Airflow-2.10.5-017CEE?logo=apacheairflow)
![MLflow](https://img.shields.io/badge/MLflow-3.14-0194E2?logo=mlflow)
![FastAPI](https://img.shields.io/badge/FastAPI-inference-009688?logo=fastapi)
![Prometheus](https://img.shields.io/badge/Prometheus-3.12-E6522C?logo=prometheus)
![Grafana](https://img.shields.io/badge/Grafana-13.0-F46800?logo=grafana)
![License](https://img.shields.io/badge/License-MIT-green)

MLOps pipeline for customer churn prediction in a retail context.  
Model: RandomForestClassifier with threshold calibration (AUC-ROC = 0.552 baseline, threshold = 0.825).  
Built as a certification project (RNCP 37624 — Bloc 4 Data Engineer & AI, Campus Numérique in the Alps, 2026).

---

## Architecture

```
smartretail-churn/
├── pipeline/
│   ├── app.py                  # FastAPI serving layer (/predict, /health, /metrics, /admin/reload-model)
│   ├── preprocessing.py        # Data cleaning encapsulated as a reusable module
│   ├── train.py                # Training, MLflow logging, model registration, alias promotion
│   ├── smartretail_dag.py      # Airflow DAG — preprocess >> train
│   └── requirements.txt        # Pinned dependencies
├── monitoring/
│   └── prometheus.yml          # Prometheus scrape config (localhost:8000/metrics every 15s)
├── Dataset/
│   └── dataset_churn_simule.csv  # Simulated dataset — 499 rows × 6 columns (no real customer data)
├── Dossier_Numerique/
│   ├── PARTIE 1/               # Data audit & model comparison
│   ├── PARTIE 2/               # Model optimisation
│   ├── PARTIE 3/               # Architecture & deployment
│   ├── PARTIE 4/               # GDPR & regulatory framework
│   ├── PARTIE 5/               # Monitoring KPIs & drift detection
│   └── PARTIE 6/               # Final presentation (7-slide jury deck)
└── README.md
```

Pipeline flow:

```
Dataset (simulated)
      │
      ▼
┌─────────────────────────────────┐
│         Apache Airflow DAG      │
│     preprocess  ──▶  train      │
└─────────────────────────────────┘
      │
      ▼
┌─────────────┐     ┌──────────────────┐
│   FastAPI   │────▶│  MLflow Registry │
│  /predict   │     │  (@production)   │
│ /admin/...  │     └──────────────────┘
└─────────────┘
      │
      ▼
┌─────────────────────────────────────────────┐
│           Prometheus + Grafana              │
│  Level 1 — Model: prediction distribution, │
│            AUC drift, confidence scores     │
│  Level 2 — Data: feature drift, missingness │
│  Level 3 — System: latency, throughput,     │
│            error rates                      │
└─────────────────────────────────────────────┘
```

See [`Dossier_Numerique/PARTIE 3/Architecture_Diagram.png`](Dossier_Numerique/PARTIE%203/Architecture_Diagram.png) for the full architecture diagram.  
See [`Dossier_Numerique/PARTIE 5/Mission6_Drift_Detection_Loop.svg`](Dossier_Numerique/PARTIE%205/Mission6_Drift_Detection_Loop.svg) for the drift detection and retraining loop.

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| API Server | Uvicorn (ASGI) |
| ML Model | scikit-learn — RandomForestClassifier |
| Imbalance handling | SMOTE + class_weight + Random Undersampling |
| Hyperparameter tuning | GridSearchCV |
| Experiment Tracking | MLflow 3.14 |
| Model Registry | MLflow Registry (`@production` alias) |
| Metrics | prometheus-client |
| Monitoring | Prometheus 3.12 + Grafana 13.0 |
| Orchestration | Apache Airflow 2.10.5 |
| Environment | Conda (Python 3.11) |

> **Zero-downtime model reload:** The model is loaded once at startup. After a promotion, `POST /admin/reload-model` swaps the model in memory without restarting the server.

---

## Installation

```bash
# Create and activate the environment
conda create -n smartretail_pipeline python=3.11
conda activate smartretail_pipeline

# Install dependencies
pip install -r pipeline/requirements.txt
```

---

## Starting the Services

### 1. MLflow Tracking Server
```bash
mlflow server --host 0.0.0.0 --port 5000 &
```

### 2. Train and Register the Model
```bash
python pipeline/train.py
```
Promote the model to Production via MLflow UI (`http://localhost:5000`):  
Models → SmartRetail → Version 1 → Aliases → `production`

### 3. FastAPI / Uvicorn
```bash
cd pipeline
uvicorn app:app --reload --port 8000
```

Reload the production model without restarting:
```bash
curl -X POST http://localhost:8000/admin/reload-model
```

### 4. Prometheus
```bash
prometheus --config.file=/absolute/path/to/monitoring/prometheus.yml --web.listen-address=":9090" &
```
> Use absolute path — Prometheus does not expand `~` in `--config.file`.

### 5. Grafana
```bash
grafana server --homepath /opt/homebrew/share/grafana &
```
Access: `http://localhost:3000` (admin/admin)

### 6. Airflow
```bash
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/pipeline
airflow standalone
```
Access: `http://localhost:8080`

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | API health check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/predict` | Predict churn probability for a customer |
| GET | `/admin/reload-model` | Reload production model (zero downtime) |

---

## Prediction Example

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "age": 45,
    "anciennete_mois": 24,
    "montant_achats": 1200.0,
    "nb_commandes": 8,
    "satisfaction_score": 3
  }'
```

Response:
```json
{
  "churn_probability": 0.34,
  "prediction": "no_churn",
  "threshold_applied": 0.825
}
```

---

## Model Reload (Zero Downtime)

```bash
curl -X POST http://localhost:8000/admin/reload-model
```

Response:
```json
{
  "status": "ok",
  "message": "Model successfully reloaded: models:/SmartRetail@production"
}
```

---

## Airflow DAG

The pipeline is orchestrated via `smartretail_dag.py`:

```
preprocess  ──▶  train
```

| Task | Description |
|------|-------------|
| `preprocess` | Feature engineering and data validation from raw dataset |
| `train` | Model training, MLflow logging, conditional promotion to `@production` |

To trigger manually:
1. Open `http://localhost:8080`
2. Find `smartretail_churn_pipeline`
3. Click ▶

---

## Monitoring Architecture (3 KPI Levels)

| Level | Scope | Metrics |
|-------|-------|---------|
| Level 1 — Model | Prediction quality | Prediction distribution, churn rate, confidence scores, AUC drift |
| Level 2 — Data | Feature drift | Feature distribution shifts, missing value rates |
| Level 3 — System | Infrastructure | API latency, request throughput, error rates |

KPI definitions: [`Dossier_Numerique/PARTIE 5/Mission6_KPI_List.md`](Dossier_Numerique/PARTIE%205/Mission6_KPI_List.md)

---

## Model Performance

| Version | Strategy | AUC-ROC | Threshold | Status |
|---------|----------|---------|-----------|--------|
| v1 — baseline | RandomForest (default) | 0.552 | 0.5 | — |
| v2 — optimised | SMOTE + GridSearchCV | improved | 0.825 | **@production** |

See [`Dossier_Numerique/PARTIE 2/Mission3_Optimization.ipynb`](Dossier_Numerique/PARTIE%202/Mission3_Optimization.ipynb) for the full before/after optimisation analysis including ROC curves and confusion matrices.

---

## Live Implementation Evidence

Three validated tests documented in [`Dossier_Numerique/PARTIE 3/Mission4_Live_Implementation_Annex.md`](Dossier_Numerique/PARTIE%203/Mission4_Live_Implementation_Annex.md):

1. **Zero-downtime hot-reload** — model swapped in memory without server restart
2. **Airflow DAG execution** — full pipeline triggered and completed via Airflow UI
3. **Real-time Prometheus/Grafana monitoring** — metrics scraped and visualised live

---

## GDPR Compliance

Documented in [`Dossier_Numerique/PARTIE 4/Mission5_GDPR_Regulatory_Note.md`](Dossier_Numerique/PARTIE%204/Mission5_GDPR_Regulatory_Note.md):

- Legal basis: legitimate interest
- Data minimisation applied to the 6-feature dataset
- Right to explanation documented for automated churn decisions
- Bias analysis included
- Data retention policy defined

---

## Note on Reproducibility

`Mission1_Data_Audit.ipynb`, `Mission2_Model_Comparison.ipynb`, and `Mission3_Optimization.ipynb` were verified to run end-to-end from a fresh kernel, starting only from `dataset_churn_simule.csv`.

All industrialization components (Airflow 2.10.5, MLflow 3.14, FastAPI, Prometheus 3.12, Grafana 13.0) were implemented and tested locally on macOS Apple Silicon M4 — see `Mission4_Live_Implementation_Annex.md` for full validation evidence.

---

## Author

**Natália Helen Ferreira**  
PhD in Biological Chemistry | Data Engineer & AI (RNCP Level 7, in progress)  
[LinkedIn](https://linkedin.com/in/ferreiranh) · [GitHub](https://github.com/NatyFerreira)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
