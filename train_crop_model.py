import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier

# Load dataset
data = pd.read_csv("dataset/Crop_recommendation.csv")

# Input features
X = data[[
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall"
]]

# Target
y = data["label"]

# Create Random Forest model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

# Train
model.fit(X, y)

# Save model
with open("models/RandomForest.pkl", "wb") as f:
    pickle.dump(model, f)

print("New RandomForest.pkl created successfully!")
print("Features:", list(X.columns))
print("Number of classes:", len(model.classes_))