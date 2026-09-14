from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import KnowledgeBaseEntry, User
from app.routes.auth import get_current_user
from app.services.knowledge_service import get_knowledge_for_store_or_404, get_store_or_404


router = APIRouter(
    prefix="/stores/{store_id}",
    tags=["Knowledge Base"],
)


class KnowledgeCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    is_active: bool = True


class KnowledgeUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class KnowledgeResponse(BaseModel):
    id: int
    title: str
    content: str
    is_active: bool
    store_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/knowledge", response_model=list[KnowledgeResponse])
def list_knowledge_entries(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        get_store_or_404(db, store_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    entries = (
        db.query(KnowledgeBaseEntry)
        .filter(KnowledgeBaseEntry.store_id == store_id)
        .order_by(KnowledgeBaseEntry.created_at.desc())
        .all()
    )
    return entries


@router.get("/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
def get_knowledge_entry(
    store_id: int,
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        entry = get_knowledge_for_store_or_404(db, store_id, knowledge_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return entry


@router.post("/knowledge", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_entry(
    store_id: int,
    data: KnowledgeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        get_store_or_404(db, store_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    entry = KnowledgeBaseEntry(
        title=data.title.strip(),
        content=data.content.strip(),
        is_active=data.is_active,
        store_id=store_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
def update_knowledge_entry(
    store_id: int,
    knowledge_id: int,
    data: KnowledgeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        entry = get_knowledge_for_store_or_404(db, store_id, knowledge_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    update_data = data.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"] is not None:
        update_data["title"] = update_data["title"].strip()
    if "content" in update_data and update_data["content"] is not None:
        update_data["content"] = update_data["content"].strip()

    for field, value in update_data.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/knowledge/{knowledge_id}")
def delete_knowledge_entry(
    store_id: int,
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        entry = get_knowledge_for_store_or_404(db, store_id, knowledge_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    db.delete(entry)
    db.commit()
    return {"message": "Knowledge entry deleted successfully"}
