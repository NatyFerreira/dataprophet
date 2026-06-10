# DataProphet — Árvores de Grenoble

API MLOps de predição do ano de plantio de árvores urbanas de Grenoble.  
Modelo: RandomForestRegressor treinado em 31 670 árvores (R² = 0.70).

---

## Arquitetura

```
dataprophet/
├── main.py              # API FastAPI (predição + métricas + feedback)
├── schemas.py           # Schemas Pydantic (ArvoreFeatures, HelpData)
├── metrics.py           # Métricas Prometheus (Counter, Histogram)
├── train.py             # Treino + logging MLflow
├── retrain.py           # Retraining automático com promoção
├── prometheus.yml       # Configuração scraping Prometheus
├── docker-compose.yml   # MLflow Server
├── environment.yml      # Dependências conda
├── help_data/           # Feedback dos usuários (JSONs)
└── README.md
```

---

## Stack

| Componente | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn |
| Modelo | scikit-learn 1.2.2 (RandomForest) |
| Tracking | MLflow 3.13 |
| Registry | MLflow Model Registry (alias `production`) |
| Métricas | prometheus-client |
| Monitoring | Prometheus 3.12 + Grafana 13 |
| Ambiente | conda Python 3.11 |

---

## Instalação

```bash
# 1. Criar e ativar o ambiente
conda env create -f environment.yml
conda activate dataprophet

# 2. Instalar dependências adicionais
pip install mlflow prometheus-client
```

---

## Iniciar os serviços

### 1. MLflow (Tracking Server)
```bash
mlflow server --host 0.0.0.0 --port 5000 &
```

### 2. Treinar e registrar o modelo
```bash
python train.py --n_estimators 100 --max_depth 15
```
Depois promover para production no MLflow UI (`http://localhost:5000`):  
Models → DataProphet → Version 1 → Aliases → Add → `production`

### 3. API FastAPI
```bash
uvicorn main:app --reload --port 8000
```

### 4. Prometheus
```bash
prometheus --config.file=prometheus.yml --web.listen-address=":9090" &
```

### 5. Grafana
```bash
grafana server --homepath /opt/homebrew/share/grafana &
```
Acesso: `http://localhost:3000` (admin/admin)

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API |
| GET | `/metrics` | Métricas Prometheus |
| POST | `/api/predict` | Predição do ano de plantio |
| POST | `/api/helpdata` | Feedback do usuário |

---

## Predição

```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "genre_bota": "Prunus",
    "espece": "serrulata",
    "stadededeveloppement": "Arbre jeune",
    "hauteurarbre": "Moins de 10 m",
    "typenature": "Libre",
    "latitude": 45.167,
    "longitude": 5.740
  }'
```

Resposta:
```json
{
  "annee_predite": 2007.24,
  "annee_arrondie": 2007
}
```

---

## Feedback (fechar o ciclo MLOps)

```bash
curl -X POST http://localhost:8000/api/helpdata \
  -H "Content-Type: application/json" \
  -d '{
    "genre_bota": "Prunus",
    "espece": "serrulata",
    "stadededeveloppement": "Arbre jeune",
    "hauteurarbre": "Moins de 10 m",
    "typenature": "Libre",
    "latitude": 45.167,
    "longitude": 5.740,
    "label_correct": "stable"
  }'
```

Os JSONs são salvos em `help_data/` e usados pelo `retrain.py` no Dia 4.

---

## Monitoring

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` → dashboard **DataProphet — Monitoring Production**
  - Panel 1: Volume de predições por minuto
  - Panel 2: Latência média de predição (s)
  - Panel 3: Distribuição de predições por década

---

## Métricas de performance

| Versão | n_estimators | max_depth | MAE | R² |
|---|---|---|---|---|
| v1 (production) | 100 | 15 | 6.49 anos | 0.70 |
| v2 | 50 | 10 | 8.54 anos | 0.59 |
