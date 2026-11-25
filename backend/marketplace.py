
import os
import math
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional

import cloudinary
import cloudinary.uploader
from bson import ObjectId
from pymongo.errors import PyMongoError, DuplicateKeyError
from fastapi import (
    APIRouter,
    HTTPException,
    Header,
    status,
    UploadFile,
    File,
    Form,
)
from jose import JWTError, jwt
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator

from backend.database import products_collection


# ============================================================
# ROUTER CONFIGURATION
# ============================================================

router = APIRouter(
    prefix="/marketplace",
    tags=["Agriculture Marketplace"],
)


# ============================================================
# CONFIGURATION
# ============================================================

SECRET_KEY = os.getenv("JWT_SECRET")

if not SECRET_KEY:
    raise ValueError("JWT_SECRET is not set in the .env file")

ALGORITHM = "HS256"

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

if not os.getenv("CLOUDINARY_URL"):
    raise ValueError("CLOUDINARY_URL is not set in the root .env file")


# ============================================================
# PRODUCT VALIDATION
# ============================================================

def validate_non_empty_string(value: str, field_name: str):
    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    return value


def validate_finite_positive_number(value: float, field_name: str):
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite number")

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")

    return value


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default="", max_length=1000)
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    unit: str = Field(default="kg", min_length=1, max_length=20)
    location: str = Field(..., min_length=1, max_length=200)
    image_url: Optional[str] = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        value = validate_non_empty_string(value, "Product name")

        if len(value) < 2:
            raise ValueError("Product name must contain at least 2 characters")

        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value):
        return validate_non_empty_string(value, "Category")

    @field_validator("location")
    @classmethod
    def validate_location(cls, value):
        return validate_non_empty_string(value, "Location")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value):
        return validate_non_empty_string(value, "Unit")

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        return value.strip() if value else ""

    @field_validator("price", "quantity")
    @classmethod
    def validate_numbers(cls, value):
        if not math.isfinite(value):
            raise ValueError("Value must be a finite number")

        if value <= 0:
            raise ValueError("Value must be greater than zero")

        return value


# ============================================================
# AUTHENTICATION
# ============================================================

def get_current_user(authorization: Optional[str]):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="A valid Bearer token is required",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="A valid Bearer token is required",
        )

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="A valid Bearer token is required",
        )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")

        if not user_id or not email or not role:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )

        if role not in {"farmer", "buyer"}:
            raise HTTPException(
                status_code=401,
                detail="Invalid user role in token",
            )

        return {
            "id": user_id,
            "email": email,
            "role": role,
        }

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )


def require_farmer(user: dict):
    if user["role"] != "farmer":
        raise HTTPException(
            status_code=403,
            detail="Only farmers can perform this action",
        )


# ============================================================
# IMAGE VALIDATION
# ============================================================

def validate_image(image_bytes: bytes):
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Image is empty",
        )

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image must be 5 MB or smaller",
        )

    try:
        image = Image.open(BytesIO(image_bytes))

        image_format = image.format

        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=400,
                detail="Upload a valid JPG, PNG, or WEBP image",
            )

        image.verify()

        return ALLOWED_IMAGE_FORMATS[image_format]

    except HTTPException:
        raise

    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid image",
        )


# ============================================================
# DATABASE PRODUCT CREATION
# ============================================================

def save_product(data: dict, image_public_id: Optional[str] = None):
    data["created_at"] = datetime.now(timezone.utc)
    data["available"] = True

    try:
        result = products_collection.insert_one(data)

        return {
            "message": "Product listed successfully",
            "product_id": str(result.inserted_id),
            "image_url": data.get("image_url", ""),
        }

    except PyMongoError:
        # If DB insertion fails after Cloudinary upload,
        # attempt to remove the uploaded image.
        if image_public_id:
            try:
                cloudinary.uploader.destroy(image_public_id)
            except Exception:
                pass

        raise HTTPException(
            status_code=503,
            detail="Unable to save product. Please try again later.",
        )


# ============================================================
# CREATE PRODUCT - JSON ENDPOINT
# ============================================================

@router.post(
    "/products",
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product: ProductCreate,
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(authorization)

    require_farmer(user)

    data = product.model_dump()

    data.update({
        "seller_id": user["id"],
        "seller_email": user["email"],
    })

    return save_product(data)


# ============================================================
# CREATE PRODUCT - IMAGE UPLOAD ENDPOINT
# ============================================================

@router.post(
    "/products/upload",
    status_code=status.HTTP_201_CREATED,
)
async def create_product_with_image(
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    price: float = Form(..., gt=0),
    quantity: float = Form(..., gt=0),
    unit: str = Form("kg"),
    location: str = Form(...),
    image: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(authorization)

    require_farmer(user)

    # Validate textual fields
    name = validate_non_empty_string(name, "Product name")
    category = validate_non_empty_string(category, "Category")
    location = validate_non_empty_string(location, "Location")
    unit = validate_non_empty_string(unit, "Unit")
    description = description.strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Product name must contain at least 2 characters",
        )

    if len(name) > 100:
        raise HTTPException(
            status_code=422,
            detail="Product name cannot exceed 100 characters",
        )

    if len(category) > 50:
        raise HTTPException(
            status_code=422,
            detail="Category cannot exceed 50 characters",
        )

    if len(location) > 200:
        raise HTTPException(
            status_code=422,
            detail="Location cannot exceed 200 characters",
        )

    if len(unit) > 20:
        raise HTTPException(
            status_code=422,
            detail="Unit cannot exceed 20 characters",
        )

    if len(description) > 1000:
        raise HTTPException(
            status_code=422,
            detail="Description cannot exceed 1000 characters",
        )

    # Validate numeric values
    validate_finite_positive_number(price, "Price")
    validate_finite_positive_number(quantity, "Quantity")

    # Read no more than 5 MB + 1 byte to detect oversized files.
    image_bytes = await image.read(MAX_IMAGE_SIZE + 1)
    await image.close()

    # Validate actual file content, not just client MIME type.
    detected_content_type = validate_image(image_bytes)

    # Optional: reject mismatch between reported MIME and actual content.
    if (
        image.content_type
        and image.content_type != detected_content_type
    ):
        raise HTTPException(
            status_code=400,
            detail="Image file type does not match its content",
        )

    # Upload image to Cloudinary
    try:
        uploaded = cloudinary.uploader.upload(
            image_bytes,
            folder="geocropai/products",
            resource_type="image",
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Image upload failed. Check Cloudinary credentials.",
        )

    image_url = uploaded.get("secure_url")
    image_public_id = uploaded.get("public_id")

    if not image_url or not image_public_id:
        raise HTTPException(
            status_code=502,
            detail="Cloudinary returned an invalid upload response",
        )

    data = {
        "name": name,
        "category": category,
        "description": description,
        "price": price,
        "quantity": quantity,
        "unit": unit,
        "location": location,
        "image_url": image_url,
        "image_public_id": image_public_id,
        "seller_id": user["id"],
        "seller_email": user["email"],
    }

    return save_product(
        data,
        image_public_id=image_public_id,
    )


# ============================================================
# PRODUCT SERIALIZATION
# ============================================================

def serialize_product(
    product: dict,
    include_seller_email: bool = False,
):
    result = {
        "id": str(product["_id"]),
        "name": product.get("name", ""),
        "category": product.get("category", ""),
        "description": product.get("description", ""),
        "price": product.get("price", 0),
        "quantity": product.get("quantity", 0),
        "unit": product.get("unit", "kg"),
        "location": product.get("location", ""),
        "image_url": product.get("image_url", ""),
        "available": product.get("available", True),
        "created_at": product.get("created_at"),
        "seller_id": product.get("seller_id", ""),
    }

    # Seller email is included only for the seller's own listings.
    if include_seller_email:
        result["seller_email"] = product.get("seller_email", "")

    return result


# ============================================================
# GET ALL AVAILABLE PRODUCTS
# ============================================================

@router.get("/products")
def get_products():
    try:
        products = list(
            products_collection.find(
                {"available": True}
            ).sort(
                "created_at",
                -1,
            )
        )

        return {
            "count": len(products),
            "products": [
                serialize_product(product)
                for product in products
            ],
        }

    except PyMongoError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve products at this time",
        )


# ============================================================
# GET PRODUCT BY ID
# ============================================================

@router.get("/products/{product_id}")
def get_product(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID",
        )

    try:
        product = products_collection.find_one(
            {"_id": ObjectId(product_id)}
        )

    except PyMongoError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve product at this time",
        )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return serialize_product(product)


# ============================================================
# GET FARMER'S OWN LISTINGS
# ============================================================

@router.get("/my-listings")
def get_my_listings(
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(authorization)

    require_farmer(user)

    try:
        products = list(
            products_collection.find(
                {"seller_id": user["id"]}
            ).sort(
                "created_at",
                -1,
            )
        )

        return {
            "count": len(products),
            "products": [
                serialize_product(
                    product,
                    include_seller_email=True,
                )
                for product in products
            ],
        }

    except PyMongoError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve your listings at this time",
        )
