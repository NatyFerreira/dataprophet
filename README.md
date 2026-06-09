# DataProphet — Árvores de Grenoble

API de predição do ano de plantio de árvores urbanas de Grenoble.  
Modelo: RandomForestRegressor treinado em 31 670 árvores.

---

## Estrutura

```
dataprophet/
├── main.py              # Servidor FastAPI
├── schemas.py           # Formato dos dados (Pydantic)
├── ml1_rf_model.pkl     # Modelo treinado (copiar aqui)
├── environment.yml      # Dependências
└── README.md
```

---

## Instalação

```bash
# 1. Criar e ativar o ambiente
conda env create -f environment.yml
conda activate dataprophet

# 2. Copiar o modelo para esta pasta
cp caminho/para/ml1_rf_model.pkl .
```

---

## Rodar a API

```bash
python main.py
```

O servidor sobe em `http://localhost:8000`.

---

## Testar

**Interface visual (recomendado):**  
Abrir `http://localhost:8000/docs` no browser → clicar em `/api/predict` → "Try it out".

**Via curl:**
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

**Resposta esperada:**
```json
{
  "annee_predite": 2008.3,
  "annee_arrondie": 2008
}
```
