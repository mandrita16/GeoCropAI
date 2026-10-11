
import os

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/weather", tags=["Weather"])

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


@router.get("")
async def get_weather(
    city: str = Query(..., min_length=2, description="City name, e.g. Kolkata")
):
    # Read the key when the request arrives
    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENWEATHER_API_KEY not found. Check GeoCropAI-main/.env",
        )

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPENWEATHER_URL, params=params)

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="City not found")

        if response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="Weather API key is invalid or not activated yet",
            )

        response.raise_for_status()
        data = response.json()

        return {
            "success": True,
            "location": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather": data["weather"][0]["description"],
            "rainfall_last_hour_mm": data.get("rain", {}).get("1h", 0),
            "rainfall_last_3_hours_mm": data.get("rain", {}).get("3h", 0),
        }

    except HTTPException:
        raise
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502, detail="Weather provider returned an error"
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503, detail="Could not connect to the weather provider"
        )
