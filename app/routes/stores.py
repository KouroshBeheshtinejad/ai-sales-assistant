from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.business_types import get_business_type_label, normalize_business_type
from app.db.database import get_db
from app.db.models import Store, User
from app.routes.auth import get_current_user
from app.services.cloudinary_service import delete_image, upload_image


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
        .filter(Store.owner_id == current_user.id)
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
            Store.owner_id == current_user.id,
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

    old_logo_url = store.logo_url

    try:
        logo_url = upload_image(
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
        _remove_store_logo(old_logo_url)

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
            Store.owner_id == current_user.id,
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
