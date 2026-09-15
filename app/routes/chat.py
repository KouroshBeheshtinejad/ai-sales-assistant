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
    if _is_prompt_injection(data.question):
        return ChatResponse(
            success=True,
            answer="فقط می‌توانم دربارهٔ محصولات و قوانین همین فروشگاه پاسخ بدهم.",
        )
    try:
        context = retrieve_store_context(db, store_id, data.question)
    except Exception:
        logger.exception("Chat retrieval failed for store_id=%s", store_id)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant is temporarily unavailable. Please try again later.",
            },
        )
    if context is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    try:
        formatted_context = format_context(context)
        answer = provider.complete(
            SYSTEM_PROMPT,
            _chat_prompt(
                data.question,
                formatted_context,
                _answer_guidance(data.question, context, formatted_context),
            ),
        )
    except LLMProviderError:
        logger.exception("Chat provider failed for store_id=%s", store_id)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant is temporarily unavailable. Please contact the seller directly.",
            },
        )
    except Exception:
        logger.exception("Unexpected chat response-generation failure for store_id=%s", store_id)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant is temporarily unavailable. Please try again later.",
            },
        )

    if not isinstance(answer, str) or not answer.strip():
        logger.warning("Chat provider returned an empty response for store_id=%s", store_id)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant could not produce an answer. Please contact the seller directly.",
            },
        )
    return ChatResponse(success=True, answer=answer.strip())
