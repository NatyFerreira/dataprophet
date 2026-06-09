"""
retrain.py — Re-treina o modelo, compara com o que está em Produção
e promove automaticamente para Staging se melhorar o R².

Uso:
    python retrain.py
"""

import warnings
import pickle

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

warnings.filterwarnings("ignore")

MLFLOW_URI     = "http://localhost:5000"
EXPERIMENT     = "arvores-grenoble-retrain"
MODEL_NAME     = "DataProphet"
ROC_AUC_THRESHOLD = 0.01   # mínimo de melhoria em R² para promover


def carregar_dados(caminho="data.pkl"):
    with open(caminho, "rb") as f:
        df = pickle.load(f)
    target = "anneedeplantation"
    df = df.dropna(subset=[target])

    # Verifica se existem dados de feedback em help_data/
    import os, json, glob
    feedback_files = glob.glob("help_data/*.json")
    if feedback_files:
        print(f"  {len(feedback_files)} arquivos de feedback encontrados.")
        registros = []
        for path in feedback_files:
            try:
                with open(path) as f:
                    registros.append(json.load(f))
            except Exception:
                pass
        if registros:
            df_feedback = pd.DataFrame(registros)
            if target in df_feedback.columns:
                df = pd.concat([df, df_feedback], ignore_index=True)
                print(f"  Dataset aumentado com feedback: {len(df)} linhas.")
    else:
        print("  Sem dados de feedback — usando dataset base.")

    X = df.drop(columns=[target])
    y = df[target]
    return X, y


def criar_pipeline(n_estimators=100, max_depth=10):
    numeric_features     = ["latitude", "longitude"]
    categorical_features = [
        "genre_bota", "espece", "stadededeveloppement",
        "hauteurarbre", "typenature"
    ]
    preprocessor = ColumnTransformer([
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), numeric_features),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical_features),
    ])
    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
        )),
    ])


def r2_do_modelo_em_producao(client, X_test, y_test):
    """Busca o R² do modelo atualmente em Produção."""
    try:
        modelo_prod = mlflow.sklearn.load_model(
            f"models:/{MODEL_NAME}/Production"
        )
        y_pred = modelo_prod.predict(X_test)
        return r2_score(y_test, y_pred)
    except Exception:
        print("  Nenhum modelo em Produção encontrado — primeiro treino.")
        return -999


def retrain():
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient(MLFLOW_URI)

    X, y = carregar_dados()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    r2_prod = r2_do_modelo_em_producao(client, X_test, y_test)
    print(f"  R² do modelo em Produção: {r2_prod:.4f}")

    pipeline = criar_pipeline(n_estimators=100, max_depth=10)

    with mlflow.start_run() as run:
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        mae  = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2   = r2_score(y_test, y_pred)

        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth",    10)
        mlflow.log_metric("mae",  round(mae, 4))
        mlflow.log_metric("rmse", round(rmse, 4))
        mlflow.log_metric("r2",   round(r2, 4))

        result = mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )

        print(f"  Novo modelo — R²: {r2:.4f}")

        # Promoção automática para Staging se melhorar
        melhoria = r2 - r2_prod
        if melhoria > ROC_AUC_THRESHOLD:
            versao = result.registered_model_version
            client.transition_model_version_stage(
                name=MODEL_NAME,
                version=versao,
                stage="Staging",
            )
            print(f"  Modelo v{versao} promovido para Staging (melhoria: +{melhoria:.4f})")
        else:
            print(f"  Melhoria insuficiente ({melhoria:.4f}) — modelo não promovido.")


if __name__ == "__main__":
    retrain()
