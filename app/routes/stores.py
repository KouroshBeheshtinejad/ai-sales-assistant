from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.business_types import get_business_type_label, normalize_business_type
from app.db.database import get_db
from app.db.models import Store, User
from app.routes.auth import get_current_user


router = APIRouter(
    prefix="/stores",
    tags=["Stores"],
)


class StoreCreateRequest(BaseModel):
    name: str
    description: str | None = None
    business_type: str = "clothing"


@router.post("/")
def create_store(
    data: StoreCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_business_type = normalize_business_type(data.business_type)
    store = Store(
        name=data.name,
        description=data.description,
        business_type=normalized_business_type,
        owner_id=current_user.id,
    )

    db.add(store)
    db.commit()
    db.refresh(store)

    return {
        "message": "Store created successfully",
        "store_id": store.id,
        "name": store.name,
        "description": store.description,
        "business_type": store.business_type,
        "business_type_label": get_business_type_label(store.business_type),
    }


@router.get("/")
def get_my_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stores = (
        db.query(Store)
        .filter(Store.owner_id == current_user.id)
        .all()
    )

    return [
        {
            "id": store.id,
            "name": store.name,
            "description": store.description,
            "business_type": store.business_type,
            "business_type_label": get_business_type_label(store.business_type),
            "created_at": store.created_at,
        }
        for store in stores
    ]

@router.get("/{store_id}")
def get_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            Store.owner_id == current_user.id,
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    return {
        "id": store.id,
        "name": store.name,
        "description": store.description,
        "business_type": store.business_type,
        "business_type_label": get_business_type_label(store.business_type),
        "created_at": store.created_at,
    }

class StoreUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    business_type: str | None = None


@router.put("/{store_id}")
def update_store(
    store_id: int,
    data: StoreUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            Store.owner_id == current_user.id,
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "business_type" in update_data and update_data["business_type"] is not None:
        update_data["business_type"] = normalize_business_type(update_data["business_type"])

    for field, value in update_data.items():
        setattr(store, field, value)

    db.commit()
    db.refresh(store)

    return {
        "message": "Store updated successfully",
        "store_id": store.id,
        "name": store.name,
        "description": store.description,
        "business_type": store.business_type,
        "business_type_label": get_business_type_label(store.business_type),
    }

@router.delete("/{store_id}")
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            Store.owner_id == current_user.id,
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    db.delete(store)
    db.commit()

    return {
        "message": "Store deleted successfully",
        "store_id": store_id,
    }