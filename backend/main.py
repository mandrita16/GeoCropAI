
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# --------------------------------------------------
# Import backend modules after loading environment
# variables
# --------------------------------------------------

from backend.database import client, db
from backend.auth import router as auth_router
from backend.marketplace import router as marketplace_router
from backend.orders import router as orders_router
from backend.ml import router as ml_router
from backend.weather import router as weather_router


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="GeoCropAI API",
    description=(
        "GeoCropAI provides agricultural crop recommendations, "
        "fertilizer analysis, weather information, authentication, "
        "and an agricultural marketplace."
    ),
    version="1.0.0"
)


# --------------------------------------------------
# CORS configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# API routers
# --------------------------------------------------

app.include_router(auth_router)
app.include_router(marketplace_router)
app.include_router(orders_router)
app.include_router(ml_router)
app.include_router(weather_router)


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "GeoCropAI API is running",
        "status": "success",
        "version": "1.0.0"
    }


# --------------------------------------------------
# Health check endpoint
# --------------------------------------------------

@app.get("/health")
def health_check():

    try:
        client.admin.command("ping")

        return {
            "status": "healthy",
            "database": "MongoDB connected"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "MongoDB connection failed"
            }
        )
