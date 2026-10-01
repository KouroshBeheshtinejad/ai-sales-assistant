import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Order, Product, Store, User
from app.routes.auth import get_current_user
from app.services.order_service import OrderService


router = APIRouter(prefix="/admin", tags=["Administration"])


def _require_god(user: User) -> None:
    configured_email = os.getenv("GOD_USER_EMAIL", "").strip().casefold()
    if user.role != "god" or not configured_email or user.email.casefold() != configured_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="God access required")


def _require_support(user: User) -> None:
    if user.role not in {"support", "god"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Support access required")


class RoleUpdate(BaseModel):
    role: Literal["customer", "store_owner", "support"]


class AccountDecision(BaseModel):
    status: Literal["active", "rejected"]


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    return [
        {
            "id": user.id,
            "email": user.email,
            "name": " ".join(part for part in (user.first_name, user.last_name) if part),
            "role": user.role,
            "approval_status": user.approval_status,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
        }
        for user in db.scalars(select(User).order_by(User.id))
    ]


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.email.casefold() == current_user.email.casefold():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The God role is environment-managed")
    user.role = payload.role
    user.approval_status = "active" if payload.role == "customer" else "pending"
    user.token_version += 1
    db.commit()
    return {"id": user.id, "email": user.email, "role": user.role, "approval_status": user.approval_status}


@router.patch("/users/{user_id}/approval")
def decide_account_request(
    user_id: int,
    payload: AccountDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role not in {"store_owner", "support"} or user.approval_status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No account approval is pending")
    if payload.status == "active" and not user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email verification is required first")
    user.approval_status = payload.status
    user.token_version += 1
    db.commit()
    return {"id": user.id, "role": user.role, "approval_status": user.approval_status}


@router.get("/stores")
def list_all_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    stores = db.scalars(select(Store).order_by(Store.created_at.desc())).all()
    return [
        {"id": store.id, "name": store.name, "owner_id": store.owner_id, "owner_email": store.owner.email, "business_type": store.business_type}
        for store in stores
    ]


@router.get("/products")
def list_all_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    products = db.scalars(select(Product).order_by(Product.created_at.desc())).all()
    return [
        {"id": product.id, "store_id": product.store_id, "name": product.name, "price": str(product.price), "stock": product.stock, "is_active": product.is_active}
        for product in products
    ]


@router.get("/orders")
def support_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_support(current_user)
    orders = db.scalars(
        select(Order)
        .where(OrderService.finalized_order_filter())
        .order_by(Order.created_at.desc())
    ).unique()
    return [
        {
            "id": order.id,
            "store_id": order.store_id,
            "status": order.status,
            "tracking_number": order.tracking_number,
            "invoice_number": order.invoice_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "total_amount": str(order.total_amount),
            "created_at": order.created_at,
        }
        for order in orders
    ]