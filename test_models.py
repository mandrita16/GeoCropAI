
from pathlib import Path
import pickle
import json

import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    ConfusionMatrixDisplay,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "model_test_results"
OUT.mkdir(exist_ok=True)


def save_results(name, y_test, predictions, note=None):
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(
        y_test, predictions, output_dict=True, zero_division=0
    )

    print(f"\n{name.title()} model accuracy: {accuracy:.4%}")
    print(classification_report(y_test, predictions, zero_division=0))

    results = {
        "accuracy": float(accuracy),
        "report": report,
        "test_samples": int(len(y_test)),
    }

    if note:
        results["note"] = note

    with open(OUT / f"{name}_metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    fig, ax = plt.subplots(figsize=(10, 8))
    ConfusionMatrixDisplay.from_predictions(
        y_test,
        predictions,
        xticks_rotation="vertical",
        cmap="Greens",
        ax=ax,
        colorbar=False,
        values_format="d",
    )
    ax.set_title(f"{name.title()} Model — Confusion Matrix")
    fig.tight_layout()
    fig.savefig(OUT / f"{name}_confusion_matrix.png", dpi=180)
    plt.close(fig)


def split_data(X, y):
    """Use stratification only when the class counts allow it."""
    class_counts = y.value_counts()
    stratify_target = y if class_counts.min() >= 2 else None

    # Ensure the test set can contain at least one sample per class
    # when stratification is possible.
    if stratify_target is not None:
        n_classes = y.nunique()
        n_test = max(1, int(len(y) * 0.20))

        if n_test < n_classes or len(y) - n_test < n_classes:
            stratify_target = None

    return train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=stratify_target,
    )


def evaluate_crop():
    data_path = ROOT / "dataset" / "Crop_recommendation.csv"
    model_path = ROOT / "models" / "RandomForest.pkl"

    data = pd.read_csv(data_path)
    features = [
        "N", "P", "K", "temperature",
        "humidity", "ph", "rainfall"
    ]
    target = "label"

    data = data[features + [target]].dropna().copy()
    X, y = data[features], data[target]

    # The crop training script must use the same 80/20 split
    # and random_state=42 for this holdout evaluation.
    _, X_test, _, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    predictions = model.predict(X_test)

    save_results(
        "crop",
        y_test,
        predictions,
        note="Evaluation of the saved crop model on the matching holdout split.",
    )

    print("\nCrop evaluation complete.")


def evaluate_fertilizer():
    data_path = ROOT / "dataset" / "fertilizer.csv"

    data = pd.read_csv(data_path)
    data = data.drop(columns=["Unnamed: 0"], errors="ignore")

    features = ["N", "P", "K", "pH", "soil_moisture"]
    target = "Crop"

    for col in features:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data[target] = data[target].astype("string").str.strip()
    data = data.dropna(subset=features + [target])
    data = data[data[target] != ""]

    X, y = data[features], data[target]

    if len(data) < 2:
        print("\nFertilizer evaluation skipped: not enough valid samples.")
        return

    print("\nFertilizer class distribution:")
    print(y.value_counts())

    X_train, X_test, y_train, y_test = split_data(X, y)

    # This is a separate evaluation-only model.
    # It does NOT overwrite models/Fertilizer.pkl.
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    save_results(
        "fertilizer",
        y_test,
        predictions,
        note=(
            "Evaluation-only model trained on a dataset split. "
            "Results do not measure the existing Fertilizer.pkl model."
        ),
    )

    print("\nFertilizer evaluation complete.")


if __name__ == "__main__":
    evaluate_crop()
    evaluate_fertilizer()
    print(f"\nResults saved in: {OUT}")
