
from datetime import datetime, timezone
from typing import Optional
import math

from bson import ObjectId
from pymongo.errors import PyMongoError

from fastapi import (
    APIRouter,
    HTTPException,
    Header,
    status,
)

from pydantic import BaseModel, Field, field_validator

from backend.database import products_collection, orders_collection
from backend.marketplace import get_current_user


# ============================================================
# ROUTER CONFIGURATION
# ============================================================

router = APIRouter(
    prefix="/marketplace",
    tags=["Orders"],
)


# ============================================================
# ORDER REQUEST MODEL
# ============================================================

class OrderCreate(BaseModel):
    product_id: str
    quantity: float = Field(..., gt=0)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value):
        if not math.isfinite(value):
            raise ValueError("Quantity must be a finite number")

        if value <= 0:
            raise ValueError("Quantity must be greater than zero")

        return value


# ============================================================
# ORDER SERIALIZATION
# ============================================================

def serialize_order(
    order: dict,
    include_buyer_email: bool = False,
    include_seller_email: bool = False,
):
    result = {
        "id": str(order["_id"]),
        "product_id": order.get("product_id", ""),
        "product_name": order.get("product_name", ""),
        "quantity": order.get("quantity", 0),
        "unit": order.get("unit", "kg"),
        "price_per_unit": order.get("price_per_unit", 0),
        "total_price": order.get("total_price", 0),
        "status": order.get("status", "placed"),
        "created_at": order.get("created_at"),
    }

    if include_buyer_email:
        result["buyer_email"] = order.get("buyer_email", "")

    if include_seller_email:
        result["seller_email"] = order.get("seller_email", "")

    return result


# ============================================================
# BUYER: PLACE ORDER
# ============================================================

@router.post(
    "/orders",
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order: OrderCreate,
    authorization: Optional[str] = Header(default=None),
):
    # --------------------------------------------------------
    # 1. Authentication
    # --------------------------------------------------------

    user = get_current_user(authorization)

    if user["role"] != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only buyers can place orders",
        )

    # --------------------------------------------------------
    # 2. Validate Product ID
    # --------------------------------------------------------

    if not ObjectId.is_valid(order.product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID",
        )

    product_id = ObjectId(order.product_id)

    # --------------------------------------------------------
    # 3. Find Product
    # --------------------------------------------------------

    try:
        product = products_collection.find_one({
            "_id": product_id,
            "available": True,
        })

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve product",
        )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or unavailable",
        )

    # --------------------------------------------------------
    # 4. Validate Quantity
    # --------------------------------------------------------

    requested_quantity = order.quantity

    available_quantity = product.get("quantity", 0)

    if requested_quantity > available_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {available_quantity} {product.get('unit', 'kg')} available",
        )

    # --------------------------------------------------------
    # 5. Calculate Price
    # --------------------------------------------------------

    unit_price = product["price"]

    total_price = round(
        requested_quantity * unit_price,
        2,
    )

    # --------------------------------------------------------
    # 6. ATOMIC STOCK DEDUCTION
    # --------------------------------------------------------

    # MongoDB performs this operation atomically.
    #
    # The stock will only be deducted if:
    # - The product still exists
    # - It is still available
    # - Enough quantity remains
    #
    # This prevents two buyers from purchasing the same
    # remaining stock simultaneously.

    try:
        stock_result = products_collection.update_one(
            {
                "_id": product_id,
                "available": True,
                "quantity": {
                    "$gte": requested_quantity,
                },
            },
            {
                "$inc": {
                    "quantity": -requested_quantity,
                },
            },
        )

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reserve product stock",
        )

    if stock_result.modified_count == 0:
        # Stock may have changed between the initial
        # read and atomic update.
        latest_product = products_collection.find_one({
            "_id": product_id,
        })

        if not latest_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product no longer exists",
            )

        latest_quantity = latest_product.get("quantity", 0)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock changed. Only {latest_quantity} {latest_product.get('unit', 'kg')} available",
        )

    # --------------------------------------------------------
    # 7. Update Product Availability
    # --------------------------------------------------------

    try:
        updated_product = products_collection.find_one({
            "_id": product_id,
        })

        if updated_product and updated_product.get("quantity", 0) <= 0:
            products_collection.update_one(
                {
                    "_id": product_id,
                },
                {
                    "$set": {
                        "available": False,
                    },
                },
            )

    except PyMongoError:
        # Stock has already been deducted.
        # The order will still proceed.
        pass

    # --------------------------------------------------------
    # 8. Create Order Document
    # --------------------------------------------------------

    order_data = {
        "buyer_id": user["id"],
        "buyer_email": user["email"],

        "seller_id": product["seller_id"],
        "seller_email": product.get("seller_email", ""),

        "product_id": str(product["_id"]),
        "product_name": product["name"],

        "quantity": requested_quantity,
        "unit": product.get("unit", "kg"),

        # Price snapshot.
        # Future product price changes will not affect
        # this existing order.
        "price_per_unit": unit_price,
        "total_price": total_price,

        "status": "placed",

        "created_at": datetime.now(timezone.utc),
    }

    # --------------------------------------------------------
    # 9. Insert Order
    # --------------------------------------------------------

    try:
        result = orders_collection.insert_one(order_data)

    except PyMongoError:
        # If order insertion fails, restore the stock.
        # This is a compensating action.
        try:
            products_collection.update_one(
                {
                    "_id": product_id,
                },
                {
                    "$inc": {
                        "quantity": requested_quantity,
                    },
                    "$set": {
                        "available": True,
                    },
                },
            )

        except PyMongoError:
            # If compensation also fails, manual recovery
            # may be required. This is why a DB transaction
            # is the ideal long-term solution.
            pass

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order could not be created. Please try again.",
        )

    # --------------------------------------------------------
    # 10. Response
    # --------------------------------------------------------

    return {
        "message": "Order placed successfully",
        "order_id": str(result.inserted_id),
        "status": "placed",
        "product_name": product["name"],
        "quantity": requested_quantity,
        "unit": product.get("unit", "kg"),
        "price_per_unit": unit_price,
        "total_price": total_price,
    }


# ============================================================
# BUYER: MY ORDERS
# ============================================================

@router.get("/my-orders")
def get_my_orders(
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(authorization)

    if user["role"] != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only buyers can access their orders",
        )

    try:
        orders = list(
            orders_collection.find({
                "buyer_id": user["id"],
            }).sort(
                "created_at",
                -1,
            )
        )

        result = [
            serialize_order(
                order,
                include_seller_email=True,
            )
            for order in orders
        ]

        return {
            "count": len(result),
            "orders": result,
        }

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve your orders",
        )


# ============================================================
# FARMER: ORDERS RECEIVED
# ============================================================

@router.get("/seller-orders")
def get_seller_orders(
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(authorization)

    if user["role"] != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only farmers can access seller orders",
        )

    try:
        orders = list(
            orders_collection.find({
                "seller_id": user["id"],
            }).sort(
                "created_at",
                -1,
            )
        )

        result = [
            serialize_order(
                order,
                include_buyer_email=True,
            )
            for order in orders
        ]

        return {
            "count": len(result),
            "orders": result,
        }

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve seller orders",
        )


# ============================================================
# GET ORDER BY ID
# ============================================================

@router.get("/orders/{order_id}")
def get_order(
    order_id: str,
    authorization: Optional[str] = Header(default=None),
):
    user = get_current_user(authorization)

    if not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID",
        )

    try:
        order = orders_collection.find_one({
            "_id": ObjectId(order_id),
        })

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve order",
        )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Only the buyer or seller associated with the order
    # can view it.
    if (
        order.get("buyer_id") != user["id"]
        and order.get("seller_id") != user["id"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this order",
        )

    if user["role"] == "buyer":
        return serialize_order(
            order,
            include_seller_email=True,
        )

    return serialize_order(
        order,
        include_buyer_email=True,
    )
