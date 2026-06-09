import os
import time
import pandas as pd
import mlflow.sklearn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from schemas import ArvoreFeatures, PredictionResponse
from metrics import PREDICTION_COUNTER, PREDICTION_LATENCY

MLFLOW_URI = os.getenv("MLFLOW_URI", "http://localhost:5000")
MODEL_URI  = "models:/DataProphet@production"

app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carrega o modelo do MLflow Registry ao iniciar."""
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

@app.get("/health", tags=["status"])
def health():
    """Verifica se o serviço está ativo."""
    return {"status": "ok", "modelo_carregado": "model" in app_state}

@app.get("/metrics", tags=["status"])
def metrics():
    """Expõe métricas no formato Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/predict", response_model=PredictionResponse, tags=["predição"])
def predict(dados: ArvoreFeatures):
    """
    Recebe as características de uma árvore e retorna o
    ano de plantio estimado pelo modelo RandomForest.
    """
    if "model" not in app_state:
        raise HTTPException(status_code=503, detail="Modelo não disponível.")

    entrada = pd.DataFrame([dados.model_dump()])

    inicio = time.time()
    resultado = app_state["model"].predict(entrada)
    duracao = time.time() - inicio

    ano = float(resultado[0])

    # Label por década (ex: '1990s', '2000s')
    decada = f"{int(ano) // 10 * 10}s"
    PREDICTION_COUNTER.labels(decada=decada).inc()
    PREDICTION_LATENCY.observe(duracao)

    return PredictionResponse(
        annee_predite=round(ano, 2),
        annee_arrondie=round(ano),
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
