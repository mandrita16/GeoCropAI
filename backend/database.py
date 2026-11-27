
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI is missing. "
        "Please configure it in the project root .env file."
    )


# ============================================================
# MONGODB CLIENT
# ============================================================

client = MongoClient(
    MONGO_URI,

    # Connection timeout
    serverSelectionTimeoutMS=5000,

    # Initial connection timeout
    connectTimeoutMS=5000,

    # Socket timeout
    socketTimeoutMS=10000,

    # Connection pooling
    maxPoolSize=50,
    minPoolSize=0,

    # Idle connections
    maxIdleTimeMS=60000,

    # Retry certain operations automatically
    retryWrites=True,
)


# ============================================================
# DATABASE
# ============================================================

db = client["geocropai"]


# ============================================================
# COLLECTIONS
# ============================================================

users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]


# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

def check_database_connection() -> bool:
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


def get_database_status() -> dict:
    """
    Returns detailed database health information.
    Useful for the /health endpoint.
    """

    try:
        client.admin.command("ping")

        return {
            "status": "connected",
            "database": db.name,
        }

    except PyMongoError as error:

        return {
            "status": "disconnected",
            "database": db.name,
            "error": str(error),
        }


# ============================================================
# DATABASE INDEXES
# ============================================================

def initialize_database_indexes():
    """
    Creates indexes used by GeoCropAI.

    Run this during application startup.

    Important:
    Unique indexes prevent duplicate accounts even when
    multiple signup requests happen simultaneously.
    """

    try:

        # ----------------------------------------------------
        # USERS
        # ----------------------------------------------------

        users_collection.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="unique_email",
        )

        users_collection.create_index(
            [("username", ASCENDING)],
            unique=True,
            name="unique_username",
        )

        # ----------------------------------------------------
        # PRODUCTS
        # ----------------------------------------------------

        products_collection.create_index(
            [("seller_id", ASCENDING)],
            name="seller_products",
        )

        products_collection.create_index(
            [
                ("available", ASCENDING),
                ("category", ASCENDING),
            ],
            name="available_products_by_category",
        )

        products_collection.create_index(
            [("created_at", DESCENDING)],
            name="products_newest_first",
        )

        products_collection.create_index(
            [("price", ASCENDING)],
            name="products_by_price",
        )

        # ----------------------------------------------------
        # ORDERS
        # ----------------------------------------------------

        orders_collection.create_index(
            [
                ("buyer_id", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="buyer_orders_newest_first",
        )

        orders_collection.create_index(
            [
                ("seller_id", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="seller_orders_newest_first",
        )

        orders_collection.create_index(
            [("product_id", ASCENDING)],
            name="orders_by_product",
        )

        print("MongoDB indexes initialized successfully.")

        return True

    except PyMongoError as error:

        print(
            f"MongoDB index initialization failed: {error}"
        )

        return False


# ============================================================
# DATABASE SHUTDOWN
# ============================================================

def close_database_connection():
    """
    Closes the MongoDB client connection pool.
    """

    client.close()
