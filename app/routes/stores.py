from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_types import get_business_type_label, normalize_business_type
from app.db.database import get_db
from app.db.models import Store, StoreMembership, User
from app.routes.auth import get_current_user, require_roles, store_owner_filter, store_owner_only_filter
from app.services.cloudinary_service import delete_image, upload_image
from app.services.image_validation import validate_image_content


router = APIRouter(
    prefix="/stores",
    tags=["Stores"],
)

STORE_UPLOAD_DIR = Path("uploads/stores")
MAX_LOGO_SIZE = 5 * 1024 * 1024
LOGO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _remove_store_logo(logo_url: str | None) -> None:
    if not logo_url:
        return

    if logo_url.startswith("/uploads/stores/"):
        path = STORE_UPLOAD_DIR / logo_url.rsplit("/", 1)[-1]
        if path.is_file():
            path.unlink()
        return

    delete_image(logo_url)


class StoreCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=10000)
    business_type: str = Field("clothing", max_length=100)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Store name must not be blank")
        return value


@router.post("/")
def create_store(
    data: StoreCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, "store_owner", "god")
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
        "logo_url": store.logo_url,
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
        .filter(store_owner_filter(current_user))
        .all()
    )

    return [
        {
            "id": store.id,
            "name": store.name,
            "description": store.description,
            "logo_url": store.logo_url,
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
            store_owner_filter(current_user),
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
        "logo_url": store.logo_url,
        "business_type": store.business_type,
        "business_type_label": get_business_type_label(store.business_type),
        "created_at": store.created_at,
    }


class StoreUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    business_type: str | None = Field(None, max_length=100)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Store name must not be blank")
        return value


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
            store_owner_only_filter(current_user),
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
        "logo_url": store.logo_url,
        "business_type": store.business_type,
        "business_type_label": get_business_type_label(store.business_type),
    }


@router.post("/{store_id}/logo")
async def upload_store_logo(
    store_id: int,
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            store_owner_only_filter(current_user),
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    if logo.content_type not in LOGO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type",
        )

    content = await logo.read(MAX_LOGO_SIZE + 1)

    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large",
        )

    try:
        validate_image_content(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc

    old_logo_url = store.logo_url

    try:
        logo_url = await run_in_threadpool(
            upload_image,
            content,
            public_id=f"store_{store.id}",
            folder="nava/stores",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload store logo",
        ) from exc

    store.logo_url = logo_url
    db.commit()
    db.refresh(store)

    if old_logo_url and old_logo_url.startswith("/uploads/stores/"):
        await run_in_threadpool(_remove_store_logo, old_logo_url)

    return {
        "store_id": store.id,
        "logo_url": store.logo_url,
        "message": "Store logo uploaded successfully",
    }


@router.delete("/{store_id}/logo")
def delete_store_logo(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            store_owner_only_filter(current_user),
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    logo_url = store.logo_url

    try:
        _remove_store_logo(logo_url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to remove store logo",
        ) from exc

    store.logo_url = None
    db.commit()

    return {
        "store_id": store.id,
        "logo_url": None,
        "message": "Store logo removed successfully",
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
            store_owner_only_filter(current_user),
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


class StoreAdminDecision(BaseModel):
    status: Literal["approved", "rejected"]


@router.get("/{store_id}/admin-requests")
def list_store_admin_requests(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.scalar(select(Store).where(Store.id == store_id, store_owner_only_filter(current_user)))
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    memberships = db.scalars(
        select(StoreMembership)
        .where(StoreMembership.store_id == store_id, StoreMembership.status == "pending")
        .order_by(StoreMembership.created_at)
    ).all()
    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "email": item.user.email,
            "name": " ".join(part for part in (item.user.first_name, item.user.last_name) if part),
            "is_verified": item.user.is_verified,
            "created_at": item.created_at,
        }
        for item in memberships
    ]


@router.patch("/{store_id}/admin-requests/{membership_id}")
def decide_store_admin_request(
    store_id: int,
    membership_id: int,
    payload: StoreAdminDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.scalar(select(Store).where(Store.id == store_id, store_owner_only_filter(current_user)))
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    membership = db.get(StoreMembership, membership_id)
    if membership is None or membership.store_id != store_id or membership.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin request not found")
    if payload.status == "approved" and not membership.user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email verification is required first")
    membership.status = payload.status
    user = membership.user
    approved_elsewhere = db.scalar(
        select(StoreMembership.id).where(
            StoreMembership.user_id == user.id,
            StoreMembership.status == "approved",
            StoreMembership.id != membership.id,
        )
    )
    user.approval_status = "active" if payload.status == "approved" or approved_elsewhere else "rejected"
    user.token_version += 1
    db.commit()
    return {"membership_id": membership.id, "status": membership.status, "user_approval_status": user.approval_status}
