
from pathlib import Path
import json
import pickle

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset" / "Crop_recommendation.csv"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "RandomForest.pkl"
METRICS_PATH = MODEL_DIR / "crop_metrics.json"

FEATURES = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall",
]
TARGET = "label"


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    data = pd.read_csv(DATA_PATH)

    required = FEATURES + [TARGET]
    missing_columns = set(required) - set(data.columns)

    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")

    data = data[required].copy()

    print("Original rows:", len(data))
    print("Missing values:\n", data.isnull().sum())
    print("Duplicate rows:", int(data.duplicated().sum()))

    # Remove exact duplicate rows and incomplete records.
    data = data.drop_duplicates()
    data = data.dropna(subset=required)

    # Validate numerical features.
    for column in FEATURES:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=FEATURES)
    data = data[data[TARGET].astype(str).str.strip() != ""]
    data[TARGET] = data[TARGET].astype(str).str.strip()

    if data.empty:
        raise ValueError("No valid rows remain after preprocessing.")

    X = data[FEATURES]
    y = data[TARGET]

    if y.nunique() < 2:
        raise ValueError("At least two crop classes are required.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
        class_weight=None,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    print(f"\nTraining rows: {len(X_train)}")
    print(f"Testing rows: {len(X_test)}")
    print(f"Crop classes: {y.nunique()}")
    print(f"Test accuracy: {accuracy:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, predictions, zero_division=0))

    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions, labels=model.classes_))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Save only after training and evaluation succeed.
    with MODEL_PATH.open("wb") as file:
        pickle.dump(model, file)

    metrics = {
        "features": FEATURES,
        "target": TARGET,
        "algorithm": "RandomForestClassifier",
        "n_estimators": 200,
        "random_state": 42,
        "test_size": 0.20,
        "test_accuracy": float(accuracy),
        "training_rows": len(X_train),
        "testing_rows": len(X_test),
        "classes": [str(c) for c in model.classes_],
    }

    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    print(f"\nSaved model: {MODEL_PATH}")
    print(f"Saved metrics: {METRICS_PATH}")


if __name__ == "__main__":
    main()
