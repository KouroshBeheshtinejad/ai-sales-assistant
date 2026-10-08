import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Order, OrderItem, Product, Store, StoreReview, User
from app.routes.auth import get_current_user
from app.services.chat_flow import checkout_reminder, handle_commerce_turn
from app.services.chat_rate_limit import enforce_chat_rate_limit
from app.services.conversation_service import ConversationService
from app.services.grounded_responder import friendly_error
from app.services.llm_provider import (
    LLMProvider,
    LLMProviderError,
    get_llm_provider,
)
from app.services.sales_agent import SalesAgentService
from app.services.text_utils import detect_language


router = APIRouter(tags=["Public Chat"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    guest_token: str | None = None

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank")
        return value


class ChatResponse(BaseModel):
    success: bool
    answer: str
    guest_token: str | None = None


class StoreReviewInput(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=1, max_length=2000)
    title: str | None = Field(None, max_length=120)
    product_id: int | None = Field(None, gt=0)
    parent_id: int | None = Field(None, gt=0)


def _store_rating_summary(db: Session, store_id: int):
    rows = db.query(StoreReview.rating).filter(StoreReview.store_id == store_id).all()
    ratings = [row[0] for row in rows]
    if not ratings:
        return {"average_rating": 0.0, "reviews_count": 0, "rating": 0.0}
    average = sum(ratings) / len(ratings)
    return {
        "average_rating": round(average, 2),
        "reviews_count": len(ratings),
        "rating": round(average, 2),
    }


def _persist_chat_turn(db, conversation, question: str, answer: str) -> None:
    ConversationService.add_message(
        db, conversation_id=conversation.id, role="user", content=question
    )
    ConversationService.add_message(
        db, conversation_id=conversation.id, role="assistant", content=answer
    )
    db.commit()


@router.get(
    "/public/stores/{store_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def public_store_page(
    store_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return templates.TemplateResponse(
        request=request,
        name="public_store.html",
        context={
            "store": store,
            "products": (
                db.query(Product)
                .filter(Product.store_id == store_id, Product.is_active.is_(True))
                .order_by(Product.id)
                .all()
            ),
        },
    )


@router.get("/public/stores/{store_id}/catalog")
def public_store_catalog(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    rating_summary = _store_rating_summary(db, store_id)
    products = (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.is_active.is_(True))
        .order_by(Product.id)
        .all()
    )
    return {
        "store": {
            "id": store.id,
            "name": store.name,
            "country_code": store.country_code,
            "currency": store.currency,
            "description": store.description,
            "logo_url": store.logo_url,
            "business_type": store.business_type,
            "categories": store.categories or [],
            "primary_color": store.primary_color,
            "secondary_color": store.secondary_color,
            "contact_phone": store.contact_phone,
            "address": store.address,
            "location_name": store.location_name,
            "latitude": float(store.latitude) if store.latitude is not None else None,
            "longitude": float(store.longitude) if store.longitude is not None else None,
            "location_url": store.location_url,
            "store_hours": store.store_hours,
            "average_rating": rating_summary["average_rating"],
            "reviews_count": rating_summary["reviews_count"],
            "rating": rating_summary["rating"],
        },
        "products": [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "image_url": product.image_url,
                "price": str(product.price),
                "currency": store.currency,
                "stock": product.stock - product.reserved_stock,
                "size": product.size,
                "color": product.color,
                "attributes": product.attributes or {},
                "category_ids": product.category_ids or [],
                "is_active": product.is_active,
            }
            for product in products
        ],
    }


@router.get("/public/stores/{store_id}/reviews")
def public_store_reviews(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    reviews = (
        db.query(StoreReview)
        .filter(StoreReview.store_id == store_id, StoreReview.parent_id.is_(None))
        .order_by(StoreReview.created_at.desc())
        .all()
    )
    summary = _store_rating_summary(db, store_id)
    payload = []
    for review in reviews:
        user_name = "مشتری"
        if review.user:
            parts = [part for part in (review.user.first_name, review.user.last_name) if part]
            user_name = " ".join(parts) or review.user.email.split("@", 1)[0]
        product_name = None
        if review.product_id:
            product = db.get(Product, review.product_id)
            product_name = product.name if product else None
        replies = []
        for reply in review.replies:
            reply_user_name = "مشتری"
            if reply.user:
                parts = [part for part in (reply.user.first_name, reply.user.last_name) if part]
                reply_user_name = " ".join(parts) or reply.user.email.split("@", 1)[0]
            replies.append({
                "id": reply.id,
                "user_id": reply.user_id,
                "user_name": reply_user_name,
                "comment": reply.comment,
                "rating": reply.rating,
                "created_at": reply.created_at.isoformat(),
            })
        payload.append({
            "id": review.id,
            "user_id": review.user_id,
            "user_name": user_name,
            "rating": review.rating,
            "title": review.title,
            "comment": review.comment,
            "created_at": review.created_at.isoformat(),
            "product_id": review.product_id,
            "product_name": product_name,
            "reply_count": len(replies),
            "replies": replies,
        })
    return {
        "store_id": store_id,
        "store_name": store.name,
        "average_rating": summary["average_rating"],
        "reviews_count": summary["reviews_count"],
        "reviews": payload,
    }


@router.post("/public/stores/{store_id}/reviews")
def create_store_review(
    store_id: int,
    data: StoreReviewInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    if data.product_id is not None:
        product = db.get(Product, data.product_id)
        if product is None or product.store_id != store_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if data.parent_id is not None:
        parent = db.get(StoreReview, data.parent_id)
        if parent is None or parent.store_id != store_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply target not found")
    if data.product_id is None:
        has_paid_order = bool(
            db.query(Order.id)
            .filter(
                Order.store_id == store_id,
                Order.user_id == current_user.id,
                Order.paid_at.is_not(None),
                Order.status.in_(("paid", "completed", "fulfilled", "shipped", "delivered")),
            )
            .first()
        )
    else:
        has_paid_order = bool(
            db.query(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                OrderItem.product_id == data.product_id,
                Order.store_id == store_id,
                Order.user_id == current_user.id,
                Order.paid_at.is_not(None),
                Order.status.in_(("paid", "completed", "fulfilled", "shipped", "delivered")),
            )
            .first()
        )
    if not has_paid_order:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You need a paid order from this store to review it.")
    if data.product_id is not None:
        existing = db.query(StoreReview.id).filter(StoreReview.user_id == current_user.id, StoreReview.product_id == data.product_id).first()
    else:
        existing = db.query(StoreReview.id).filter(StoreReview.user_id == current_user.id, StoreReview.store_id == store_id, StoreReview.product_id.is_(None)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already reviewed this store.")
    review = StoreReview(
        user_id=current_user.id,
        store_id=store_id,
        product_id=data.product_id,
        rating=data.rating,
        title=data.title,
        comment=data.comment,
        parent_id=data.parent_id,
        is_approved=True,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already reviewed this item.")
    db.refresh(review)
    return {
        "message": "Review submitted successfully",
        "review": {
            "id": review.id,
            "rating": review.rating,
            "title": review.title,
            "comment": review.comment,
            "product_id": review.product_id,
            "store_id": review.store_id,
            "created_at": review.created_at.isoformat(),
        },
    }


@router.post(
    "/public/stores/{store_id}/chat",
    response_model=ChatResponse,
)
def chat(
    store_id: int,
    request: Request,
    data: ChatRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
    guest_token_header: str | None = Header(default=None, alias="X-Guest-Token"),
):
    enforce_chat_rate_limit(request)

    request_guest_token = data.guest_token or guest_token_header
    conversation, response_guest_token = ConversationService.get_or_create_conversation(
        db,
        store_id=store_id,
        guest_token=request_guest_token,
    )

    agent = SalesAgentService(db=db, provider=provider)

    history_messages = ConversationService.get_history(
        db,
        conversation_id=conversation.id,
        limit=20,
    )
    history = [
        {"role": message.role, "content": message.content}
        for message in history_messages
        if message.role in {"user", "assistant"}
    ]

    guest_token = response_guest_token or request_guest_token

    try:
        # 1) Cart / checkout / tracking run deterministically (never via the model).
        answer = handle_commerce_turn(
            db,
            conversation,
            store_id=store_id,
            guest_token=guest_token,
            question=data.question,
            history=history,
        )

        # 2) Everything else is answered by the grounded assistant (RAG + model/offline).
        if answer is None:
            answer = agent.respond(
                store_id=store_id,
                question=data.question,
                history=history,
                context={
                    "conversation": conversation,
                    "guest_token": guest_token,
                    "user_id": None,
                },
            )
            answer += checkout_reminder(conversation, data.question)

        _persist_chat_turn(db, conversation, data.question, answer)

    except ValueError as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "answer": friendly_error(str(exc), detect_language(data.question)),
            },
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    except LLMProviderError as exc:  # defensive: the agent normally absorbs provider failures
        logger.warning("Chat provider failure escaped the agent: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant is temporarily unavailable. Please contact the seller directly.",
            },
        )
    except Exception:
        db.rollback()
        logger.exception(
            "Unexpected chat response-generation failure for store_id=%s",
            store_id,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant is temporarily unavailable. Please try again later.",
            },
        )

    return ChatResponse(
        success=True,
        answer=answer,
        guest_token=guest_token,
    )
