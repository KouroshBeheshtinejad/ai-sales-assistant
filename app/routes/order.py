from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.routes.auth import get_current_user, get_optional_user
from app.services.order_service import OrderService
from app.services.invoice_service import render_invoice_pdf
from app.services.chat_rate_limit import enforce_tracking_rate_limit


router = APIRouter(prefix="/orders", tags=["Orders"])


class CreateOrderRequest(BaseModel):
    customer_name: str | None = Field(None, min_length=1, max_length=255)
    first_name: str | None = Field(None, min_length=1, max_length=120)
    last_name: str | None = Field(None, min_length=1, max_length=120)
    email: str | None = Field(None, max_length=255)
    customer_phone: str = Field(..., min_length=1, max_length=50)
    customer_address: str = Field(..., min_length=1, max_length=500)

    @model_validator(mode="after")
    def require_compatible_name(self):
        if not self.customer_name and not (self.first_name and self.last_name):
            raise ValueError("Provide customer_name or first_name and last_name")
        if not self.customer_name:
            self.customer_name = f"{self.first_name} {self.last_name}"
        return self


def order_response(order):
    return {
        "id": order.id,
        "tracking_number": order.tracking_number,
            "invoice_number": order.invoice_number,
        "user_id": order.user_id,
        "store_id": order.store_id,
        "status": order.status,
        "customer_name": order.customer_name,
        "first_name": order.customer_first_name,
        "last_name": order.customer_last_name,
        "email": order.customer_email,
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


@router.get("/track/{tracking_number}")
def track_order(
    tracking_number: str,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_tracking_rate_limit(request)
    order = OrderService.get_order_by_tracking_number(db, tracking_number)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {
        "tracking_number": order.tracking_number,
        "store_id": order.store_id,
        "store_name": order.store.name,
        "status": order.status,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "cancelled_at": order.cancelled_at,
    }


@router.post(
    "/stores/{store_id}",
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    store_id: int,
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if current_user is None and (not guest_token or not idempotency_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest token and idempotency key are required",
        )
    try:
        order = OrderService.create_order(
            db=db,
            user_id=current_user.id if current_user else None,
            store_id=store_id,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            customer_address=payload.customer_address,
            customer_first_name=payload.first_name,
            customer_last_name=payload.last_name,
            customer_email=payload.email,
            guest_token=None if current_user else guest_token,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return order_response(order)


@router.get("/{order_id}/invoice")
def download_user_invoice(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = OrderService.get_order_by_id(db, order_id, current_user.id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return Response(
        content=render_invoice_pdf(order),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{order.invoice_number}.pdf"'},
    )


@router.get("/stores/{store_id}/guest/{order_id}")
def get_guest_order(
    store_id: int,
    order_id: int,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    db: Session = Depends(get_db),
):
    if not guest_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest token is required")
    order = OrderService.get_guest_order(
        db=db,
        order_id=order_id,
        store_id=store_id,
        guest_token=guest_token,
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order_response(order)


@router.get("/stores/{store_id}/guest/{order_id}/invoice")
def download_guest_invoice(
    store_id: int,
    order_id: int,
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    db: Session = Depends(get_db),
):
    if not guest_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest token is required")
    order = OrderService.get_guest_order(db, order_id, store_id, guest_token)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return Response(
        content=render_invoice_pdf(order),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{order.invoice_number}.pdf"'},
    )


@router.get("")
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orders = OrderService.list_user_orders(
        db=db,
        user_id=current_user.id,
    )
    return [order_response(order) for order in orders]


@router.get("/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = OrderService.get_order_by_id(
        db=db,
        order_id=order_id,
        user_id=current_user.id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order_response(order)


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = OrderService.cancel_order(
            db=db,
            order_id=order_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        if str(exc) == "Order not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return order_response(order)