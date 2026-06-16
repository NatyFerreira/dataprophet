"""
retrain.py — Retrains the model, compares it with the one in Production,
and automatically promotes it to Staging if the R² improves.

Usage:
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
ROC_AUC_THRESHOLD = 0.01   # minimum R² improvement required for promotion


def carregar_dados(caminho="data.pkl"):
    with open(caminho, "rb") as f:
        df = pickle.load(f)
    target = "anneedeplantation"
    df = df.dropna(subset=[target])

    # Check if feedback data exists in help_data/
    import os, json, glob
    feedback_files = glob.glob("help_data/*.json")
    if feedback_files:
        print(f"  {len(feedback_files)} feedback files found.")
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
                print(f"  Dataset augmented with feedback: {len(df)} rows.")
    else:
        print("  No feedback data — using base dataset.")

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
    """Fetches the R² of the model currently in Production."""
    try:
        modelo_prod = mlflow.sklearn.load_model(
            f"models:/{MODEL_NAME}/Production"
        )
        y_pred = modelo_prod.predict(X_test)
        return r2_score(y_test, y_pred)
    except Exception:
        print("  No model in Production found — first training.")
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
    print(f"  R² of Production model: {r2_prod:.4f}")

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

        print(f"  New model — R²: {r2:.4f}")

        # Automatic promotion to Staging if improved
        improvement = r2 - r2_prod
        if improvement > ROC_AUC_THRESHOLD:
            version = result.registered_model_version
            client.transition_model_version_stage(
                name=MODEL_NAME,
                version=version,
                stage="Staging",
            )
            print(f"  Model v{version} promoted to Staging (improvement: +{improvement:.4f})")
        else:
            print(f"  Insufficient improvement ({improvement:.4f}) — model not promoted.")


if __name__ == "__main__":
    retrain()