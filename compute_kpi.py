"""
compute_kpi.py — Business KPI Level 3
Calculates the model's precision based on corrections stored in help_data/
and the user correction rate (difference between predicted vs annee_correcte).
"""

import os
import json
import glob
import requests

API_URL = "http://localhost:8000/api/predict"
HELP_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help_data")
TOLERANCE_YEARS = 5  # prediction considered "correct" if within +/- 5 years


def load_feedback():
    files = glob.glob(os.path.join(HELP_DATA_DIR, "*.json"))
    records = []
    for f in files:
        with open(f) as fp:
            records.append(json.load(fp))
    return records


def predict(record):
    payload = {
        k: v for k, v in record.items()
        if k not in ("label_correct", "annee_correcte")
    }
    response = requests.post(API_URL, json=payload, timeout=5)
    response.raise_for_status()
    return response.json()["annee_arrondie"]


def main():
    records = load_feedback()
    if not records:
        print("No feedback found in help_data/. Nothing to compute.")
        return

    total = len(records)
    api_success = 0
    results = []

    # Counters for the correction-rate KPI
    n_with_correction = 0
    n_predictions_within_tolerance = 0

    for r in records:
        try:
            predicted = predict(r)
            api_success += 1

            annee_correcte = r.get("annee_correcte")
            entry = {
                "genre_bota": r.get("genre_bota"),
                "predicted": predicted,
                "annee_correcte": annee_correcte,
            }

            if annee_correcte is not None:
                n_with_correction += 1
                diff = abs(predicted - annee_correcte)
                entry["diff_years"] = diff
                if diff <= TOLERANCE_YEARS:
                    n_predictions_within_tolerance += 1

            results.append(entry)

        except Exception as e:
            print(f"Prediction error: {e}")

    print(f"\n{'='*55}")
    print("DataProphet - KPI Level 3 (Business)")
    print(f"{'='*55}")
    print(f"Total feedbacks analyzed         : {total}")
    print(f"Successful predictions (API)     : {api_success}")
    print(f"API success rate                 : {api_success/total*100:.1f}%")

    if n_with_correction > 0:
        accuracy = n_predictions_within_tolerance / n_with_correction * 100
        print(f"\nFeedbacks with year correction   : {n_with_correction}")
        print(f"Predictions within +/-{TOLERANCE_YEARS} years : {n_predictions_within_tolerance}")
        print(f"Correction rate (true accuracy)  : {accuracy:.1f}%")
    else:
        print("\nNo feedback contains 'annee_correcte' -- ")
        print("correction rate cannot be computed with current data.")
        print("(Existing feedbacks use the legacy field 'label_correct'.)")

    print(f"\nDetails:")
    for r in results:
        diff_str = f" | diff: {r['diff_years']} years" if "diff_years" in r else ""
        print(f"  {r['genre_bota']:<20} -> predicted: {r['predicted']} | correct: {r['annee_correcte']}{diff_str}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
