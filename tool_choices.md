# DataProphet — Tool Choices & Justification

## Overview

This document explains the rationale behind each technology chosen for the DataProphet
MLOps pipeline. Each tool is evaluated against the specific needs of the project,
with an alternative and a justification for the final choice.

---

## 1. FastAPI

**Problem it solves in DataProphet**
The model needed to be exposed as a real-time REST API that could receive tree features,
call the RandomForest, and return a predicted planting year in milliseconds.
FastAPI also needed to expose a `/metrics` endpoint for Prometheus scraping and a
`/api/helpdata` endpoint for user feedback collection.

**Alternative considered**
Flask — the most common Python web framework for ML APIs.

**Why FastAPI**
FastAPI provides automatic OpenAPI documentation (Swagger UI at `/docs`) out of the box,
which was essential for testing endpoints without writing curl commands during development.
Its native Pydantic integration enforced input validation on `ArvoreFeatures` and `HelpData`
schemas with zero boilerplate. Flask would have required additional libraries (Marshmallow,
flasgger) to achieve the same result. FastAPI's async support also makes it production-ready
for higher concurrency without framework changes.

---

## 2. MLflow

**Problem it solves in DataProphet**
Without MLflow, model versions were stored as local `.pkl` files with no traceability —
the classic `model_final_VRAIMENT_v3.pkl` problem. MLflow solved three distinct needs:
experiment tracking (logging MAE, R², RMSE per run), model registry (versioning and
promoting models via aliases), and model serving (the API loads `models:/DataProphet@production`
directly from the registry instead of a hardcoded file path).

**Alternative considered**
Weights & Biases (W&B) — a more feature-rich experiment tracking platform.

**Why MLflow**
MLflow is fully open-source and self-hosted, requiring no external account or API key.
For a local development stack, this meant zero configuration overhead. The Model Registry
alias system (`@production`) integrated directly with the FastAPI lifespan loader, making
model promotion a one-step operation from the UI or via `MlflowClient`. W&B would have
added external dependencies and costs at scale.

---

## 3. Prometheus + Grafana

**Problem it solves in DataProphet**
The API needed continuous observability — not just knowing it was running, but tracking
prediction volume, latency distribution (P95), and error rates over time. Prometheus
scraped `/metrics` every 15 seconds, storing time-series data. Grafana visualized this
data and triggered alerts when latency exceeded 500ms or prediction volume dropped.

**Alternative considered**
Datadog — a managed observability platform with built-in dashboards.

**Why Prometheus + Grafana**
Both tools are open-source, run locally without external dependencies, and integrate
natively with the `prometheus_client` Python library. Adding a `Counter` and `Histogram`
to `main.py` required fewer than 10 lines of code. Datadog would have required an agent,
an API key, and ongoing costs. For a self-contained MLOps stack, Prometheus + Grafana
provides the same core observability with full control over retention and alerting rules.

---

## 4. Apache Airflow

**Problem it solves in DataProphet**
The retraining pipeline (`retrain.py`) was triggered manually from the terminal.
If no one ran it for weeks, the model silently aged. Airflow automated the full weekly
cycle: reading feedback JSONs → validating and preparing data → retraining → conditional
promotion. The `BranchPythonOperator` in `dag_deploy` made the promotion decision
automatically based on R² improvement, removing human intervention from the loop.

**Alternative considered**
Cron jobs with bash scripts — the simplest possible scheduler.

**Why Airflow**
Cron jobs have no UI, no retry logic, no dependency management, and no visibility into
failures. Airflow provided a visual DAG graph showing task success/failure in real time,
automatic retries on failure, and the ability to chain DAGs with `TriggerDagRunOperator`.
The `dag_mlops_weekly` master DAG encapsulates the entire pipeline in a single triggerable
unit. For a production MLOps system, this observability into the orchestration layer is
as important as the observability into the API itself.

---

## Summary Table

| Tool | Core need in DataProphet | Alternative | Key differentiator |
|---|---|---|---|
| FastAPI | Real-time prediction API + auto docs | Flask | Native Pydantic, Swagger UI, async |
| MLflow | Experiment tracking + model registry | W&B | Self-hosted, alias-based promotion |
| Prometheus | Metrics scraping + time-series storage | Datadog | Open-source, local, zero cost |
| Grafana | Dashboards + alerting | Datadog | Open-source, flexible, Prometheus-native |
| Airflow | Pipeline orchestration + scheduling | Cron | UI, retries, DAG dependencies, branching |
