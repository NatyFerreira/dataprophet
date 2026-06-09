# metrics.py — Métriques Prometheus pour DataProphet
from prometheus_client import Counter, Histogram

# Contador de predições por faixa de ano (label: decada)
PREDICTION_COUNTER = Counter(
    "dataprophet_predictions_total",
    "Número total de predições realizadas",
    ["decada"],  # ex: '1990s', '2000s', '2010s'
)

# Histograma de latência por predição (em segundos)
PREDICTION_LATENCY = Histogram(
    "dataprophet_prediction_duration_seconds",
    "Duração de cada predição em segundos",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)
