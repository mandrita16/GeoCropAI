
import os
import math
import re
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional

import cloudinary
import cloudinary.uploader

from bson import ObjectId
from pymongo.errors import PyMongoError

from fastapi import (
    APIRouter,
    HTTPException,
    Header,
    status,
    UploadFile,
    File,
    Form,
    Query,
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

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

if not os.getenv("CLOUDINARY_URL"):
    raise ValueError("CLOUDINARY_URL is not set in the root .env file")


# ============================================================
# VALIDATION HELPERS
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


# ============================================================
# PRODUCT CREATE MODEL
# ============================================================

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
        return validate_non_empty_string(value, "Product name")

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
# PRODUCT UPDATE MODEL
# ============================================================

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)

    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[float] = Field(None, ge=0)

    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    location: Optional[str] = Field(None, min_length=1, max_length=200)

    @field_validator(
        "name",
        "category",
        "description",
        "unit",
        "location",
    )
    @classmethod
    def validate_text_fields(cls, value):
        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError("Field cannot be empty")

        return value

    @field_validator("price", "quantity")
    @classmethod
    def validate_numeric_fields(cls, value):
        if value is not None and not math.isfinite(value):
            raise ValueError("Value must be finite")

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
# CLOUDINARY CLEANUP
# ============================================================

def delete_cloudinary_image(public_id: Optional[str]):
    if not public_id:
        return

    try:
        cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
        )
    except Exception:
        # Cleanup failure should not hide the original error.
        pass


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

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid image",
        )


# ============================================================
# DATABASE PRODUCT CREATION
# ============================================================

def save_product(
    data: dict,
    image_public_id: Optional[str] = None,
):
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
        # Remove Cloudinary image if database insertion fails.
        delete_cloudinary_image(image_public_id)

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

    if len(name) < 2 or len(name) > 100:
        raise HTTPException(
            status_code=422,
            detail="Product name must contain 2-100 characters",
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

    validate_finite_positive_number(price, "Price")
    validate_finite_positive_number(quantity, "Quantity")

    # Read at most 5 MB + 1 byte.
    image_bytes = await image.read(MAX_IMAGE_SIZE + 1)
    await image.close()

    detected_content_type = validate_image(image_bytes)

    # Verify reported MIME type against actual file content.
    if (
        image.content_type
        and image.content_type != detected_content_type
        and image.content_type != "application/octet-stream"
    ):
        raise HTTPException(
            status_code=400,
            detail="Image file type does not match its content",
        )

    # Upload to Cloudinary
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
        # Clean up if Cloudinary gave us a public ID but
        # the response was otherwise incomplete.
        delete_cloudinary_image(image_public_id)

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

    # Email is private and only included in the farmer's
    # own listings response.
    if include_seller_email:
        result["seller_email"] = product.get("seller_email", "")

    return result


# ============================================================
# GET PRODUCTS - PAGINATION, SEARCH AND FILTERS
# ============================================================

@router.get("/products")
def get_products(
    page: int = Query(
        default=1,
        ge=1,
        description="Page number",
    ),
    limit: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Number of products per page",
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Search name, category, or description",
    ),
    category: Optional[str] = Query(
        default=None,
        max_length=50,
        description="Filter by category",
    ),
    location: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Filter by location",
    ),
    min_price: Optional[float] = Query(
        default=None,
        ge=0,
        description="Minimum price",
    ),
    max_price: Optional[float] = Query(
        default=None,
        ge=0,
        description="Maximum price",
    ),
):
    # Validate price range.
    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise HTTPException(
            status_code=422,
            detail="min_price cannot be greater than max_price",
        )

    query = {
        "available": True,
    }

    # Search product name, category, and description.
    if search and search.strip():
        search_pattern = re.escape(search.strip())

        query["$or"] = [
            {
                "name": {
                    "$regex": search_pattern,
                    "$options": "i",
                }
            },
            {
                "category": {
                    "$regex": search_pattern,
                    "$options": "i",
                }
            },
            {
                "description": {
                    "$regex": search_pattern,
                    "$options": "i",
                }
            },
        ]

    # Category filter.
    if category and category.strip():
        query["category"] = {
            "$regex": re.escape(category.strip()),
            "$options": "i",
        }

    # Location filter.
    if location and location.strip():
        query["location"] = {
            "$regex": re.escape(location.strip()),
            "$options": "i",
        }

    # Price range filters.
    if min_price is not None or max_price is not None:
        query["price"] = {}

        if min_price is not None:
            query["price"]["$gte"] = min_price

        if max_price is not None:
            query["price"]["$lte"] = max_price

    try:
        total_products = products_collection.count_documents(query)

        total_pages = (
            math.ceil(total_products / limit)
            if total_products > 0
            else 0
        )

        skip = (page - 1) * limit

        products = list(
            products_collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        serialized_products = [
            serialize_product(product)
            for product in products
        ]

        return {
            "count": len(serialized_products),
            "total_products": total_products,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "filters": {
                "search": search,
                "category": category,
                "location": location,
                "min_price": min_price,
                "max_price": max_price,
            },
            "products": serialized_products,
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
            {
                "_id": ObjectId(product_id),
            }
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
                {
                    "seller_id": user["id"],
                }
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


# ============================================================
# UPDATE PRODUCT
# ============================================================

@router.put("/products/{product_id}")
def update_product(
    product_id: str,
    product_data: ProductUpdate,
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(authorization)

    require_farmer(user)

    # Validate product ID.
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid product ID",
        )

    # Only fields explicitly provided by the client
    # should be updated.
    update_data = product_data.model_dump(
        exclude_unset=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    try:
        existing_product = products_collection.find_one(
            {
                "_id": ObjectId(product_id),
            }
        )

        if not existing_product:
            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        # Ownership check.
        if existing_product.get("seller_id") != user["id"]:
            raise HTTPException(
                status_code=403,
                detail="You can only update your own products",
            )

        update_data["updated_at"] = datetime.now(timezone.utc)

        products_collection.update_one(
            {
                "_id": ObjectId(product_id),
            },
            {
                "$set": update_data,
            },
        )

        updated_product = products_collection.find_one(
            {
                "_id": ObjectId(product_id),
            }
        )

        return {
            "message": "Product updated successfully",
            "product": serialize_product(
                updated_product,
                include_seller_email=True,
            ),
        }

    except PyMongoError:
        raise HTTPException(
            status_code=503,
            detail="Unable to update product at this time",
        )
