from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load root-level GeoCropAI-main/.env FIRST
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Import backend modules after loading environment variables
from backend.database import client, db
from backend.auth import router as auth_router
from backend.marketplace import router as marketplace_router
from backend.orders import router as orders_router
from backend.ml import router as ml_router
from backend.disease import router as disease_router
from backend.weather import router as weather_router
app = FastAPI(
    title="GeoCropAI API",
    description="Agriculture AI and Marketplace API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication routes
app.include_router(auth_router)
app.include_router(marketplace_router)
app.include_router(orders_router)
app.include_router(ml_router)
app.include_router(disease_router)
app.include_router(weather_router)

@app.get("/")
def root():
    return {
        "message": "GeoCropAI API is running",
        "status": "success"
    }


@app.get("/health")
def health_check():
    try:
        client.admin.command("ping")

        return {
            "status": "healthy",
            "database": "MongoDB connected"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "MongoDB connection failed",
            "error": str(e)
        }