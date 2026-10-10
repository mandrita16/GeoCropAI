
import os
import pickle
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Load dataset
data = pd.read_csv("dataset/Fertilizer Prediction.csv")

# Clean column names
data.columns = data.columns.str.strip()

# Standardize column names
data = data.rename(columns={
    "Temparature": "Temperature",
    "Humidity": "Humidity",
    "Moisture": "Moisture",
    "Soil Type": "Soil_Type",
    "Crop Type": "Crop_Type",
    "Nitrogen": "N",
    "Phosphorous": "P",
    "Potassium": "K",
    "Fertilizer Name": "Fertilizer"
})

# Features and target
numeric_features = [
    "Temperature",
    "Humidity",
    "Moisture",
    "N",
    "P",
    "K"
]

categorical_features = [
    "Soil_Type",
    "Crop_Type"
]

target = "Fertilizer"

required = numeric_features + categorical_features + [target]
missing = [col for col in required if col not in data.columns]

if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Keep required columns and remove incomplete rows
data = data[required].dropna().copy()

# Ensure numeric columns contain numeric values
for col in numeric_features:
    data[col] = pd.to_numeric(data[col], errors="raise")

X = data[numeric_features + categorical_features]
y = data[target].astype(str).str.strip()

# Check whether each class has enough examples for stratification
counts = y.value_counts()
if len(counts) < 2 or counts.min() < 2:
    raise ValueError(
        "Each fertilizer class needs at least 2 rows "
        "for this stratified train/test split."
    )

# Preprocess categorical features; preserve numeric features
preprocessor = ColumnTransformer(
    transformers=[
        ("categorical", OneHotEncoder(handle_unknown="ignore"),
         categorical_features),
        ("numeric", "passthrough", numeric_features)
    ]
)

# Complete pipeline
model = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced"
    ))
])

# Split data before training
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# Train and evaluate
model.fit(X_train, y_train)
predictions = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, predictions))
print(classification_report(
    y_test, predictions, zero_division=0
))

# Save complete pipeline
os.makedirs("models", exist_ok=True)

with open("models/Fertilizer.pkl", "wb") as f:
    pickle.dump(model, f)

print("Fertilizer.pkl saved successfully!")
print("Input features:", list(X.columns))
print("Fertilizer classes:", list(model.classes_))
