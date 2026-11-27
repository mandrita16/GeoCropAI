
from pathlib import Path
from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

load_dotenv(ROOT_DIR / ".env")


# ============================================================
# IMPORT BACKEND MODULES
# ============================================================

from backend.database import (
    client,
    db,
    check_database_connection,
    initialize_database_indexes,
    close_database_connection,
)

from backend.auth import router as auth_router
from backend.marketplace import router as marketplace_router
from backend.orders import router as orders_router
from backend.ml import router as ml_router
from backend.weather import router as weather_router


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # --------------------------------------------------------
    # STARTUP
    # --------------------------------------------------------

    print("Starting GeoCropAI API...")

    # Verify MongoDB connection
    if not check_database_connection():

        print(
            "WARNING: MongoDB connection could not be established."
        )

    else:

        print(
            "MongoDB connection established successfully."
        )

        # Initialize database indexes
        indexes_initialized = initialize_database_indexes()

        if indexes_initialized:
            print("Database indexes initialized.")
        else:
            print("WARNING: Database index initialization failed.")

    yield

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    print("Shutting down GeoCropAI API...")

    close_database_connection()

    print("MongoDB connection closed.")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="GeoCropAI API",
    description=(
        "GeoCropAI provides agricultural crop recommendations, "
        "fertilizer analysis, weather information, authentication, "
        "and an agricultural marketplace."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

# Local development frontend origins
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Optional deployment configuration
frontend_origins_env = os.getenv(
    "FRONTEND_ORIGINS",
    "",
)

if frontend_origins_env.strip():

    frontend_origins = [
        origin.strip()
        for origin in frontend_origins_env.split(",")
        if origin.strip()
    ]

else:

    frontend_origins = default_origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTER REGISTRATION
# ============================================================

app.include_router(auth_router)
app.include_router(marketplace_router)
app.include_router(orders_router)
app.include_router(ml_router)
app.include_router(weather_router)

# Disease detection router intentionally excluded.


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "GeoCropAI API is running",
        "status": "success",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    database_connected = check_database_connection()

    if not database_connected:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "MongoDB connection failed",
            },
        )

    return {
        "status": "healthy",
        "database": "MongoDB connected",
        "database_name": db.name,
    }
