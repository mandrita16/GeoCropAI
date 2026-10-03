import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier

# Load fertilizer dataset
data = pd.read_csv("dataset/fertilizer.csv")

# Remove unnecessary index column
data = data.drop(columns=["Unnamed: 0"])

# Input features
X = data[
    [
        "N",
        "P",
        "K",
        "pH",
        "soil_moisture"
    ]
]

# Target
y = data["Crop"]

# Create Random Forest model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

# Train model
model.fit(X, y)

# Save trained model
with open("models/Fertilizer.pkl", "wb") as f:
    pickle.dump(model, f)

print("New Fertilizer.pkl created successfully!")
print("Features:", list(X.columns))
print("Number of classes:", len(model.classes_))
print("Classes:", list(model.classes_))