import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product, Store
from app.services.chat_retrieval import (
    RetrievedContext,
    format_context,
    normalize_for_search,
    retrieve_store_context,
)
from app.services.chat_rate_limit import enforce_chat_rate_limit
from app.services.sales_agent import SalesAgentService
from app.services.conversation_service import ConversationService
from app.services.sales_intent import SalesIntent, detect_intent
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.guest_commerce import (
    cart_summary,
    extract_customer_fields,
    extract_quantity,
    get_cart,
    is_checkout_cancellation,
    is_confirmation,
    resolve_product,
)
from app.services.llm_provider import (
    SYSTEM_PROMPT,
    LLMProvider,
    LLMProviderError,
    get_llm_provider,
)


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


def _order_confirmation(order) -> str:
    items = "، ".join(
        f"{item.product_name} × {item.quantity}" for item in order.items
    )
    return (
        f"سفارش شما با شماره {order.id} ثبت شد.\n"
        f"اقلام: {items}\n"
        f"مبلغ کل: {order.total_amount}\n"
        f"وضعیت: {order.status}"
    )


_RECOMMENDATION_TERMS = (
    "پیشنهاد", "پیشنهاد می", "recommend", "recommendation", "suggest", "best",
)
_AMBIGUOUS_QUESTIONS = (
    "راهنمایی می کنید",
    "کمک می کنید",
    "میشه راهنمایی کنید",
    "می توانید راهنمایی کنید",
    "can you help",
    "help me",
)


def _is_prompt_injection(question: str) -> bool:
    normalized = normalize_for_search(question)
    tries_to_ignore_rules = (
        ("ignore" in normalized and any(word in normalized for word in ("previous", "rule", "instruction")))
        or ("نادیده" in normalized and any(word in normalized for word in ("دستور", "قانون", "قبلی")))
    )
    tries_to_reveal_prompt = (
        any(word in normalized for word in ("reveal", "show", "افشا", "نمایش", "بگو"))
        and any(word in normalized for word in ("system prompt", "prompt", "دستور سیستم", "پرامپت"))
    )
    return tries_to_ignore_rules or tries_to_reveal_prompt


def _answer_guidance(
    question: str, context: RetrievedContext, formatted_context: str
) -> str:
    normalized_question = normalize_for_search(question)
    if any(phrase in normalized_question for phrase in _AMBIGUOUS_QUESTIONS):
        return "The question is ambiguous. Ask one short, polite clarifying question."
    if context.is_empty:
        return (
            "No relevant store data was retrieved. Clearly say that sufficient information "
            "is not available and suggest contacting the seller."
        )
    if "Data quality notice:" in formatted_context:
        return (
            "The retrieved records conflict. State the uncertainty clearly; do not select, "
            "average, or infer a value."
        )
    if any(term in normalized_question for term in _RECOMMENDATION_TERMS):
        return (
            "This is a product recommendation request. Offer only the retrieved products, "
            "with a brief reason grounded in their listed details."
        )
    if context.products:
        return "Answer directly about the retrieved product or products using their listed details."
    return "Answer the policy or store-information question directly from the retrieved records."


def _chat_prompt(question: str, context: str, answer_guidance: str) -> str:
    retrieved_data = context or "No matching information was found."
    return (
        f"Customer question:\n{question}\n\n"
        f"Response guidance:\n{answer_guidance}\n\n"
        f"Retrieved store data:\n{retrieved_data}"
    )


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
            "description": store.description,
            "logo_url": store.logo_url,
            "business_type": store.business_type,
        },
        "products": [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "image_url": product.image_url,
                "price": str(product.price),
                "stock": product.stock,
                "size": product.size,
                "color": product.color,
                "attributes": product.attributes or {},
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
    conversation, response_guest_token = (
        ConversationService.get_or_create_conversation(
            db,
            store_id=store_id,
            guest_token=request_guest_token,
        )
    )

    agent = SalesAgentService(
        db=db,
        provider=provider,
    )

    history_messages = ConversationService.get_history(
        db,
        conversation_id=conversation.id,
        limit=20,
    )

    history = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in history_messages
        if message.role in {"user", "assistant"}
    ]

    guest_token = response_guest_token or request_guest_token
    intent = detect_intent(data.question)

    try:
        if guest_token and conversation.checkout_state == "awaiting_confirmation":
            if is_confirmation(data.question):
                order = OrderService.create_order(
                    db=db,
                    user_id=None,
                    guest_token=guest_token,
                    store_id=store_id,
                    customer_name=conversation.checkout_customer_name or "",
                    customer_phone=conversation.checkout_customer_phone or "",
                    customer_address=conversation.checkout_customer_address or "",
                    idempotency_key=conversation.checkout_idempotency_key,
                )
                conversation.checkout_state = "completed"
                conversation.checkout_idempotency_key = None
                conversation.last_order_id = order.id
                answer = _order_confirmation(order)
                _persist_chat_turn(db, conversation, data.question, answer)
                return ChatResponse(success=True, answer=answer, guest_token=guest_token)
            if is_checkout_cancellation(data.question):
                conversation.checkout_state = "idle"
                conversation.checkout_idempotency_key = None
                answer = "ثبت سفارش لغو شد. هر زمان خواستید دوباره شروع می‌کنیم."
                _persist_chat_turn(db, conversation, data.question, answer)
                return ChatResponse(success=True, answer=answer, guest_token=guest_token)
            else:
                answer = "برای ثبت سفارش، لطفاً «بله» یا «ثبت کن» را ارسال کنید."

        if guest_token and conversation.checkout_state == "awaiting_customer":
            if is_checkout_cancellation(data.question):
                conversation.checkout_state = "idle"
                conversation.checkout_idempotency_key = None
                answer = "ثبت سفارش لغو شد. هر زمان خواستید دوباره شروع می‌کنیم."
                _persist_chat_turn(db, conversation, data.question, answer)
                return ChatResponse(success=True, answer=answer, guest_token=guest_token)
            fields = extract_customer_fields(data.question)
            if not fields:
                pass
            else:
                if fields.get("name"):
                    conversation.checkout_customer_name = fields["name"]
                if fields.get("phone"):
                    conversation.checkout_customer_phone = fields["phone"]
                if fields.get("address"):
                    conversation.checkout_customer_address = fields["address"]
                if all((
                    conversation.checkout_customer_name,
                    conversation.checkout_customer_phone,
                    conversation.checkout_customer_address,
                )):
                    conversation.checkout_state = "awaiting_confirmation"
                    conversation.checkout_idempotency_key = uuid.uuid4().hex
                    cart = get_cart(db, store_id=store_id, guest_token=guest_token)
                    answer = (
                        f"اطلاعات دریافت شد.\n{cart_summary(cart)}\n"
                        "آیا سفارش را ثبت کنم؟"
                    )
                else:
                    missing = []
                    if not conversation.checkout_customer_name:
                        missing.append("نام")
                    if not conversation.checkout_customer_phone:
                        missing.append("شماره تلفن")
                    if not conversation.checkout_customer_address:
                        missing.append("آدرس")
                    answer = "لطفاً این موارد را ارسال کنید: " + "، ".join(missing)
                _persist_chat_turn(db, conversation, data.question, answer)
                return ChatResponse(success=True, answer=answer, guest_token=guest_token)

        if guest_token and intent == SalesIntent.CART_ADD:
            product = resolve_product(db, store_id, data.question, history)
            quantity = extract_quantity(data.question)
            if product is None:
                answer = "محصول را دقیق‌تر مشخص می‌کنید؟"
            elif quantity is None:
                answer = f"چه تعدادی از «{product.name}» می‌خواهید؟"
            else:
                cart = CartService.add_item(
                    db=db,
                    user_id=None,
                    guest_token=guest_token,
                    store_id=store_id,
                    product_id=product.id,
                    quantity=quantity,
                )
                answer = f"{quantity} عدد «{product.name}» به سبد خرید اضافه شد.\n{cart_summary(cart)}"
            _persist_chat_turn(db, conversation, data.question, answer)
            return ChatResponse(success=True, answer=answer, guest_token=guest_token)

        if guest_token and intent == SalesIntent.CART_VIEW:
            answer = cart_summary(get_cart(db, store_id=store_id, guest_token=guest_token))
            _persist_chat_turn(db, conversation, data.question, answer)
            return ChatResponse(success=True, answer=answer, guest_token=guest_token)

        if guest_token and intent in {SalesIntent.CHECKOUT, SalesIntent.ORDER_CREATE}:
            cart = get_cart(db, store_id=store_id, guest_token=guest_token)
            if not cart.items:
                answer = "سبد خرید شما خالی است. ابتدا یک محصول به سبد اضافه کنید."
            else:
                fields = extract_customer_fields(data.question)
                conversation.checkout_customer_name = fields.get("name")
                conversation.checkout_customer_phone = fields.get("phone")
                conversation.checkout_customer_address = fields.get("address")
                if all(fields.get(key) for key in ("name", "phone", "address")):
                    conversation.checkout_state = "awaiting_confirmation"
                    conversation.checkout_idempotency_key = uuid.uuid4().hex
                    answer = f"{cart_summary(cart)}\nآیا سفارش را ثبت کنم؟"
                else:
                    conversation.checkout_state = "awaiting_customer"
                    answer = "برای checkout لطفاً نام، شماره تلفن و آدرس خود را ارسال کنید."
            _persist_chat_turn(db, conversation, data.question, answer)
            return ChatResponse(success=True, answer=answer, guest_token=guest_token)

        answer = agent.respond(
            store_id=store_id,
            question=data.question,
            history=history,
        )
        ConversationService.add_message(
            db,
            conversation_id=conversation.id,
            role="user",
            content=data.question,
        )
        ConversationService.add_message(
            db,
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
        )
        db.commit()
        
    except ValueError as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "answer": str(exc)},
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    except LLMProviderError as exc:
        if "empty response" in str(exc).lower():
            logger.warning(
                "Chat provider could not produce an answer: %s",
                exc,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False,
                    "answer": (
                        "The store assistant could not produce an answer. "
                        "Please try again later."
                    ),
                },
            )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": (
                    "The store assistant is temporarily unavailable. "
                    "Please contact the seller directly."
                ),
            },
        )
    except Exception:
        logger.exception(
            "Unexpected chat response-generation failure for store_id=%s",
            store_id,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": (
                    "The store assistant is temporarily unavailable. "
                    "Please try again later."
                ),
            },
        )

    return ChatResponse(
        success=True,
        answer=answer,
        guest_token=response_guest_token,
    )
