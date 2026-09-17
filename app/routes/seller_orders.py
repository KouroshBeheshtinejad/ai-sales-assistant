from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.routes.auth import get_current_user
from app.services.seller_order_service import SellerOrderService


router = APIRouter(
    prefix="/seller/orders",
    tags=["Seller Orders"],
)


class UpdateOrderStatusRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=20)


def seller_order_response(order):
    return {
        "id": order.id,
        "user_id": order.user_id,
        "store_id": order.store_id,
        "status": order.status,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "customer_address": order.customer_address,
        "total_amount": str(order.total_amount),
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "cancelled_at": order.cancelled_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "unit_price": str(item.unit_price),
                "quantity": item.quantity,
                "line_total": str(item.line_total),
            }
            for item in order.items
        ],
    }


@router.get("/stores/{store_id}")
def list_store_orders(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        orders = SellerOrderService.list_store_orders(
            db=db,
            seller_id=current_user.id,
            store_id=store_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return [seller_order_response(order) for order in orders]


@router.get("/{order_id}")
def get_seller_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = SellerOrderService.get_order(
            db=db,
            seller_id=current_user.id,
            order_id=order_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return seller_order_response(order)


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = SellerOrderService.update_status(
            db=db,
            seller_id=current_user.id,
            order_id=order_id,
            new_status=payload.status,
        )
    except ValueError as exc:
        error_message = str(exc)

        if error_message == "Order not found":
            error_status = status.HTTP_404_NOT_FOUND
        else:
            error_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=error_status,
            detail=error_message,
        ) from exc

    return seller_order_response(order)