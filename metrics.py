# metrics.py — Prometheus Metrics for DataProphet
from prometheus_client import Counter, Histogram, Gauge

# Prediction counter by decade (label: decade)
PREDICTION_COUNTER = Counter(
    "dataprophet_predictions_total",
    "Total number of predictions performed",
    ["decade"],  # e.g., '1990s', '2000s', '2010s'
)

# Prediction latency histogram (in seconds)
PREDICTION_LATENCY = Histogram(
    "dataprophet_prediction_duration_seconds",
    "Duration of each prediction in seconds",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# ---------------------------------------------------------
# KPI Level 3 — Business (computed via compute_kpi.py,
# exposed here via Gauge for Grafana visualization)
# ---------------------------------------------------------

BUSINESS_API_SUCCESS_RATE = Gauge(
    "dataprophet_kpi_api_success_rate",
    "API success rate over help_data/ feedbacks (%)",
)

BUSINESS_CORRECTION_RATE = Gauge(
    "dataprophet_kpi_correction_rate",
    "Rate of predictions within tolerance vs user correction (%)",
)

BUSINESS_FEEDBACK_COUNT = Gauge(
    "dataprophet_kpi_feedback_count",
    "Total number of feedback entries analyzed in help_data/",
)
