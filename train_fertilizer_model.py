
from pathlib import Path
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset" / "fertilizer.csv"
MODEL_PATH = ROOT / "models" / "Fertilizer.pkl"

data = pd.read_csv(DATA_PATH)
data = data.drop(columns=["Unnamed: 0"], errors="ignore")

features = ["N", "P", "K", "pH", "soil_moisture"]
target = "Crop"

required = features + [target]
missing = [col for col in required if col not in data.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

data = data[required].copy()

for col in features:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data[target] = data[target].astype("string").str.strip()
data = data.dropna(subset=required)
data = data[data[target] != ""]

if data.empty:
    raise ValueError("No valid training rows found.")

X = data[features]
y = data[target]

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42
)
model.fit(X, y)

MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

print(f"Training rows: {len(data)}")
print(f"Crop classes: {y.nunique()}")
print(f"Model saved to: {MODEL_PATH}")
print("Warning: This tiny dataset is for prototype use only.")
