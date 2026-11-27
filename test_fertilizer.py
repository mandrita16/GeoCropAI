import joblib
import pandas as pd

# Load trained fertilizer model
model = joblib.load("models/Fertilizer.pkl")

print("\n🌱 GEO CROP AI — FERTILIZER TESTER")
print("=" * 50)

while True:
    crop = input("\nEnter crop name (or 'exit'): ").strip()

    if crop.lower() == "exit":
        print("Exiting tester...")
        break

    try:
        N = float(input("Enter Nitrogen (N): "))
        P = float(input("Enter Phosphorus (P): "))
        K = float(input("Enter Potassium (K): "))

        # Prepare input in the exact format expected by model
        input_data = pd.DataFrame([
            {
                "Crop": crop,
                "N": N,
                "P": P,
                "K": K
            }
        ])

        # Predict fertilizer
        prediction = model.predict(input_data)[0]

        print("\n" + "=" * 50)
        print("🌿 FERTILIZER RECOMMENDATION")
        print("=" * 50)
        print(f"Crop                 : {crop}")
        print(f"Nitrogen             : {N}")
        print(f"Phosphorus           : {P}")
        print(f"Potassium            : {K}")
        print(f"\nRecommended Fertilizer: {prediction}")

        # Show confidence and alternatives
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(input_data)[0]
            classes = model.classes_

            results = sorted(
                zip(classes, probabilities),
                key=lambda x: x[1],
                reverse=True
            )

            print("\n📊 MODEL CONFIDENCE")
            print("-" * 30)

            for fertilizer, probability in results[:3]:
                print(
                    f"{fertilizer:<15} "
                    f"{probability * 100:.2f}%"
                )

        print("=" * 50)

    except ValueError:
        print("❌ Please enter valid numerical NPK values.")

    except Exception as e:
        print(f"❌ Error: {e}")