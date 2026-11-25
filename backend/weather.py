
import os

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(
    prefix="/weather",
    tags=["Weather"]
)

OPENWEATHER_URL = (
    "https://api.openweathermap.org/data/2.5/weather"
)


# --------------------------------------------------
# Weather endpoint
# --------------------------------------------------

@router.get("")
async def get_weather(
    city: str | None = Query(
        default=None,
        min_length=2,
        description="City name, e.g. Kolkata"
    ),
    lat: float | None = Query(
        default=None,
        ge=-90,
        le=90,
        description="Latitude"
    ),
    lon: float | None = Query(
        default=None,
        ge=-180,
        le=180,
        description="Longitude"
    )
):

    # --------------------------------------------------
    # Validate location input
    # --------------------------------------------------

    if city:
        city = city.strip()

        if len(city) < 2:
            raise HTTPException(
                status_code=400,
                detail="City name must contain at least 2 characters"
            )

    coordinates_provided = (
        lat is not None or lon is not None
    )

    if coordinates_provided and (
        lat is None or lon is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Both latitude and longitude must be provided"
        )

    if not city and not coordinates_provided:
        raise HTTPException(
            status_code=400,
            detail="Provide either a city or latitude and longitude"
        )

    if city and coordinates_provided:
        raise HTTPException(
            status_code=400,
            detail="Provide either city or coordinates, not both"
        )


    # --------------------------------------------------
    # API key
    # --------------------------------------------------

    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Weather service is not configured"
        )


    # --------------------------------------------------
    # Request parameters
    # --------------------------------------------------

    params = {
        "appid": api_key,
        "units": "metric"
    }

    if city:
        params["q"] = city

    else:
        params["lat"] = lat
        params["lon"] = lon


    # --------------------------------------------------
    # Call weather provider
    # --------------------------------------------------

    try:

        timeout = httpx.Timeout(
            10.0,
            connect=5.0
        )

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            response = await client.get(
                OPENWEATHER_URL,
                params=params
            )


        # City/location not found
        if response.status_code == 404:

            raise HTTPException(
                status_code=404,
                detail="Location not found"
            )


        # Invalid API key
        if response.status_code == 401:

            raise HTTPException(
                status_code=502,
                detail="Weather provider rejected the API key"
            )


        # Rate limit
        if response.status_code == 429:

            raise HTTPException(
                status_code=503,
                detail="Weather service rate limit exceeded"
            )


        response.raise_for_status()

        data = response.json()


    # --------------------------------------------------
    # Error handling
    # --------------------------------------------------

    except HTTPException:
        raise

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail="Weather provider request timed out"
        )

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

    except ValueError:

        raise HTTPException(
            status_code=502,
            detail="Invalid response received from weather provider"
        )


    # --------------------------------------------------
    # Validate response structure
    # --------------------------------------------------

    try:

        weather_data = data["weather"][0]
        main_data = data["main"]
        location_data = data["sys"]

        rainfall_data = data.get("rain", {})

        rainfall_1h = rainfall_data.get("1h", 0)
        rainfall_3h = rainfall_data.get("3h", 0)

        rainfall_available = bool(rainfall_data)

        location_name = data["name"]
        country = location_data["country"]

        temperature = main_data["temp"]
        humidity = main_data["humidity"]
        pressure = main_data["pressure"]

        weather_description = weather_data["description"]

    except (KeyError, IndexError, TypeError):

        raise HTTPException(
            status_code=502,
            detail="Weather provider returned incomplete weather data"
        )


    # --------------------------------------------------
    # Response
    # --------------------------------------------------

    return {
        "success": True,

        "location": location_name,
        "country": country,

        "coordinates": {
            "latitude": data.get("coord", {}).get("lat"),
            "longitude": data.get("coord", {}).get("lon")
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
        )
    }
