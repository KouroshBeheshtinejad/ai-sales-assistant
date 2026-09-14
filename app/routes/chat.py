from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Store
from app.services.chat_retrieval import format_context, retrieve_store_context
from app.services.chat_rate_limit import enforce_chat_rate_limit
from app.services.llm_provider import (
    SYSTEM_PROMPT,
    LLMProvider,
    LLMProviderError,
    get_llm_provider,
)


router = APIRouter(tags=["Public Chat"])
templates = Jinja2Templates(directory="app/templates")


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


def _chat_prompt(question: str, context: str) -> str:
    retrieved_data = context or "No matching information was found."
    return (
        f"Customer question:\n{question}\n\n"
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
    context = retrieve_store_context(db, store_id, data.question)
    if context is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    try:
        answer = provider.complete(
            SYSTEM_PROMPT,
            _chat_prompt(data.question, format_context(context)),
        )
    except LLMProviderError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant is temporarily unavailable. Please contact the seller directly.",
            },
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant is temporarily unavailable. Please try again later.",
            },
        )

    if not answer.strip():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "answer": "The store assistant could not produce an answer. Please contact the seller directly.",
            },
        )
    return ChatResponse(success=True, answer=answer.strip())
