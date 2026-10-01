import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AuditLog, Conversation, FAQ, KnowledgeBaseEntry, Order, Payment, Product, Store, StoreMembership, User
from app.routes.auth import get_current_user
from app.services.audit_service import record_audit_log
from app.services.order_service import OrderService


router = APIRouter(prefix="/admin", tags=["Administration"])

_DATABASE_ENTITIES = {
    "users": (User, ("id", "email", "role", "approval_status", "is_verified", "created_at"), ("email", "role", "approval_status")),
    "stores": (Store, ("id", "name", "owner_id", "business_type", "created_at"), ("name", "business_type")),
    "memberships": (StoreMembership, ("id", "store_id", "user_id", "role", "status", "created_at"), ("role", "status")),
    "products": (Product, ("id", "store_id", "name", "price", "stock", "reserved_stock", "is_active", "created_at"), ("name",)),
    "orders": (Order, ("id", "store_id", "user_id", "status", "customer_name", "tracking_number", "total_amount", "created_at"), ("customer_name", "tracking_number", "status")),
    "payments": (Payment, ("id", "order_id", "status", "amount", "provider", "created_at"), ("status", "provider")),
    "conversations": (Conversation, ("id", "store_id", "user_id", "kind", "support_status", "assigned_to", "updated_at"), ("kind", "support_status")),
    "faqs": (FAQ, ("id", "store_id", "question", "is_active", "updated_at"), ("question",)),
    "knowledge": (KnowledgeBaseEntry, ("id", "store_id", "title", "is_active", "updated_at"), ("title",)),
    "audit_logs": (AuditLog, ("id", "actor_user_id", "action", "resource_type", "resource_id", "store_id", "created_at"), ("action", "resource_type")),
}


def _database_row(record, fields: tuple[str, ...]) -> dict:
    return {field: getattr(record, field) for field in fields}


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


class StoreOwnerTransfer(BaseModel):
    user_id: int


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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.email.casefold() == current_user.email.casefold():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The God role is environment-managed")
    before_state = {"role": user.role, "approval_status": user.approval_status}
    user.role = payload.role
    user.approval_status = "active" if payload.role == "customer" else "pending"
    user.token_version += 1
    record_audit_log(
        db,
        actor=current_user,
        action="user.role_changed",
        resource_type="user",
        resource_id=user.id,
        before_state=before_state,
        after_state={"role": user.role, "approval_status": user.approval_status},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": user.id, "email": user.email, "role": user.role, "approval_status": user.approval_status}


@router.patch("/users/{user_id}/approval")
def decide_account_request(
    user_id: int,
    payload: AccountDecision,
    request: Request,
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
    previous_status = user.approval_status
    user.approval_status = payload.status
    user.token_version += 1
    record_audit_log(
        db,
        actor=current_user,
        action=f"user.{payload.status}",
        resource_type="user",
        resource_id=user.id,
        before_state={"approval_status": previous_status},
        after_state={"approval_status": user.approval_status},
        ip_address=request.client.host if request.client else None,
    )
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


@router.patch("/stores/{store_id}/owner")
def transfer_store_ownership(
    store_id: int,
    payload: StoreOwnerTransfer,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    store = db.get(Store, store_id)
    new_owner = db.get(User, payload.user_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    if new_owner is None or not new_owner.is_verified or new_owner.approval_status != "active":
        raise HTTPException(status_code=400, detail="New owner must be a verified active user")
    if store.owner_id == new_owner.id:
        raise HTTPException(status_code=409, detail="User already owns this store")

    previous_owner = db.get(User, store.owner_id)
    previous_owner_id = store.owner_id
    store.owner_id = new_owner.id
    if previous_owner is not None:
        previous_owner.token_version += 1
    new_owner.token_version += 1
    record_audit_log(
        db,
        actor=current_user,
        action="store.owner_changed",
        resource_type="store",
        resource_id=store.id,
        store_id=store.id,
        before_state={"owner_id": previous_owner_id},
        after_state={"owner_id": new_owner.id},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"store_id": store.id, "owner_id": new_owner.id}


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


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    entries = db.scalars(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        {
            "id": entry.id,
            "actor_user_id": entry.actor_user_id,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "store_id": entry.store_id,
            "created_at": entry.created_at,
            "before_state": entry.before_state,
            "after_state": entry.after_state,
            "metadata": entry.metadata_json,
            "ip_address": entry.ip_address,
        }
        for entry in entries
    ]


@router.get("/database/summary")
def database_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    entities = (
        ("users", User),
        ("stores", Store),
        ("memberships", StoreMembership),
        ("products", Product),
        ("orders", Order),
        ("payments", Payment),
        ("conversations", Conversation),
        ("audit_logs", AuditLog),
    )
    return [
        {"entity": name, "count": db.scalar(select(func.count()).select_from(model)) or 0}
        for name, model in entities
    ]


@router.get("/system/overview")
def system_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    try:
        db.execute(select(1))
        database_status = "ok"
    except Exception:
        db.rollback()
        return {
            "database_status": "unavailable",
            "users": {"total": 0, "active": 0, "pending": 0},
            "stores": {"total": 0},
            "orders": {"total": 0},
            "payments": {"total": 0, "by_status": {"pending": 0, "paid": 0, "failed": 0}},
            "open_support": 0,
            "recent_audit": [],
        }
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(select(func.count(User.id)).where(User.approval_status == "active")) or 0
    pending_users = db.scalar(select(func.count(User.id)).where(User.approval_status == "pending")) or 0
    total_stores = db.scalar(select(func.count(Store.id))) or 0
    total_orders = db.scalar(select(func.count(Order.id))) or 0
    total_payments = db.scalar(select(func.count(Payment.id))) or 0
    payment_counts = {
        state: db.scalar(select(func.count(Payment.id)).where(Payment.status == state)) or 0
        for state in ("pending", "paid", "failed")
    }
    open_support = db.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.kind == "support",
            Conversation.support_status.not_in(("resolved", "closed")),
        )
    ) or 0
    recent_audit = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(10)
    ).all()
    return {
        "database_status": database_status,
        "users": {"total": total_users, "active": active_users, "pending": pending_users},
        "stores": {"total": total_stores},
        "orders": {"total": total_orders},
        "payments": {"total": total_payments, "by_status": payment_counts},
        "open_support": open_support,
        "recent_audit": [
            {"id": entry.id, "action": entry.action, "resource_type": entry.resource_type, "resource_id": entry.resource_id, "created_at": entry.created_at}
            for entry in recent_audit
        ],
    }


@router.get("/database/{entity}")
def search_database_records(
    entity: str,
    q: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    definition = _DATABASE_ENTITIES.get(entity)
    if definition is None:
        raise HTTPException(status_code=404, detail="Database entity not found")
    model, fields, search_fields = definition
    query = select(model)
    if q.strip():
        query = query.where(
            or_(*(cast(getattr(model, field), String).ilike(f"%{q.strip()}%") for field in search_fields))
        )
    records = db.scalars(query.order_by(model.id.desc()).limit(100)).all()
    return [_database_row(record, fields) for record in records]


@router.get("/database/{entity}/{record_id}")
def inspect_database_record(
    entity: str,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    definition = _DATABASE_ENTITIES.get(entity)
    if definition is None:
        raise HTTPException(status_code=404, detail="Database entity not found")
    model, fields, _search_fields = definition
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Database record not found")
    return _database_row(record, fields)