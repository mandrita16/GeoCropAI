"""
GeoCropAI fertilizer model retraining script.

Run from the project root:
    python backend/train_fertilizer_model.py

Expected dataset:
    dataset/fertilizer.csv

Saved model:
    models/Fertilizer.pkl

The model intentionally uses only Crop, N, P, K to remain compatible
with the current API integration.
"""

from pathlib import Path
import json
import warnings

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "dataset" / "fertilizer.csv"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "Fertilizer.pkl"
METRICS_PATH = MODEL_DIR / "fertilizer_model_metrics.json"

FEATURES = ["Crop", "N", "P", "K"]
TARGET = "Fertilizer Name"

EXPECTED_CROPS = {
    "rice", "maize", "chickpea", "kidneybeans", "pigeonpeas",
    "mothbeans", "mungbean", "blackgram", "lentil", "pomegranate",
    "banana", "mango", "grapes", "watermelon", "muskmelon", "apple",
    "orange", "papaya", "coconut", "cotton", "jute", "coffee",
}


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}\n"
            "Place the updated CSV at dataset/fertilizer.csv."
        )

    df = pd.read_csv(DATASET_PATH)
    required = FEATURES + [TARGET]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[required].copy()
    df["Crop"] = df["Crop"].astype(str).str.strip().str.lower()
    df[TARGET] = df[TARGET].astype(str).str.strip()
    for col in ["N", "P", "K"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()
    df = df.drop_duplicates()

    print("=" * 65)
    print("GeoCropAI Fertilizer Model Training")
    print("=" * 65)
    print(f"Dataset: {DATASET_PATH}")
    print(f"Rows after cleaning: {len(df)}")
    print(f"Unique crops: {df['Crop'].nunique()}")
    print(f"Fertilizer classes: {df[TARGET].nunique()}")
    print("\nClass distribution:")
    print(df[TARGET].value_counts().to_string())

    present_crops = set(df["Crop"].unique())
    missing_crops = sorted(EXPECTED_CROPS - present_crops)
    extra_crops = sorted(present_crops - EXPECTED_CROPS)
    if missing_crops:
        print("\nWARNING: These frontend crops are missing from dataset:")
        print(missing_crops)
    else:
        print("\nAll 22 frontend crops are present.")
    if extra_crops:
        print("Additional crops in dataset:", extra_crops)

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "crop",
                OneHotEncoder(handle_unknown="ignore"),
                ["Crop"],
            ),
            (
                "numeric",
                StandardScaler(),
                ["N", "P", "K"],
            ),
        ],
        remainder="drop",
    )

    candidates = {
        "RandomForest": RandomForestClassifier(
            n_estimators=400,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
    }

    results = {}
    trained_pipelines = {}

    for name, classifier in candidates.items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessing),
                ("classifier", classifier),
            ]
        )
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)

        metrics = {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision_macro": float(
                precision_score(y_test, predictions, average="macro", zero_division=0)
            ),
            "recall_macro": float(
                recall_score(y_test, predictions, average="macro", zero_division=0)
            ),
            "f1_macro": float(
                f1_score(y_test, predictions, average="macro", zero_division=0)
            ),
            "f1_weighted": float(
                f1_score(y_test, predictions, average="weighted", zero_division=0)
            ),
        }
        results[name] = metrics
        trained_pipelines[name] = pipeline

        print("\n" + "-" * 65)
        print(f"{name} evaluation")
        print("-" * 65)
        for metric, value in metrics.items():
            print(f"{metric:16s}: {value:.4f}")
        print("\nClassification report:")
        print(classification_report(y_test, predictions, zero_division=0))

    # Choose by macro F1 so smaller classes aren't ignored.
    best_name = max(results, key=lambda name: results[name]["f1_macro"])
    best_metrics = results[best_name]
    print(f"\nSelected model: {best_name} (macro F1={best_metrics['f1_macro']:.4f})")

    # Refit the selected pipeline on all available rows before deployment.
    final_model = trained_pipelines[best_name]
    final_model.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)

    report = {
        "dataset": str(DATASET_PATH.relative_to(ROOT)),
        "rows_used": int(len(df)),
        "features": FEATURES,
        "target": TARGET,
        "crops": sorted(df["Crop"].unique().tolist()),
        "classes": sorted(df[TARGET].unique().tolist()),
        "selected_model": best_name,
        "test_metrics": results,
        "note": (
            "Dataset is synthetic/expanded. Metrics measure consistency with "
            "dataset labels and do not establish agronomic validity."
        ),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 65)
    print("TRAINING COMPLETE")
    print("=" * 65)
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metrics: {METRICS_PATH}")
    print("Model features:", getattr(final_model, "feature_names_in_", FEATURES))
    print("\nAPI compatibility: Crop, N, P, K")


if __name__ == "__main__":
    main()
