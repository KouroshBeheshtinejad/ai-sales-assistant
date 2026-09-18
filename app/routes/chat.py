import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Store
from app.services.chat_retrieval import (
    RetrievedContext,
    format_context,
    normalize_for_search,
    retrieve_store_context,
)
from app.services.chat_rate_limit import enforce_chat_rate_limit
from app.services.sales_agent import SalesAgentService
from app.services.conversation_service import ConversationService
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
        context={"store": store},
    )


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
):
    enforce_chat_rate_limit(request)
    
    conversation, response_guest_token = (
            ConversationService.get_or_create_conversation(
            db,
            store_id=store_id,
            guest_token=data.guest_token,
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

    try:
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
