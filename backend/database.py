
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


# --------------------------------------------------
# Load environment variables from project root
# --------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError(
        "MONGO_URI is missing. "
        "Please configure it in the project root .env file."
    )


# --------------------------------------------------
# MongoDB client configuration
# --------------------------------------------------

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    maxPoolSize=50,
)


# --------------------------------------------------
# Database
# --------------------------------------------------

db = client["geocropai"]


# --------------------------------------------------
# Collections
# --------------------------------------------------

users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]


# --------------------------------------------------
# Database connection utility
# --------------------------------------------------

def check_database_connection():
    """
    Checks whether MongoDB is reachable.

    Returns:
        True: MongoDB is reachable.
        False: MongoDB connection failed.
    """

    try:
        client.admin.command("ping")
        return True

    except PyMongoError:
        return False
