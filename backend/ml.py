import os
import math

import httpx
import joblib
import numpy as np
import pandas as pd

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from utils.fertilizer import fertilizer_dic


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/ml",
    tags=["ML Models"]
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_DIR = os.path.join(BASE_DIR, "models")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")


# ============================================================
# CROP RECOMMENDATION MODEL
# ============================================================

CROP_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "RandomForest.pkl"
)

CROP_DATASET_PATH = os.path.join(
    DATASET_DIR,
    "Crop_recommendation.csv"
)

CROP_FEATURES = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall"
]

EXPECTED_CROP_CLASSES = 22

crop_model = None
crop_model_error = None

try:

    if not os.path.exists(CROP_MODEL_PATH):
        raise FileNotFoundError(
            f"Crop model not found: {CROP_MODEL_PATH}"
        )

    crop_model = joblib.load(CROP_MODEL_PATH)

    # --------------------------------------------------------
    # Validate model structure
    # --------------------------------------------------------

    if not hasattr(crop_model, "predict"):
        raise TypeError(
            "Loaded model does not support prediction."
        )

    model_feature_count = getattr(
        crop_model,
        "n_features_in_",
        None
    )

    if model_feature_count != len(CROP_FEATURES):
        raise ValueError(
            "Crop model feature count mismatch. "
            f"Expected {len(CROP_FEATURES)}, "
            f"found {model_feature_count}."
        )

    # --------------------------------------------------------
    # Validate feature names and ordering
    # --------------------------------------------------------

    model_features = getattr(
        crop_model,
        "feature_names_in_",
        None
    )

    if model_features is not None:

        model_features = list(model_features)

        if model_features != CROP_FEATURES:
            raise ValueError(
                "Crop model feature order mismatch. "
                f"Expected {CROP_FEATURES}, "
                f"found {model_features}."
            )

    # --------------------------------------------------------
    # Validate crop classes
    # --------------------------------------------------------

    model_classes = getattr(
        crop_model,
        "classes_",
        None
    )

    if model_classes is None:
        raise ValueError(
            "Crop model does not contain class information."
        )

    if len(model_classes) != EXPECTED_CROP_CLASSES:
        raise ValueError(
            f"Expected {EXPECTED_CROP_CLASSES} crop classes, "
            f"found {len(model_classes)}."
        )

    print("Crop model loaded successfully.")
    print(f"Model type: {type(crop_model).__name__}")
    print(f"Features: {len(CROP_FEATURES)}")
    print(f"Crop classes: {len(model_classes)}")

except Exception as e:

    crop_model = None
    crop_model_error = str(e)

    print(f"Crop model loading error: {e}")


# ============================================================
# CROP DATASET RANGE INFORMATION
# ============================================================

crop_feature_ranges = None

try:

    if os.path.exists(CROP_DATASET_PATH):

        crop_dataset = pd.read_csv(
            CROP_DATASET_PATH
        )

        missing_columns = set(CROP_FEATURES) - set(
            crop_dataset.columns
        )

        if missing_columns:
            raise ValueError(
                f"Crop dataset missing columns: "
                f"{sorted(missing_columns)}"
            )

        crop_dataset = crop_dataset[CROP_FEATURES].copy()

        for column in CROP_FEATURES:

            crop_dataset[column] = pd.to_numeric(
                crop_dataset[column],
                errors="coerce"
            )

        crop_dataset = crop_dataset.dropna(
            subset=CROP_FEATURES
        )

        crop_feature_ranges = {
            feature: {
                "min": float(crop_dataset[feature].min()),
                "max": float(crop_dataset[feature].max())
            }
            for feature in CROP_FEATURES
        }

        print("Crop dataset ranges loaded successfully.")

    else:

        print(
            "Crop dataset not found. "
            "Range validation warnings will be unavailable."
        )

except Exception as e:

    crop_feature_ranges = None

    print(
        f"Crop dataset range loading error: {e}"
    )


# ============================================================
# FERTILIZER DATASET
# ============================================================

FERTILIZER_DATASET_PATH = os.path.join(
    DATASET_DIR,
    "fertilizer.csv"
)

fertilizer_data = None
fertilizer_data_error = None

try:

    if not os.path.exists(FERTILIZER_DATASET_PATH):
        raise FileNotFoundError(
            f"Fertilizer dataset not found: "
            f"{FERTILIZER_DATASET_PATH}"
        )

    fertilizer_data = pd.read_csv(
        FERTILIZER_DATASET_PATH
    )

    required_columns = {
        "Crop",
        "N",
        "P",
        "K"
    }

    missing_columns = required_columns - set(
        fertilizer_data.columns
    )

    if missing_columns:
        raise ValueError(
            f"Fertilizer dataset missing columns: "
            f"{sorted(missing_columns)}"
        )

    # Convert nutrient values to numeric
    for column in ["N", "P", "K"]:

        fertilizer_data[column] = pd.to_numeric(
            fertilizer_data[column],
            errors="coerce"
        )

    fertilizer_data = fertilizer_data.dropna(
        subset=["Crop", "N", "P", "K"]
    )

    print("Fertilizer dataset loaded successfully.")

except Exception as e:

    fertilizer_data = None
    fertilizer_data_error = str(e)

    print(
        f"Fertilizer dataset loading error: {e}"
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_finite_number(value):
    """
    Checks whether a value is a finite number.
    """

    try:

        return math.isfinite(float(value))

    except (TypeError, ValueError):

        return False


def get_crop_range_warnings(input_values):
    """
    Compare supplied features against the training dataset ranges.

    These are dataset boundaries, not universal agronomic limits.
    """

    warnings = []

    if crop_feature_ranges is None:
        return warnings

    for feature, value in input_values.items():

        feature_range = crop_feature_ranges.get(
            feature
        )

        if feature_range is None:
            continue

        minimum = feature_range["min"]
        maximum = feature_range["max"]

        if value < minimum or value > maximum:

            warnings.append({
                "feature": feature,
                "provided_value": value,
                "training_minimum": minimum,
                "training_maximum": maximum,
                "message": (
                    f"{feature} is outside the range "
                    f"observed in the training dataset."
                )
            })

    return warnings


# ============================================================
# CROP RECOMMENDATION REQUEST
# ============================================================

class CropRequest(BaseModel):

    city: str = Field(
        ...,
        min_length=2,
        description="City name for weather information"
    )

    nitrogen: float = Field(
        ...,
        ge=0
    )

    phosphorus: float = Field(
        ...,
        ge=0
    )

    potassium: float = Field(
        ...,
        ge=0
    )

    ph: float = Field(
        ...,
        ge=0,
        le=14
    )

    rainfall: float = Field(
        ...,
        ge=0,
        description=(
            "Agricultural or seasonal rainfall estimate in mm"
        )
    )

    # --------------------------------------------------------
    # Validate finite values
    # --------------------------------------------------------

    @validator(
        "nitrogen",
        "phosphorus",
        "potassium",
        "ph",
        "rainfall"
    )
    def validate_finite_values(cls, value):

        if not math.isfinite(value):

            raise ValueError(
                "Value must be a finite number."
            )

        return value

    # --------------------------------------------------------
    # Validate city
    # --------------------------------------------------------

    @validator("city")
    def validate_city(cls, value):

        value = value.strip()

        if not value:

            raise ValueError(
                "City name cannot be empty."
            )

        if len(value) < 2:

            raise ValueError(
                "City name must contain at least 2 characters."
            )

        return value


# ============================================================
# CROP RECOMMENDATION ENDPOINT
# ============================================================

@router.post("/crop-recommendation")
async def recommend_crop(data: CropRequest):

    # --------------------------------------------------------
    # 1. Check model availability
    # --------------------------------------------------------

    if crop_model is None:

        raise HTTPException(
            status_code=503,
            detail="Crop recommendation model is unavailable."
        )

    # --------------------------------------------------------
    # 2. Check weather API configuration
    # --------------------------------------------------------

    api_key = os.getenv(
        "OPENWEATHER_API_KEY"
    )

    if not api_key:

        raise HTTPException(
            status_code=503,
            detail="Weather API configuration is missing."
        )

    city = data.city

    # --------------------------------------------------------
    # 3. Fetch current weather information
    # --------------------------------------------------------

    try:

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": city,
                    "appid": api_key,
                    "units": "metric"
                }
            )

        # ----------------------------------------------------
        # Weather API error handling
        # ----------------------------------------------------

        if response.status_code == 404:

            raise HTTPException(
                status_code=404,
                detail=f"City not found: {city}"
            )

        if response.status_code == 401:

            raise HTTPException(
                status_code=502,
                detail="Weather API authentication failed."
            )

        if response.status_code == 429:

            raise HTTPException(
                status_code=503,
                detail="Weather API rate limit exceeded."
            )

        response.raise_for_status()

        weather_data = response.json()

        # ----------------------------------------------------
        # 4. Extract weather data
        # ----------------------------------------------------

        temperature = float(
            weather_data["main"]["temp"]
        )

        humidity = float(
            weather_data["main"]["humidity"]
        )

        weather_description = (
            weather_data["weather"][0]["description"]
            if weather_data.get("weather")
            else "Unavailable"
        )

        location_name = weather_data.get(
            "name",
            city
        )

        country = weather_data.get(
            "sys",
            {}
        ).get(
            "country",
            "Unknown"
        )

        # Validate API data
        if not is_finite_number(temperature):

            raise ValueError(
                "Invalid temperature returned by weather API."
            )

        if not is_finite_number(humidity):

            raise ValueError(
                "Invalid humidity returned by weather API."
            )

        # ----------------------------------------------------
        # 5. Prepare input features
        # ----------------------------------------------------

        input_values = {
            "N": float(data.nitrogen),
            "P": float(data.phosphorus),
            "K": float(data.potassium),
            "temperature": temperature,
            "humidity": humidity,
            "ph": float(data.ph),
            "rainfall": float(data.rainfall)
        }

        input_data = pd.DataFrame(
            [input_values],
            columns=CROP_FEATURES
        )

        # ----------------------------------------------------
        # 6. Check training dataset ranges
        # ----------------------------------------------------

        range_warnings = get_crop_range_warnings(
            input_values
        )

        # ----------------------------------------------------
        # 7. Generate crop prediction
        # ----------------------------------------------------

        predicted_crop = crop_model.predict(
            input_data
        )[0]

        # ----------------------------------------------------
        # 8. Generate top recommendations
        # ----------------------------------------------------

        top_recommendations = []

        if hasattr(crop_model, "predict_proba"):

            probabilities = crop_model.predict_proba(
                input_data
            )[0]

            crop_classes = crop_model.classes_

            sorted_indices = np.argsort(
                probabilities
            )[::-1]

            top_indices = sorted_indices[:3]

            for index in top_indices:

                top_recommendations.append({
                    "crop": str(crop_classes[index]),
                    "probability": round(
                        float(probabilities[index]) * 100,
                        2
                    )
                })

        # ----------------------------------------------------
        # 9. Return response
        # ----------------------------------------------------

        return {

            "success": True,

            "location": {
                "city": location_name,
                "country": country
            },

            "weather": {
                "temperature_celsius": temperature,
                "humidity_percent": humidity,
                "description": weather_description,
                "data_type": "Current weather"
            },

            "soil": {
                "nitrogen": data.nitrogen,
                "phosphorus": data.phosphorus,
                "potassium": data.potassium,
                "ph": data.ph,
                "rainfall_mm": data.rainfall
            },

            "recommended_crop": str(
                predicted_crop
            ),

            "top_recommendations": (
                top_recommendations
            ),

            "data_information": {

                "temperature_source": "Weather API",

                "humidity_source": "Weather API",

                "nitrogen_source": "User supplied",

                "phosphorus_source": "User supplied",

                "potassium_source": "User supplied",

                "ph_source": "User supplied",

                "rainfall_source": "User supplied",

                "rainfall_note": (
                    "Rainfall should represent a suitable "
                    "seasonal or agricultural estimate, "
                    "not current hourly rainfall."
                ),

                "prediction_score_note": (
                    "The model's prediction scores indicate "
                    "its relative classification confidence "
                    "for the supplied input. They are not "
                    "guaranteed probabilities of crop success."
                ),

                "training_dataset_range_warnings": (
                    range_warnings
                ),

                "range_warning_note": (
                    "Training dataset ranges represent the "
                    "observed feature ranges in the dataset. "
                    "They are not universal agricultural limits."
                )
            }
        }

    # --------------------------------------------------------
    # 10. Error handling
    # --------------------------------------------------------

    except HTTPException:

        raise

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=503,
            detail="Weather service timed out. Please try again."
        )

    except httpx.RequestError:

        raise HTTPException(
            status_code=503,
            detail="Unable to connect to the weather service."
        )

    except httpx.HTTPStatusError:

        raise HTTPException(
            status_code=502,
            detail="Weather service returned an error."
        )

    except (KeyError, TypeError, ValueError):

        raise HTTPException(
            status_code=502,
            detail="Invalid weather data received."
        )

    except Exception as e:

        print(
            f"Crop recommendation error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Crop recommendation failed."
        )


# ============================================================
# FERTILIZER RECOMMENDATION REQUEST
# ============================================================

class FertilizerRequest(BaseModel):

    crop_name: str = Field(
        ...,
        min_length=1
    )

    nitrogen: float = Field(
        ...,
        ge=0
    )

    phosphorus: float = Field(
        ...,
        ge=0
    )

    potassium: float = Field(
        ...,
        ge=0
    )

    @validator(
        "nitrogen",
        "phosphorus",
        "potassium"
    )
    def validate_finite_values(cls, value):

        if not math.isfinite(value):

            raise ValueError(
                "Nutrient values must be finite numbers."
            )

        return value

    @validator("crop_name")
    def validate_crop_name(cls, value):

        value = value.strip()

        if not value:

            raise ValueError(
                "Crop name cannot be empty."
            )

        return value


# ============================================================
# FERTILIZER RECOMMENDATION ENDPOINT
# ============================================================

@router.post("/fertilizer-recommendation")
def recommend_fertilizer(data: FertilizerRequest):

    # --------------------------------------------------------
    # 1. Check dataset availability
    # --------------------------------------------------------

    if fertilizer_data is None:

        raise HTTPException(
            status_code=503,
            detail="Fertilizer dataset could not be loaded."
        )

    try:

        required_columns = {
            "Crop",
            "N",
            "P",
            "K"
        }

        if not required_columns.issubset(
            fertilizer_data.columns
        ):

            raise HTTPException(
                status_code=500,
                detail=(
                    "Fertilizer dataset must contain "
                    "Crop, N, P and K columns."
                )
            )

        # ----------------------------------------------------
        # 2. Find crop reference values
        # ----------------------------------------------------

        crop_data = fertilizer_data[
            fertilizer_data["Crop"]
            .astype(str)
            .str.strip()
            .str.lower()
            == data.crop_name.lower()
        ]

        if crop_data.empty:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No fertilizer data found for crop: "
                    f"{data.crop_name}"
                )
            )

        # ----------------------------------------------------
        # 3. Handle duplicate crop entries
        # ----------------------------------------------------

        if len(crop_data) > 1:

            crop_data = crop_data[
                ["N", "P", "K"]
            ].drop_duplicates()

            if len(crop_data) > 1:

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Multiple different fertilizer "
                        "reference records exist for this crop."
                    )
                )

        # ----------------------------------------------------
        # 4. Extract reference values
        # ----------------------------------------------------

        required_n = float(
            crop_data["N"].iloc[0]
        )

        required_p = float(
            crop_data["P"].iloc[0]
        )

        required_k = float(
            crop_data["K"].iloc[0]
        )

        reference_values = {
            "N": required_n,
            "P": required_p,
            "K": required_k
        }

        soil_values = {
            "N": float(data.nitrogen),
            "P": float(data.phosphorus),
            "K": float(data.potassium)
        }

        # ----------------------------------------------------
        # 5. Validate reference values
        # ----------------------------------------------------

        for nutrient, value in reference_values.items():

            if not is_finite_number(value):

                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Invalid reference value for "
                        f"nutrient {nutrient}."
                    )
                )

            if value < 0:

                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Negative reference value found "
                        f"for nutrient {nutrient}."
                    )
                )

        # ----------------------------------------------------
        # 6. Analyze each nutrient
        # ----------------------------------------------------

        TOLERANCE_PERCENT = 10

        nutrient_analysis = {}

        nutrient_recommendations = []

        for nutrient in ["N", "P", "K"]:

            reference = reference_values[nutrient]

            soil_value = soil_values[nutrient]

            difference = reference - soil_value

            # ------------------------------------------------
            # Percentage difference
            # ------------------------------------------------

            if reference != 0:

                difference_percent = (
                    (soil_value - reference)
                    / reference
                ) * 100

            else:

                # Percentage difference is mathematically
                # undefined when reference value is zero.

                difference_percent = None

            # ------------------------------------------------
            # Determine nutrient status
            # ------------------------------------------------

            if reference == 0:

                if soil_value == 0:

                    status = "within_reference"

                    recommendation_key = None

                else:

                    status = "above_reference"

                    recommendation_key = (
                        "NHigh" if nutrient == "N"
                        else "PHigh" if nutrient == "P"
                        else "KHigh"
                    )

            elif difference_percent < -TOLERANCE_PERCENT:

                status = "below_reference"

                recommendation_key = (
                    "Nlow" if nutrient == "N"
                    else "Plow" if nutrient == "P"
                    else "Klow"
                )

            elif difference_percent > TOLERANCE_PERCENT:

                status = "above_reference"

                recommendation_key = (
                    "NHigh" if nutrient == "N"
                    else "PHigh" if nutrient == "P"
                    else "KHigh"
                )

            else:

                status = "within_reference"

                recommendation_key = None

            # ------------------------------------------------
            # Recommendation text
            # ------------------------------------------------

            if recommendation_key:

                recommendation_text = fertilizer_dic.get(
                    recommendation_key,
                    "No recommendation available."
                )

                nutrient_recommendations.append({

                    "nutrient": nutrient,

                    "status": status,

                    "recommendation_key": (
                        recommendation_key
                    ),

                    "recommendation": str(
                        recommendation_text
                    )
                })

            else:

                recommendation_text = (
                    "The supplied value is within the "
                    "initial reference tolerance. "
                    "Avoid making adjustments without "
                    "a soil test."
                )

            # ------------------------------------------------
            # Store nutrient analysis
            # ------------------------------------------------

            nutrient_analysis[nutrient] = {

                "reference_value": reference,

                "soil_value": soil_value,

                "difference": round(
                    difference,
                    2
                ),

                "percentage_difference": (
                    round(difference_percent, 2)
                    if difference_percent is not None
                    else None
                ),

                "status": status,

                "recommendation": (
                    recommendation_text
                )
            }

        # ----------------------------------------------------
        # 7. Determine largest relative deviation
        # ----------------------------------------------------

        nutrients_with_percentages = [
            nutrient
            for nutrient in nutrient_analysis
            if nutrient_analysis[nutrient][
                "percentage_difference"
            ] is not None
        ]

        if nutrients_with_percentages:

            largest_deviation_nutrient = max(
                nutrients_with_percentages,
                key=lambda nutrient: abs(
                    nutrient_analysis[nutrient][
                        "percentage_difference"
                    ]
                )
            )

        else:

            largest_deviation_nutrient = None

        # ----------------------------------------------------
        # 8. Generate summary
        # ----------------------------------------------------

        below_reference = [
            nutrient
            for nutrient, analysis
            in nutrient_analysis.items()
            if analysis["status"] == "below_reference"
        ]

        above_reference = [
            nutrient
            for nutrient, analysis
            in nutrient_analysis.items()
            if analysis["status"] == "above_reference"
        ]

        within_reference = [
            nutrient
            for nutrient, analysis
            in nutrient_analysis.items()
            if analysis["status"] == "within_reference"
        ]

        # ----------------------------------------------------
        # 9. Return response
        # ----------------------------------------------------

        return {

            "success": True,

            "crop": data.crop_name,

            "reference_type": (
                "Dataset crop reference values. "
                "These are not a substitute for "
                "a laboratory soil test or "
                "region-specific fertilizer prescription."
            ),

            "nutrient_analysis": nutrient_analysis,

            "summary": {

                "below_reference": below_reference,

                "above_reference": above_reference,

                "within_reference": within_reference,

                "largest_relative_deviation": (
                    largest_deviation_nutrient
                )
            },

            "recommendations": (
                nutrient_recommendations
            ),

            "tolerance_percent": (
                TOLERANCE_PERCENT
            )
        }

    # --------------------------------------------------------
    # 10. Error handling
    # --------------------------------------------------------

    except HTTPException:

        raise

    except Exception as e:

        print(
            f"Fertilizer recommendation error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Fertilizer recommendation failed."
        )