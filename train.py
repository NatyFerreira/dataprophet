"""
train.py — Treina o modelo e registra tudo no MLflow.

Uso:
    python train.py                          # parâmetros padrão
    python train.py --n_estimators 50 --max_depth 10
"""

import argparse
import warnings
import pickle

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

warnings.filterwarnings("ignore")

MLFLOW_URI      = "http://localhost:5000"
EXPERIMENT_NAME = "arvores-grenoble"
MODEL_NAME      = "DataProphet"


def carregar_dados(caminho="data.pkl"):
    with open(caminho, "rb") as f:
        df = pickle.load(f)
    target = "anneedeplantation"
    df = df.dropna(subset=[target])
    X = df.drop(columns=[target])
    y = df[target]
    return X, y


def criar_pipeline(n_estimators, max_depth):
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


def treinar(n_estimators=100, max_depth=15):
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    X, y = carregar_dados()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = criar_pipeline(n_estimators, max_depth)

    with mlflow.start_run():
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        mae  = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2   = r2_score(y_test, y_pred)

        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth",    max_depth)
        mlflow.log_metric("mae",  round(mae, 4))
        mlflow.log_metric("rmse", round(rmse, 4))
        mlflow.log_metric("r2",   round(r2, 4))

        # Compatível com MLflow server v2.x
        mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )

        print(f"✓ Run concluído:")
        print(f"  n_estimators = {n_estimators}")
        print(f"  max_depth    = {max_depth}")
        print(f"  MAE          = {mae:.2f} anos")
        print(f"  RMSE         = {rmse:.2f} anos")
        print(f"  R²           = {r2:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_estimators", type=int, default=100)
    parser.add_argument("--max_depth",    type=int, default=15)
    args = parser.parse_args()
    treinar(args.n_estimators, args.max_depth)
