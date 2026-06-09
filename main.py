import os
import time
import pandas as pd
import mlflow.sklearn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from schemas import ArvoreFeatures, PredictionResponse

MLFLOW_URI = os.getenv("MLFLOW_URI", "http://localhost:5000")
MODEL_URI  = "models:/DataProphet/Production"

app_state = {}

# ---------------------------------------------------------
# MÉTRICAS PROMETHEUS (KIT 3)
# ---------------------------------------------------------

PREDICTIONS_TOTAL = Counter(
    "dataprophet_predictions_total",
    "Número total de predições realizadas pela API"
)

PREDICTION_LATENCY = Histogram(
    "dataprophet_prediction_latency_seconds",
    "Latência do endpoint /api/predict"
)

# ---------------------------------------------------------
# LIFESPAN — CARREGAR MODELO DO REGISTRY
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        app_state["model"] = mlflow.sklearn.load_model(MODEL_URI)
        print(f"✓ Modelo carregado do Registry: {MODEL_URI}")
    except Exception as e:
        print(f"✗ ERRO ao carregar modelo do Registry: {e}")
        print("  Certifique-se que o MLflow está rodando e há um modelo em Production.")
        raise
    yield
    app_state.clear()


app = FastAPI(
    title="DataProphet — Árvores de Grenoble",
    description="API de predição do ano de plantio de árvores urbanas.",
    version="3.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------
# HEALTHCHECK
# ---------------------------------------------------------

@app.get("/health", tags=["status"])
def health():
    return {"status": "ok", "modelo_carregado": "model" in app_state}

# ---------------------------------------------------------
# ENDPOINT DE PREDIÇÃO + MÉTRICAS
# ---------------------------------------------------------

@app.post("/api/predict", response_model=PredictionResponse, tags=["predição"])
def predict(dados: ArvoreFeatures):
    if "model" not in app_state:
        raise HTTPException(status_code=503, detail="Modelo não disponível.")

    start = time.time()

    entrada = pd.DataFrame([dados.model_dump()])
    resultado = app_state["model"].predict(entrada)
    ano = float(resultado[0])

    # Atualiza métricas
    PREDICTIONS_TOTAL.inc()
    PREDICTION_LATENCY.observe(time.time() - start)

    return PredictionResponse(
        annee_predite=round(ano, 2),
        annee_arrondie=round(ano),
    )

# ---------------------------------------------------------
# ENDPOINT /metrics PARA PROMETHEUS
# ---------------------------------------------------------

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------
# ENDPOINT /api/helpdata — FEEDBACK DO USUÁRIO (KIT 3)
# ---------------------------------------------------------

import json
from datetime import datetime
from schemas import HelpData  # <-- você vai adicionar esse schema no schemas.py

HELPDATA_DIR = "help_data"
os.makedirs(HELPDATA_DIR, exist_ok=True)

@app.post("/api/helpdata", tags=["feedback"])
def save_helpdata(data: HelpData):
    """Salva feedback do usuário em help_data/ como JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{HELPDATA_DIR}/{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(data.model_dump(), f, indent=4)

    return {
        "status": "ok",
        "message": "Feedback salvo com sucesso",
        "file": filename,
    }

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
