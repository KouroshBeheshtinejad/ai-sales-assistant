from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.db.models import Conversation, Store, User
from app.routes.auth import get_current_user, get_current_user_from_cookie

router = APIRouter(prefix="/seller/conversations", tags=["Seller Conversations"])
templates = Jinja2Templates(directory="app/templates")


def _owned_store(db: Session, seller_id: int, store_id: int) -> Store:
    store = db.scalar(select(Store).where(Store.id == store_id, Store.owner_id == seller_id))
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


def _conversation_response(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "store_id": conversation.store_id,
        "guest_token": conversation.guest_token,
        "user_id": conversation.user_id,
        "status": conversation.status,
        "checkout_state": conversation.checkout_state,
        "last_order_id": conversation.last_order_id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in conversation.messages
        ],
    }


@router.get("/view/{store_id}", response_class=HTMLResponse, include_in_schema=False)
def conversations_page(
    store_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    _owned_store(db, current_user.id, store_id)
    conversations = db.scalars(
        select(Conversation)
        .options(joinedload(Conversation.messages))
        .where(Conversation.store_id == store_id)
        .order_by(Conversation.updated_at.desc())
    ).unique().all()
    return templates.TemplateResponse(
        request=request,
        name="seller_conversations.html",
        context={"conversations": conversations, "store_id": store_id, "user": current_user},
    )


@router.get("/stores/{store_id}")
def list_conversations(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _owned_store(db, current_user.id, store_id)
    conversations = db.scalars(
        select(Conversation)
        .options(joinedload(Conversation.messages))
        .where(Conversation.store_id == store_id)
        .order_by(Conversation.updated_at.desc())
    ).unique().all()
    return [_conversation_response(conversation) for conversation in conversations]


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = db.scalar(
        select(Conversation)
        .join(Store, Conversation.store_id == Store.id)
        .options(joinedload(Conversation.messages))
        .where(Conversation.id == conversation_id, Store.owner_id == current_user.id)
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _conversation_response(conversation)
