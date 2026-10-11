
import os

import httpx
import joblib
import numpy as np
import pandas as pd

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from utils.fertilizer import fertilizer_dic


router = APIRouter(
    prefix="/ml",
    tags=["ML Models"]
)

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


# ============================================================
# CROP RECOMMENDATION MODEL
# ============================================================

CROP_MODEL_PATH = os.path.join(
    BASE_DIR, "models", "RandomForest.pkl"
)

try:
    crop_model = joblib.load(CROP_MODEL_PATH)
except Exception as e:
    crop_model = None
    print(f"Crop model loading error: {e}")


# ============================================================
# FERTILIZER DATASET
# ============================================================

FERTILIZER_DATASET_PATH = os.path.join(
    BASE_DIR, "dataset", "fertilizer.csv"
)

try:
    fertilizer_data = pd.read_csv(
        FERTILIZER_DATASET_PATH
    )
except Exception as e:
    fertilizer_data = None
    print(f"Fertilizer dataset loading error: {e}")


# ============================================================
# CROP RECOMMENDATION REQUEST
# Temperature and humidity come from OpenWeatherMap.
# ============================================================

class CropRequest(BaseModel):
    city: str = Field(..., min_length=2)
    nitrogen: float = Field(..., ge=0)
    phosphorus: float = Field(..., ge=0)
    potassium: float = Field(..., ge=0)
    ph: float = Field(..., ge=0, le=14)

    # Rainfall is still supplied by the user.
    # It should represent a suitable seasonal/growing-period
    # rainfall value, not the current hourly rainfall.
    rainfall: float = Field(..., ge=0)


# ============================================================
# CROP RECOMMENDATION ENDPOINT
# ============================================================

@router.post("/crop-recommendation")
async def recommend_crop(data: CropRequest):

    if crop_model is None:
        raise HTTPException(
            status_code=500,
            detail="Crop recommendation model could not be loaded"
        )

    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENWEATHER_API_KEY is missing from the root .env file"
        )

    try:
        # Fetch current weather for the selected city.
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": data.city.strip(),
                    "appid": api_key,
                    "units": "metric"
                }
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="City not found"
            )

        if response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="Weather API key is invalid or not activated"
            )

        response.raise_for_status()
        weather_data = response.json()

        temperature = float(weather_data["main"]["temp"])
        humidity = float(weather_data["main"]["humidity"])

        # Keep the feature order consistent with model training:
        # N, P, K, temperature, humidity, pH, rainfall.
        features = np.array([[
            data.nitrogen,
            data.phosphorus,
            data.potassium,
            temperature,
            humidity,
            data.ph,
            data.rainfall
        ]])

        prediction = crop_model.predict(features)[0]

        if hasattr(prediction, "item"):
            prediction = prediction.item()

        return {
            "success": True,
            "location": weather_data["name"],
            "country": weather_data["sys"]["country"],
            "weather": {
                "temperature": temperature,
                "humidity": humidity,
                "description": weather_data["weather"][0]["description"]
            },
            "soil": {
                "nitrogen": data.nitrogen,
                "phosphorus": data.phosphorus,
                "potassium": data.potassium,
                "ph": data.ph,
                "rainfall_used_mm": data.rainfall
            },
            "recommended_crop": str(prediction)
        }

    except HTTPException:
        raise

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to the weather provider"
        )

    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="Weather provider returned an error"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Crop prediction failed: {str(e)}"
        )


# ============================================================
# FERTILIZER RECOMMENDATION REQUEST
# ============================================================

class FertilizerRequest(BaseModel):
    crop_name: str = Field(..., min_length=1)
    nitrogen: float = Field(..., ge=0)
    phosphorus: float = Field(..., ge=0)
    potassium: float = Field(..., ge=0)


# ============================================================
# FERTILIZER RECOMMENDATION ENDPOINT
# ============================================================

@router.post("/fertilizer-recommendation")
def recommend_fertilizer(data: FertilizerRequest):

    if fertilizer_data is None:
        raise HTTPException(
            status_code=500,
            detail="Fertilizer dataset could not be loaded"
        )

    try:
        required_columns = {"Crop", "N", "P", "K"}

        if not required_columns.issubset(fertilizer_data.columns):
            raise HTTPException(
                status_code=500,
                detail="Fertilizer dataset must contain Crop, N, P and K columns"
            )

        crop_data = fertilizer_data[
            fertilizer_data["Crop"].astype(str).str.strip().str.lower()
            == data.crop_name.strip().lower()
        ]

        if crop_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No fertilizer data found for crop: {data.crop_name}"
            )

        required_n = float(crop_data["N"].iloc[0])
        required_p = float(crop_data["P"].iloc[0])
        required_k = float(crop_data["K"].iloc[0])

        # Positive difference means the target value is higher
        # than the supplied soil nutrient value.
        n_difference = required_n - data.nitrogen
        p_difference = required_p - data.phosphorus
        k_difference = required_k - data.potassium

        differences = {
            "N": abs(n_difference),
            "P": abs(p_difference),
            "K": abs(k_difference)
        }

        nutrient = max(differences, key=differences.get)

        if nutrient == "N":
            recommendation_key = (
                "NHigh" if n_difference < 0 else "Nlow"
            )
        elif nutrient == "P":
            recommendation_key = (
                "PHigh" if p_difference < 0 else "Plow"
            )
        else:
            recommendation_key = (
                "KHigh" if k_difference < 0 else "Klow"
            )

        recommendation = fertilizer_dic.get(recommendation_key)

        if recommendation is None:
            raise HTTPException(
                status_code=500,
                detail=f"Missing fertilizer rule: {recommendation_key}"
            )

        return {
            "success": True,
            "crop": data.crop_name.strip(),
            "required_npk": {
                "nitrogen": required_n,
                "phosphorus": required_p,
                "potassium": required_k
            },
            "soil_npk": {
                "nitrogen": float(data.nitrogen),
                "phosphorus": float(data.phosphorus),
                "potassium": float(data.potassium)
            },
            "largest_difference": nutrient,
            "recommendation_key": recommendation_key,
            "recommendation": str(recommendation)
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fertilizer recommendation failed: {str(e)}"
        )
