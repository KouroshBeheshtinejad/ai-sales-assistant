from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import FAQ, User
from app.routes.auth import get_current_user
from app.services.knowledge_service import get_faq_for_store_or_404, get_store_or_404
from app.services.semantic_index import (
    SOURCE_FAQ,
    safely_discard_semantic_document,
    safely_sync_semantic_document,
)


router = APIRouter(
    prefix="/stores/{store_id}",
    tags=["FAQs"],
)


class FAQCreateRequest(BaseModel):
    question: str = Field(..., max_length=500)
    answer: str = Field(..., max_length=10000)
    is_active: bool = True

    @field_validator("question", "answer")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("FAQ text must not be blank")
        return value


class FAQUpdateRequest(BaseModel):
    question: str | None = Field(default=None, max_length=500)
    answer: str | None = Field(default=None, max_length=10000)
    is_active: bool | None = None

    @field_validator("question", "answer")
    @classmethod
    def text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("FAQ text must not be blank")
        return value


class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    is_active: bool
    store_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/faqs", response_model=list[FAQResponse])
def list_faqs(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        get_store_or_404(db, store_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    faqs = (
        db.query(FAQ)
        .filter(FAQ.store_id == store_id)
        .order_by(FAQ.created_at.desc())
        .all()
    )
    return faqs


@router.get("/faqs/{faq_id}", response_model=FAQResponse)
def get_faq(
    store_id: int,
    faq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        faq = get_faq_for_store_or_404(db, store_id, faq_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return faq


@router.post("/faqs", response_model=FAQResponse, status_code=status.HTTP_201_CREATED)
def create_faq(
    store_id: int,
    data: FAQCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        get_store_or_404(db, store_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    faq = FAQ(
        question=data.question.strip(),
        answer=data.answer.strip(),
        is_active=data.is_active,
        store_id=store_id,
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)
    safely_sync_semantic_document(db, faq)
    return faq


@router.put("/faqs/{faq_id}", response_model=FAQResponse)
def update_faq(
    store_id: int,
    faq_id: int,
    data: FAQUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        faq = get_faq_for_store_or_404(db, store_id, faq_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    safely_discard_semantic_document(db, SOURCE_FAQ, faq.id, faq.store_id)
    update_data = data.model_dump(exclude_unset=True)
    if "question" in update_data and update_data["question"] is not None:
        update_data["question"] = update_data["question"].strip()
    if "answer" in update_data and update_data["answer"] is not None:
        update_data["answer"] = update_data["answer"].strip()

    for field, value in update_data.items():
        setattr(faq, field, value)

    db.commit()
    db.refresh(faq)
    safely_sync_semantic_document(db, faq)
    return faq


@router.delete("/faqs/{faq_id}")
def delete_faq(
    store_id: int,
    faq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        faq = get_faq_for_store_or_404(db, store_id, faq_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    safely_discard_semantic_document(db, SOURCE_FAQ, faq.id, faq.store_id)
    db.delete(faq)
    db.commit()
    return {"message": "FAQ deleted successfully"}
