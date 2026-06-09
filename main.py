import joblib
import numpy as np
import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from schemas import ArvoreFeatures, PredictionResponse


# — Estado global da aplicação —
# O modelo é carregado UMA VEZ quando o servidor inicia
# e fica em memória. Não recarrega a cada predição.
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executa no início e no fim do servidor."""
    # INÍCIO: carrega o modelo
    try:
        app_state["model"] = joblib.load("ml1_rf_model.pkl")
        print("✓ Modelo carregado com sucesso.")
    except FileNotFoundError:
        print("✗ ERRO: ml1_rf_model.pkl não encontrado.")
        print("  Coloque o arquivo na mesma pasta que main.py.")
        raise
    yield
    # FIM: limpeza (opcional)
    app_state.clear()


# — Criação da aplicação —
app = FastAPI(
    title="DataProphet — Árvores de Grenoble",
    description="API de predição do ano de plantio de árvores urbanas.",
    version="1.0.0",
    lifespan=lifespan,
)


# — Rota 1: health check —
@app.get("/health", tags=["status"])
def health():
    """Verifica se o serviço está ativo."""
    return {"status": "ok", "modelo_carregado": "model" in app_state}


# — Rota 2: predição —
@app.post("/api/predict", response_model=PredictionResponse, tags=["predição"])
def predict(dados: ArvoreFeatures):
    """
    Recebe as características de uma árvore e retorna o
    ano de plantio estimado pelo modelo RandomForest.
    """
    if "model" not in app_state:
        raise HTTPException(status_code=503, detail="Modelo não disponível.")

    # Converte o schema Pydantic para DataFrame
    # (o pipeline sklearn espera um DataFrame com os nomes das colunas)
    entrada = pd.DataFrame([dados.model_dump()])

    # Predição
    resultado = app_state["model"].predict(entrada)
    ano = float(resultado[0])

    return PredictionResponse(
        annee_predite=round(ano, 2),
        annee_arrondie=round(ano),
    )


# — Ponto de entrada —
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
