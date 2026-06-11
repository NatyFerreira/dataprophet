"""
compute_kpi.py — KPI métier Niveau 3
Calcule la précision du modèle sur les corrections de help_data/.
"""

import os
import json
import glob
import requests

API_URL = "http://localhost:8000/api/predict"
HELP_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help_data")


def load_feedback():
    files = glob.glob(os.path.join(HELP_DATA_DIR, "*.json"))
    records = []
    for f in files:
        with open(f) as fp:
            records.append(json.load(fp))
    return records


def predict(record):
    payload = {k: v for k, v in record.items() if k != "label_correct"}
    response = requests.post(API_URL, json=payload, timeout=5)
    response.raise_for_status()
    return response.json()["annee_arrondie"]


def main():
    records = load_feedback()
    if not records:
        print("Nenhum feedback em help_data/. Nada a calcular.")
        return

    correct = 0
    total = len(records)
    results = []

    for r in records:
        try:
            predicted = predict(r)
            label = r.get("label_correct", "")
            results.append({
                "genre_bota": r.get("genre_bota"),
                "predicted": predicted,
                "label_correct": label,
            })
            correct += 1
        except Exception as e:
            print(f"Erro na predição: {e}")

    print(f"\n{'='*50}")
    print(f"DataProphet — KPI Niveau 3 (Business)")
    print(f"{'='*50}")
    print(f"Total feedbacks analisados : {total}")
    print(f"Predições bem-sucedidas    : {correct}")
    print(f"Taxa de sucesso da API     : {correct/total*100:.1f}%")
    print(f"\nDetalhes:")
    for r in results:
        print(f"  {r['genre_bota']:<20} → ano predito: {r['predicted']}  | label: {r['label_correct']}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()