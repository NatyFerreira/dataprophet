import os
import pandas as pd
import mlflow.sklearn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from schemas import ArvoreFeatures, PredictionResponse

MLFLOW_URI   = os.getenv("MLFLOW_URI", "http://localhost:5000")
MODEL_URI    = f"models:/DataProphet@production"

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
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["status"])
def health():
    """Verifica se o serviço está ativo."""
    return {"status": "ok", "modelo_carregado": "model" in app_state}


@app.post("/api/predict", response_model=PredictionResponse, tags=["predição"])
def predict(dados: ArvoreFeatures):
    """
    Recebe as características de uma árvore e retorna o
    ano de plantio estimado pelo modelo RandomForest.
    """
    if "model" not in app_state:
        raise HTTPException(status_code=503, detail="Modelo não disponível.")

    entrada = pd.DataFrame([dados.model_dump()])
    resultado = app_state["model"].predict(entrada)
    ano = float(resultado[0])

    return PredictionResponse(
        annee_predite=round(ano, 2),
        annee_arrondie=round(ano),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
