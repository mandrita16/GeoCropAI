from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

from backend.database import products_collection, orders_collection
from backend.marketplace import get_current_user


router = APIRouter(
    prefix="/marketplace",
    tags=["Orders"]
)


# -----------------------------------
# Order Request
# -----------------------------------

class OrderCreate(BaseModel):
    product_id: str
    quantity: float = Field(..., gt=0)


# -----------------------------------
# BUYER: Place Order
# -----------------------------------

@router.post("/orders")
def create_order(
    order: OrderCreate,
    authorization: Optional[str] = Header(default=None)
):

    user = get_current_user(authorization)

    if user["role"] != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only buyers can place orders"
        )

    if not ObjectId.is_valid(order.product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID"
        )

    product = products_collection.find_one({
        "_id": ObjectId(order.product_id),
        "available": True
    })

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or unavailable"
        )

    if order.quantity > product["quantity"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {product['quantity']} {product['unit']} available"
        )

    total_price = order.quantity * product["price"]

    # Reduce available quantity
    new_quantity = product["quantity"] - order.quantity

    products_collection.update_one(
        {"_id": product["_id"]},
        {
            "$set": {
                "quantity": new_quantity,
                "available": new_quantity > 0
            }
        }
    )

    order_data = {
        "buyer_id": user["id"],
        "buyer_email": user["email"],
        "seller_id": product["seller_id"],
        "seller_email": product["seller_email"],
        "product_id": str(product["_id"]),
        "product_name": product["name"],
        "quantity": order.quantity,
        "unit": product["unit"],
        "price_per_unit": product["price"],
        "total_price": total_price,
        "status": "placed",
        "created_at": datetime.now(timezone.utc)
    }

    result = orders_collection.insert_one(order_data)

    return {
        "message": "Order placed successfully",
        "order_id": str(result.inserted_id),
        "total_price": total_price
    }


# -----------------------------------
# BUYER: My Orders
# -----------------------------------

@router.get("/my-orders")
def get_my_orders(
    authorization: Optional[str] = Header(default=None)
):

    user = get_current_user(authorization)

    if user["role"] != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only buyers can access their orders"
        )

    orders = list(
        orders_collection.find({
            "buyer_id": user["id"]
        }).sort(
            "created_at",
            -1
        )
    )

    result = []

    for order in orders:

        result.append({
            "id": str(order["_id"]),
            "product_id": order["product_id"],
            "product_name": order["product_name"],
            "seller_email": order["seller_email"],
            "quantity": order["quantity"],
            "unit": order["unit"],
            "price_per_unit": order["price_per_unit"],
            "total_price": order["total_price"],
            "status": order["status"],
            "created_at": order["created_at"]
        })

    return {
        "count": len(result),
        "orders": result
    }


# -----------------------------------
# FARMER: Orders Received
# -----------------------------------

@router.get("/seller-orders")
def get_seller_orders(
    authorization: Optional[str] = Header(default=None)
):

    user = get_current_user(authorization)

    if user["role"] != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only farmers can access seller orders"
        )

    orders = list(
        orders_collection.find({
            "seller_id": user["id"]
        }).sort(
            "created_at",
            -1
        )
    )

    result = []

    for order in orders:

        result.append({
            "id": str(order["_id"]),
            "product_id": order["product_id"],
            "product_name": order["product_name"],
            "buyer_email": order["buyer_email"],
            "quantity": order["quantity"],
            "unit": order["unit"],
            "total_price": order["total_price"],
            "status": order["status"],
            "created_at": order["created_at"]
        })

    return {
        "count": len(result),
        "orders": result
    }