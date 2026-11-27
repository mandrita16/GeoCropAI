import os
import math
import asyncio
from pathlib import Path

import httpx
from dotenv import load_dotenv

from fastapi import APIRouter, HTTPException, Query


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/weather",
    tags=["Weather"],
)


# ============================================================
# OPENWEATHER CONFIGURATION
# ============================================================

OPENWEATHER_URL = (
    "https://api.openweathermap.org/data/2.5/weather"
)


# ============================================================
# WEATHER ENDPOINT
# ============================================================

@router.get("")
async def get_weather(
    city: str | None = Query(
        default=None,
        description="City name, e.g. Kolkata",
    ),

    lat: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description="Latitude",
    ),

    lon: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description="Longitude",
    ),
):

    # ========================================================
    # 1. VALIDATE LOCATION INPUT
    # ========================================================

    if city is not None:

        city = city.strip()

        if not city:

            raise HTTPException(
                status_code=400,
                detail="City name cannot be empty",
            )

        if len(city) < 2:

            raise HTTPException(
                status_code=400,
                detail="City name must contain at least 2 characters",
            )

    coordinates_provided = (
        lat is not None or lon is not None
    )

    # Both coordinates must be provided
    if coordinates_provided and (
        lat is None or lon is None
    ):

        raise HTTPException(
            status_code=400,
            detail="Both latitude and longitude must be provided",
        )

    # Require either city or coordinates
    if not city and not coordinates_provided:

        raise HTTPException(
            status_code=400,
            detail="Provide either a city or latitude and longitude",
        )

    # Do not allow both location methods
    if city and coordinates_provided:

        raise HTTPException(
            status_code=400,
            detail="Provide either city or coordinates, not both",
        )


    # ========================================================
    # 2. API KEY VALIDATION
    # ========================================================

    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:

        raise HTTPException(
            status_code=503,
            detail="Weather service is not configured",
        )


    # ========================================================
    # 3. REQUEST PARAMETERS
    # ========================================================

    params = {
        "appid": api_key,
        "units": "metric",
    }

    if city:

        params["q"] = city

    else:

        params["lat"] = lat
        params["lon"] = lon


    # ========================================================
    # 4. CALL WEATHER PROVIDER WITH RETRY
    # ========================================================

    data = None

    max_attempts = 2

    for attempt in range(max_attempts):

        try:

            timeout = httpx.Timeout(
                20.0,
                connect=8.0,
            )

            async with httpx.AsyncClient(
                timeout=timeout,
            ) as client:

                response = await client.get(
                    OPENWEATHER_URL,
                    params=params,
                )


            # ------------------------------------------------
            # PROVIDER ERROR HANDLING
            # ------------------------------------------------

            if response.status_code == 404:

                raise HTTPException(
                    status_code=404,
                    detail="Location not found",
                )

            if response.status_code == 401:

                raise HTTPException(
                    status_code=502,
                    detail="Weather provider rejected the API key",
                )

            if response.status_code == 429:

                raise HTTPException(
                    status_code=503,
                    detail="Weather service rate limit exceeded",
                )

            if response.status_code >= 500:

                raise HTTPException(
                    status_code=502,
                    detail="Weather provider is currently unavailable",
                )

            response.raise_for_status()

            data = response.json()

            # Successful request
            break


        # ------------------------------------------------
        # HTTP EXCEPTIONS
        # ------------------------------------------------

        except HTTPException:

            raise


        # ------------------------------------------------
        # TIMEOUT HANDLING
        # ------------------------------------------------

        except httpx.TimeoutException:

            if attempt < max_attempts - 1:

                await asyncio.sleep(1)

                continue

            raise HTTPException(
                status_code=504,
                detail="Weather provider request timed out. Please try again.",
            )


        # ------------------------------------------------
        # CONNECTION ERROR HANDLING
        # ------------------------------------------------

        except httpx.RequestError:

            if attempt < max_attempts - 1:

                await asyncio.sleep(1)

                continue

            raise HTTPException(
                status_code=503,
                detail="Could not connect to the weather provider",
            )


        # ------------------------------------------------
        # HTTP STATUS ERROR
        # ------------------------------------------------

        except httpx.HTTPStatusError:

            raise HTTPException(
                status_code=502,
                detail="Weather provider returned an unexpected error",
            )


        # ------------------------------------------------
        # INVALID JSON
        # ------------------------------------------------

        except ValueError:

            raise HTTPException(
                status_code=502,
                detail="Invalid response received from weather provider",
            )


    # ========================================================
    # 5. VALIDATE RESPONSE STRUCTURE
    # ========================================================

    try:

        weather_data = data["weather"][0]

        main_data = data["main"]

        location_data = data["sys"]

        coordinate_data = data["coord"]

        rainfall_data = data.get("rain", {})

        location_name = data["name"]

        country = location_data["country"]

        temperature = main_data["temp"]

        humidity = main_data["humidity"]

        pressure = main_data["pressure"]

        weather_description = weather_data["description"]

        latitude = coordinate_data.get("lat")

        longitude = coordinate_data.get("lon")

        rainfall_1h = rainfall_data.get("1h", 0)

        rainfall_3h = rainfall_data.get("3h", 0)

        rainfall_available = bool(rainfall_data)


    except (
        KeyError,
        IndexError,
        TypeError,
        AttributeError,
    ):

        raise HTTPException(
            status_code=502,
            detail="Weather provider returned incomplete weather data",
        )


    # ========================================================
    # 6. VALIDATE NUMERIC DATA
    # ========================================================

    numeric_values = [
        temperature,
        humidity,
        pressure,
        rainfall_1h,
        rainfall_3h,
    ]

    try:

        for value in numeric_values:

            if not isinstance(value, (int, float)):

                raise ValueError

            if not math.isfinite(value):

                raise ValueError


    except (ValueError, TypeError):

        raise HTTPException(
            status_code=502,
            detail="Weather provider returned invalid numeric data",
        )


    # ========================================================
    # 7. RESPONSE
    # ========================================================

    return {

        "success": True,

        "location": location_name,

        "country": country,

        "coordinates": {
            "latitude": latitude,
            "longitude": longitude,
        },

        "temperature": temperature,

        "humidity": humidity,

        "pressure": pressure,

        "weather": weather_description,

        "rainfall_last_hour_mm": rainfall_1h,

        "rainfall_last_3_hours_mm": rainfall_3h,

        "rainfall_data_available": rainfall_available,

        "data_source": "OpenWeather Current Weather API",

        "rainfall_note": (
            "Current rainfall measurements are not equivalent "
            "to seasonal or annual rainfall."
        ),

    }