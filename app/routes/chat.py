import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product, Store
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
