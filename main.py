import os
import time
import json
import glob
import pandas as pd
import mlflow.sklearn
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from schemas import ArvoreFeatures, PredictionResponse, HelpData
from metrics import (
    PREDICTION_COUNTER,
    PREDICTION_LATENCY,
    BUSINESS_API_SUCCESS_RATE,
    BUSINESS_CORRECTION_RATE,
    BUSINESS_FEEDBACK_COUNT,
)

MLFLOW_URI = os.getenv("MLFLOW_URI", "http://localhost:5000")
MODEL_URI  = "models:/DataProphet@production"

app_state = {}

HELPDATA_DIR = "help_data"
os.makedirs(HELPDATA_DIR, exist_ok=True)

TOLERANCE_YEARS = 5

# ---------------------------------------------------------
# LIFESPAN — LOAD MODEL FROM REGISTRY
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        app_state["model"] = mlflow.sklearn.load_model(MODEL_URI)
        print(f"✓ Model loaded from Registry: {MODEL_URI}")
    except Exception as e:
        print(f"✗ ERROR loading model from Registry: {e}")
        print("  Make sure MLflow is running and a model is in Production.")
        raise
    yield
    app_state.clear()


app = FastAPI(
    title="DataProphet — Trees of Grenoble",
    description="API for predicting the planting year of urban trees.",
    version="3.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------
# HEALTHCHECK
# ---------------------------------------------------------

@app.get("/health", tags=["status"])
def health():
    return {"status": "ok", "model_loaded": "model" in app_state}

# ---------------------------------------------------------
# AUXILIARY FUNCTION — decade from predicted year
# ---------------------------------------------------------

def get_decade(year: float) -> str:
    decade = (int(year) // 10) * 10
    return f"{decade}s"

# ---------------------------------------------------------
# PREDICTION ENDPOINT + METRICS
# ---------------------------------------------------------

@app.post("/api/predict", response_model=PredictionResponse, tags=["prediction"])
def predict(dados: ArvoreFeatures):
    if "model" not in app_state:
        raise HTTPException(status_code=503, detail="Model not available.")

    start = time.time()

    entrada = pd.DataFrame([dados.model_dump()])
    resultado = app_state["model"].predict(entrada)
    year = float(resultado[0])

    # Update metrics
    PREDICTION_COUNTER.labels(decade=get_decade(year)).inc()
    PREDICTION_LATENCY.observe(time.time() - start)

    return PredictionResponse(
        annee_predite=round(year, 2),
        annee_arrondie=round(year),
    )

# ---------------------------------------------------------
# /metrics ENDPOINT FOR PROMETHEUS
# ---------------------------------------------------------

@app.get("/metrics")
def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------
# /api/helpdata — USER FEEDBACK ENDPOINT (KIT 3)
# ---------------------------------------------------------

@app.post("/api/helpdata", tags=["feedback"])
def save_helpdata(data: HelpData):
    """Saves user feedback into help_data/ as JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{HELPDATA_DIR}/{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(data.model_dump(), f, indent=4)

    return {
        "status": "ok",
        "message": "Feedback saved successfully",
        "file": filename,
    }

# ---------------------------------------------------------
# /admin/reload-model — reload model without restart
# ---------------------------------------------------------

@app.post("/admin/reload-model", tags=["admin"])
def reload_model():
    """Reloads the @production model from MLflow Registry without restarting the process."""
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        new_model = mlflow.sklearn.load_model(MODEL_URI)
        app_state["model"] = new_model
        print(f"✓ Model reloaded: {MODEL_URI}")
        return {
            "status": "ok",
            "message": f"Model successfully reloaded: {MODEL_URI}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading model: {e}")

# ---------------------------------------------------------
# /admin/compute-kpi — compute Level 3 KPI and expose in /metrics
# ---------------------------------------------------------

@app.post("/admin/compute-kpi", tags=["admin"])
def compute_kpi():
    """Computes the Business KPI (Level 3) and updates Prometheus Gauges."""
    if "model" not in app_state:
        raise HTTPException(status_code=503, detail="Model not available.")

    files = glob.glob(os.path.join(HELPDATA_DIR, "*.json"))
    if not files:
        return {"status": "no_data", "message": "No feedback in help_data/."}

    total = len(files)
    api_success = 0
    n_with_correction = 0
    n_within_tolerance = 0

    for f in files:
        try:
            with open(f) as fp:
                record = json.load(fp)

            payload = {
                k: v for k, v in record.items()
                if k not in ("label_correct", "annee_correcte")
            }
            entrada = pd.DataFrame([payload])
            resultado = app_state["model"].predict(entrada)
            predicted = round(float(resultado[0]))
            api_success += 1

            annee_correcte = record.get("annee_correcte")
            if annee_correcte is not None:
                n_with_correction += 1
                if abs(predicted - annee_correcte) <= TOLERANCE_YEARS:
                    n_within_tolerance += 1
        except Exception:
            continue

    success_rate = (api_success / total * 100) if total else 0
    correction_rate = (n_within_tolerance / n_with_correction * 100) if n_with_correction else 0

    BUSINESS_API_SUCCESS_RATE.set(success_rate)
    BUSINESS_CORRECTION_RATE.set(correction_rate)
    BUSINESS_FEEDBACK_COUNT.set(total)

    return {
        "status": "ok",
        "total_feedbacks": total,
        "api_success_rate": round(success_rate, 1),
        "feedbacks_with_correction": n_with_correction,
        "correction_rate": round(correction_rate, 1),
    }

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)