# DataProphet — Before/After Retraining Analysis

## 1. Context

The model currently in production is **Version 1** of the MLflow registry (`@production`),
trained on 09/06/2026 on the full dataset of 31,670 urban trees from Grenoble
(`data.pkl`), with hyperparameters `n_estimators=100` and `max_depth=15`.
The target is the planting year (`anneedeplantation`), treated as a regression problem.

---

## 2. Comparative Results

| Run | Experiment | Date | n_estimators | max_depth | MAE (years) | R² | RMSE |
|---|---|---|---|---|---|---|---|
| classy-dolphin-247 (train) | arvores-grenoble | 09/06/2026 | 50 | 10 | 8.54 | 0.591 | 11.52 |
| **rumbling-asp-30 (train — production)** | arvores-grenoble | 09/06/2026 | **100** | **15** | **6.49** | **0.703** | **9.81** |
| judicious-snipe-787 (retrain) | arvores-grenoble-retrain | 10/06/2026 | 100 | 10 | 8.53 | 0.592 | 11.49 |
| bright-dove-901 (retrain) | arvores-grenoble-retrain | 10/06/2026 | 100 | 10 | 8.53 | 0.592 | 11.49 |

> All retraining runs use `max_depth=10` — the default value in `retrain.py`.

---

## 3. Decision

**The new model should not be promoted to Production.**

The production model (R²=0.703, MAE=6.49 years) significantly outperforms all retraining
runs (R²=0.592, MAE=8.53 years). The R² gap is **0.111 points**, well above the 1%
improvement threshold configured in `dag_deploy.py`.

The `BranchPythonOperator` in `dag_deploy` correctly decided `skip_promotion` —
the current production model is maintained.

The performance gap is primarily explained by the `max_depth` hyperparameter:
the production model uses `max_depth=15` versus `max_depth=10` in `retrain.py`.
To improve retraining results, these parameters should be aligned or a hyperparameter
search should be implemented in the pipeline.

---

## 4. Limitations

- **Insufficient feedback volume**: `help_data/` contains only 5 entries,
  all identical (Prunus serrulata). Retraining was therefore performed on a dataset
  that does not represent the diversity of tree species.

- **Non-optimized hyperparameters**: `retrain.py` uses `max_depth=10` by default,
  lower than the `max_depth=15` of the production model. A hyperparameter search
  (GridSearchCV) should be integrated into the pipeline.

- **Overfitting risk**: with only 5 feedback examples, any model retrained on this
  data risks overfitting these cases without generalizing.

- **Representativeness**: all feedbacks come from the same species and the same user —
  they do not reflect the real distribution of trees in Grenoble.
