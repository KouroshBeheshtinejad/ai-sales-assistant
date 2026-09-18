from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.routes.auth import get_optional_user
from app.services.cart_service import CartService, MAX_CART_QUANTITY


router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
)


class AddCartItemRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=MAX_CART_QUANTITY)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., gt=0, le=MAX_CART_QUANTITY)


def _cart_response(cart):
    items = []

    for item in cart.items:
        if item.product is None:
            continue

        unit_price = Decimal(str(item.product.price))
        line_total = unit_price * item.quantity

        items.append(
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "unit_price": unit_price,
                "quantity": item.quantity,
                "line_total": line_total,
            }
        )

    total = CartService.calculate_total(cart)

    return {
        "cart_id": cart.id,
        "user_id": cart.user_id,
        "guest_token": cart.guest_token,
        "store_id": cart.store_id,
        "items": items,
        "total_amount": total,
    }


@router.get("/stores/{store_id}")
def get_cart(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
):
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        cart = CartService.get_or_create_cart(
            db=db,
            user_id=current_user.id if current_user else None,
            store_id=store_id,
            guest_token=None if current_user else guest_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _cart_response(cart)


@router.post("/stores/{store_id}/items")
def add_cart_item(
    store_id: int,
    data: AddCartItemRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
):
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        cart = CartService.add_item(
            db=db,
            user_id=current_user.id if current_user else None,
            store_id=store_id,
            product_id=data.product_id,
            quantity=data.quantity,
            guest_token=None if current_user else guest_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _cart_response(cart)


@router.patch("/stores/{store_id}/items/{product_id}")
def update_cart_item(
    store_id: int,
    product_id: int,
    data: UpdateCartItemRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
):
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        cart = CartService.update_item(
            db=db,
            user_id=current_user.id if current_user else None,
            store_id=store_id,
            product_id=product_id,
            quantity=data.quantity,
            guest_token=None if current_user else guest_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _cart_response(cart)


@router.delete("/stores/{store_id}/items/{product_id}")
def remove_cart_item(
    store_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
):
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        cart = CartService.remove_item(
            db=db,
            user_id=current_user.id if current_user else None,
            store_id=store_id,
            product_id=product_id,
            guest_token=None if current_user else guest_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _cart_response(cart)


@router.delete("/stores/{store_id}")
def clear_cart(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
):
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        CartService.clear_cart(
            db=db,
            user_id=current_user.id if current_user else None,
            store_id=store_id,
            guest_token=None if current_user else guest_token,
        )
        cart = CartService.get_or_create_cart(
            db=db,
            user_id=current_user.id if current_user else None,
            store_id=store_id,
            guest_token=None if current_user else guest_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _cart_response(cart)