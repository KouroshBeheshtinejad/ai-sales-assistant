from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.csrf import require_csrf_header
from app.db.database import get_db
from app.db.models import Conversation, Message, Order, Store, User
from app.routes.auth import get_current_user
from app.security.policies import has_store_permission, store_scope_filter
from app.services.audit_service import record_audit_log
from app.services.chat_rate_limit import enforce_auth_rate_limit


router = APIRouter(prefix="/support", tags=["Support"])
SUPPORT_STATUSES = {"new", "assigned", "waiting_customer", "waiting_support", "resolved", "closed"}


def _require_support(user: User) -> None:
    if user.approval_status != "active" or user.role not in {"support", "god"}:
        raise HTTPException(status_code=403, detail="Support access required")


def _support_item(db: Session, conversation_id: int) -> Conversation:
    item = db.scalar(
        select(Conversation)
        .options(joinedload(Conversation.messages), joinedload(Conversation.user), joinedload(Conversation.store))
        .where(Conversation.id == conversation_id, Conversation.kind == "support")
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item


def _customer_item(db: Session, conversation_id: int, user: User) -> Conversation:
    accessible_stores = select(Store.id).where(store_scope_filter(user, "support.contact"))
    item = db.scalar(
        select(Conversation)
        .options(joinedload(Conversation.messages), joinedload(Conversation.user), joinedload(Conversation.store))
        .where(
            Conversation.id == conversation_id,
            Conversation.kind == "support",
            or_(
                Conversation.user_id == user.id,
                Conversation.store_id.in_(accessible_stores),
            ),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item


def _response(db: Session, item: Conversation) -> dict:
    order = db.get(Order, item.last_order_id) if item.last_order_id else None
    return {
        "id": item.id,
        "user_id": item.user_id,
        "store_id": item.store_id,
        "status": item.support_status,
        "priority": item.priority,
        "assigned_to": item.assigned_to,
        "customer": {
            "id": item.user.id,
            "name": " ".join(part for part in (item.user.first_name, item.user.last_name) if part),
            "email": item.user.email,
            "phone": item.user.phone,
        } if item.user else None,
        "store": {"id": item.store.id, "name": item.store.name} if item.store else None,
        "order": {
            "id": order.id,
            "status": order.status,
            "tracking_number": order.tracking_number,
            "total_amount": str(order.total_amount),
        } if order and order.user_id == item.user_id else None,
        "updated_at": item.updated_at,
        "messages": [
            {"id": message.id, "role": message.role, "content": message.content, "created_at": message.created_at}
            for message in item.messages
        ],
    }


class NewSupportConversation(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    store_id: int | None = Field(None, gt=0)
    order_id: int | None = Field(None, gt=0)


class SupportReply(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class SupportStatusUpdate(BaseModel):
    status: Literal["waiting_customer", "waiting_support", "resolved", "closed"]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_support_conversation(
    payload: NewSupportConversation,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_header),
):
    enforce_auth_rate_limit(request, "support-message")
    if payload.order_id is not None:
        order = db.scalar(
            select(Order).where(Order.id == payload.order_id, Order.user_id == user.id)
        )
        if order is None or (payload.store_id is not None and payload.store_id != order.store_id):
            raise HTTPException(status_code=404, detail="Order not found")
        store_id = order.store_id
    else:
        store_id = payload.store_id
    if (
        store_id is not None
        and user.role not in {"customer", "support", "god"}
        and not has_store_permission(db, user, store_id, "support.contact")
    ):
        raise HTTPException(status_code=404, detail="Store not found")
    item = Conversation(
        user_id=user.id,
        store_id=store_id,
        last_order_id=payload.order_id,
        kind="support",
        support_status="new",
        status="active",
    )
    db.add(item)
    db.flush()
    db.add(Message(conversation_id=item.id, role="user", content=payload.message.strip()))
    record_audit_log(
        db, actor=user, action="support.conversation_created", resource_type="conversation",
        resource_id=item.id, store_id=item.store_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": item.id, "status": item.support_status}


@router.get("/conversations")
def list_customer_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    accessible_stores = select(Store.id).where(store_scope_filter(user, "support.contact"))
    items = db.scalars(
        select(Conversation)
        .options(joinedload(Conversation.messages), joinedload(Conversation.user), joinedload(Conversation.store))
        .where(
            Conversation.kind == "support",
            or_(Conversation.user_id == user.id, Conversation.store_id.in_(accessible_stores)),
        )
        .order_by(Conversation.updated_at.desc())
    ).unique().all()
    return [_response(db, item) for item in items]


@router.get("/conversations/{conversation_id}")
def get_customer_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _response(db, _customer_item(db, conversation_id, user))


@router.post("/conversations/{conversation_id}/reply")
def customer_reply(
    conversation_id: int,
    payload: SupportReply,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_header),
):
    enforce_auth_rate_limit(request, "support-message")
    item = _customer_item(db, conversation_id, user)
    if item.support_status in {"resolved", "closed"}:
        raise HTTPException(status_code=409, detail="Conversation is closed")
    db.add(Message(conversation_id=item.id, role="user", content=payload.message.strip()))
    item.support_status = "waiting_support"
    record_audit_log(
        db, actor=user, action="support.customer_replied", resource_type="conversation",
        resource_id=item.id, store_id=item.store_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": item.id, "status": item.support_status}


@router.get("/queue")
def support_queue(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_support(user)
    query = select(Conversation).where(Conversation.kind == "support")
    if status_filter is not None:
        if status_filter not in SUPPORT_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid support status")
        query = query.where(Conversation.support_status == status_filter)
    items = db.scalars(
        query.options(
            joinedload(Conversation.messages), joinedload(Conversation.user), joinedload(Conversation.store)
        ).order_by(Conversation.updated_at.desc())
    ).unique().all()
    return [_response(db, item) for item in items]


@router.get("/summary")
def support_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role in {"support", "god"}:
        _require_support(user)
        attention = db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.kind == "support",
                Conversation.support_status.in_(("new", "waiting_support")),
                or_(Conversation.assigned_to.is_(None), Conversation.assigned_to == user.id),
            )
        )
        return {"attention_count": attention or 0, "kind": "queue"}

    attention = db.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.kind == "support",
            Conversation.user_id == user.id,
            Conversation.support_status == "waiting_customer",
        )
    )
    return {"attention_count": attention or 0, "kind": "replies"}


@router.post("/queue/{conversation_id}/claim")
def claim_support_conversation(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_header),
):
    _require_support(user)
    claimed = db.execute(
        update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.kind == "support",
            Conversation.support_status.not_in(("resolved", "closed")),
            or_(Conversation.assigned_to.is_(None), Conversation.assigned_to == user.id),
        )
        .values(assigned_to=user.id, support_status="assigned")
    )
    if claimed.rowcount != 1:
        item = _support_item(db, conversation_id)
        if item.support_status in {"resolved", "closed"}:
            raise HTTPException(status_code=409, detail="Conversation is closed")
        raise HTTPException(status_code=409, detail="Conversation is already assigned")
    item = _support_item(db, conversation_id)
    record_audit_log(
        db, actor=user, action="support.conversation_claimed", resource_type="conversation",
        resource_id=item.id, store_id=item.store_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": item.id, "status": item.support_status, "assigned_to": user.id}


@router.post("/queue/{conversation_id}/reply")
def support_reply(
    conversation_id: int,
    payload: SupportReply,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_header),
):
    _require_support(user)
    enforce_auth_rate_limit(request, "support-message")
    item = _support_item(db, conversation_id)
    if item.assigned_to != user.id and user.role != "god":
        raise HTTPException(status_code=403, detail="Claim this conversation first")
    if item.support_status in {"resolved", "closed"}:
        raise HTTPException(status_code=409, detail="Conversation is closed")
    db.add(Message(conversation_id=item.id, role="assistant", content=payload.message.strip()))
    item.support_status = "waiting_customer"
    record_audit_log(
        db, actor=user, action="support.agent_replied", resource_type="conversation",
        resource_id=item.id, store_id=item.store_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": item.id, "status": item.support_status}


@router.patch("/queue/{conversation_id}/status")
def update_support_status(
    conversation_id: int,
    payload: SupportStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_header),
):
    _require_support(user)
    item = _support_item(db, conversation_id)
    if item.assigned_to != user.id and user.role != "god":
        raise HTTPException(status_code=403, detail="Claim this conversation first")
    previous_status = item.support_status
    item.support_status = payload.status
    if payload.status == "closed":
        item.status = "closed"
    record_audit_log(
        db, actor=user, action="support.status_changed", resource_type="conversation",
        resource_id=item.id, store_id=item.store_id,
        before_state={"status": previous_status}, after_state={"status": payload.status},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": item.id, "status": item.support_status}