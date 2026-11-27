from pathlib import Path
import pickle

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report
)

# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parent

DATA_PATH = ROOT / "dataset" / "fertilizer.csv"
MODEL_PATH = ROOT / "models" / "Fertilizer.pkl"

# =========================================================
# LOAD DATA
# =========================================================

data = pd.read_csv(DATA_PATH)

data = data.drop(columns=["Unnamed: 0"], errors="ignore")

print("Dataset loaded successfully.")
print("Dataset shape:", data.shape)

# =========================================================
# FEATURES AND TARGET
# =========================================================

features = ["Crop", "N", "P", "K"]

target = "Fertilizer Name"

required_columns = features + [target]

missing_columns = [
    column for column in required_columns
    if column not in data.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns in dataset: {missing_columns}"
    )

data = data[required_columns].copy()

# =========================================================
# CLEAN DATA
# =========================================================

for column in ["N", "P", "K"]:
    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )

data["Crop"] = (
    data["Crop"]
    .astype(str)
    .str.strip()
    .str.lower()
)

data[target] = (
    data[target]
    .astype(str)
    .str.strip()
)

data = data.dropna(subset=required_columns)

data = data[
    (data["Crop"] != "") &
    (data[target] != "")
]

if data.empty:
    raise ValueError("No valid training rows found.")

print("\nFertilizer distribution:")
print(data[target].value_counts())

# =========================================================
# FEATURES
# =========================================================

X = data[features]
y = data[target]

categorical_features = ["Crop"]

numerical_features = ["N", "P", "K"]

# =========================================================
# PREPROCESSING
# =========================================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "crop_encoder",
            OneHotEncoder(
                handle_unknown="ignore"
            ),
            categorical_features
        )
    ],
    remainder="passthrough"
)

# =========================================================
# MODEL
# =========================================================

model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),

        (
            "classifier",
            RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                class_weight="balanced",
                max_features="sqrt"
            )
        )
    ]
)

# =========================================================
# TRAIN / TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# =========================================================
# TRAIN FOR EVALUATION
# =========================================================

evaluation_model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),

        (
            "classifier",
            RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                class_weight="balanced",
                max_features="sqrt"
            )
        )
    ]
)

evaluation_model.fit(X_train, y_train)

# =========================================================
# EVALUATION
# =========================================================

predictions = evaluation_model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

precision = precision_score(
    y_test,
    predictions,
    average="weighted",
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    average="weighted",
    zero_division=0
)

f1 = f1_score(
    y_test,
    predictions,
    average="weighted",
    zero_division=0
)

print("\n========== MODEL EVALUATION ==========")

print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print(f"F1 Score:  {f1:.4f}")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)

# =========================================================
# TRAIN FINAL MODEL ON FULL DATASET
# =========================================================

final_model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),

        (
            "classifier",
            RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                class_weight="balanced",
                max_features="sqrt"
            )
        )
    ]
)

final_model.fit(X, y)

# =========================================================
# SAVE MODEL
# =========================================================

MODEL_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(MODEL_PATH, "wb") as file:
    pickle.dump(final_model, file)

# =========================================================
# SUMMARY
# =========================================================

print("\n========== TRAINING COMPLETE ==========")

print(f"Training rows: {len(X)}")
print(f"Training samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")
print(f"Crop classes: {data['Crop'].nunique()}")
print(f"Fertilizer classes: {y.nunique()}")

print(f"\nModel saved at:")
print(MODEL_PATH)

print("\nFertilizer classes:")
print(list(final_model.classes_))

print("\nModel successfully trained!")