
import os
from datetime import datetime, timezone
from typing import Optional

import cloudinary
import cloudinary.uploader
from bson import ObjectId
from fastapi import (
    APIRouter, HTTPException, Header, status,
    UploadFile, File, Form
)
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from backend.database import products_collection

router = APIRouter(
    prefix="/marketplace",
    tags=["Agriculture Marketplace"]
)

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET is not set in the .env file")

ALGORITHM = "HS256"

# Cloudinary reads CLOUDINARY_URL from the environment.
if not os.getenv("CLOUDINARY_URL"):
    raise ValueError("CLOUDINARY_URL is not set in the root .env file")


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2)
    category: str
    description: Optional[str] = ""
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    unit: str = "kg"
    location: str
    image_url: Optional[str] = ""


def get_current_user(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="A valid Bearer token is required"
        )

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")

        if not user_id or not email or not role:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"id": user_id, "email": email, "role": role}

    except JWTError:
        raise HTTPException(
            status_code=401, detail="Invalid or expired token"
        )


def save_product(data: dict):
    data["created_at"] = datetime.now(timezone.utc)
    data["available"] = True

    result = products_collection.insert_one(data)
    return {
        "message": "Product listed successfully",
        "product_id": str(result.inserted_id),
        "image_url": data.get("image_url", "")
    }


# Existing JSON listing endpoint (kept for compatibility)
@router.post("/products")
def create_product(
    product: ProductCreate,
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(authorization)

    if user["role"] != "farmer":
        raise HTTPException(
            status_code=403,
            detail="Only farmers can list products"
        )

    data = product.model_dump()
    data.update({
        "seller_id": user["id"],
        "seller_email": user["email"]
    })
    return save_product(data)


# New image-upload endpoint
@router.post("/products/upload")
async def create_product_with_image(
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    price: float = Form(..., gt=0),
    quantity: float = Form(..., gt=0),
    unit: str = Form("kg"),
    location: str = Form(...),
    image: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(authorization)

    if user["role"] != "farmer":
        raise HTTPException(
            status_code=403,
            detail="Only farmers can list products"
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, PNG, or WEBP image"
        )

    image_bytes = await image.read()
    await image.close()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image is empty")

    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image must be 5 MB or smaller"
        )

    try:
        uploaded = cloudinary.uploader.upload(
            image_bytes,
            folder="geocropai/products",
            resource_type="image"
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Image upload failed. Check Cloudinary credentials."
        )

    data = {
        "name": name.strip(),
        "category": category.strip(),
        "description": description.strip(),
        "price": price,
        "quantity": quantity,
        "unit": unit,
        "location": location.strip(),
        "image_url": uploaded["secure_url"],
        "image_public_id": uploaded["public_id"],
        "seller_id": user["id"],
        "seller_email": user["email"]
    }

    return save_product(data)


def serialize_product(product: dict, include_seller=True):
    result = {
        "id": str(product["_id"]),
        "name": product["name"],
        "category": product["category"],
        "description": product.get("description", ""),
        "price": product["price"],
        "quantity": product["quantity"],
        "unit": product.get("unit", "kg"),
        "location": product["location"],
        "image_url": product.get("image_url", ""),
        "available": product.get("available", True),
        "created_at": product["created_at"]
    }

    if include_seller:
        result["seller_id"] = product.get("seller_id", "")
        result["seller_email"] = product.get("seller_email", "")

    return result


@router.get("/products")
def get_products():
    products = list(
        products_collection.find({"available": True}).sort(
            "created_at", -1
        )
    )
    return {
        "count": len(products),
        "products": [serialize_product(p) for p in products]
    }


@router.get("/products/{product_id}")
def get_product(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = products_collection.find_one(
        {"_id": ObjectId(product_id)}
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return serialize_product(product)


@router.get("/my-listings")
def get_my_listings(
    authorization: Optional[str] = Header(default=None)
):
    user = get_current_user(authorization)

    if user["role"] != "farmer":
        raise HTTPException(
            status_code=403,
            detail="Only farmers can access their listings"
        )

    products = list(
        products_collection.find(
            {"seller_id": user["id"]}
        ).sort("created_at", -1)
    )

    return {
        "count": len(products),
        "products": [
            serialize_product(p, include_seller=False)
            for p in products
        ]
    }
