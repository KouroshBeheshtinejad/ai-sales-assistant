from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product, Store, User
from app.routes.auth import get_current_user, store_owner_filter
from app.services.cloudinary_service import delete_image, upload_image
from app.services.image_validation import validate_image_content
from app.services.audit_service import record_audit_log
from app.services.semantic_index import (
    SOURCE_PRODUCT,
    safely_discard_semantic_document,
    safely_sync_semantic_document,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

PRODUCT_UPLOAD_DIR = Path("uploads/products")
MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _remove_product_image(image_url: str | None) -> None:
    if not image_url:
        return

    if image_url.startswith("/uploads/products/"):
        filename = image_url.rsplit("/", 1)[-1]
        path = PRODUCT_UPLOAD_DIR / filename
        if path.is_file():
            path.unlink()
        return

    delete_image(image_url)


class ProductCreateRequest(BaseModel):
    store_id: int
    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=10000)
    price: float = Field(..., ge=0, le=9999999999.99, allow_inf_nan=False)
    stock: int = Field(0, ge=0, le=2147483647)
    size: str | None = Field(None, max_length=100)
    color: str | None = Field(None, max_length=100)
    attributes: dict[str, Any] | None = None
    category_ids: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Product name must not be blank")
        return value


def _product_response(product: Product, message: str | None = None):
    response = {
        "id": product.id,
        "product_id": product.id,
        "store_id": product.store_id,
        "name": product.name,
        "description": product.description,
        "image_url": product.image_url,
        "price": product.price,
        "stock": product.stock - product.reserved_stock,
        "reserved_stock": product.reserved_stock,
        "size": product.size,
        "color": product.color,
        "attributes": product.attributes or {},
        "category_ids": product.category_ids or [],
        "is_active": product.is_active,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }
    if message is not None:
        response["message"] = message
    return response


def _validated_category_ids(store: Store, category_ids: list[str]) -> list[str]:
    valid_ids = {item.get("id") for item in store.categories or []}
    unique_ids = list(dict.fromkeys(category_ids))
    if any(category_id not in valid_ids for category_id in unique_ids):
        raise HTTPException(status_code=422, detail="Product categories must belong to its store")
    return unique_ids


@router.post("/")
def create_product(
    data: ProductCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == data.store_id,
            store_owner_filter(current_user, "product.create"),
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    category_ids = _validated_category_ids(store, data.category_ids)

    product = Product(
        name=data.name,
        description=data.description,
        price=data.price,
        stock=data.stock,
        size=(data.attributes or {}).get("size", data.size),
        color=(data.attributes or {}).get("color", data.color),
        attributes=data.attributes or {},
        category_ids=category_ids,
        store_id=store.id,
    )

    db.add(product)
    db.flush()
    record_audit_log(
        db,
        actor=current_user,
        action="product.created",
        resource_type="product",
        resource_id=product.id,
        store_id=product.store_id,
        after_state={
            "name": product.name,
            "price": str(product.price),
            "stock": product.stock,
            "is_active": product.is_active,
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(product)
    safely_sync_semantic_document(db, product)

    return _product_response(product, "Product created successfully")


@router.post("/{product_id}/image")
async def upload_product_image(
    product_id: int,
    request: Request,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(
            Product.id == product_id,
            store_owner_filter(current_user, "product.update"),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if image.content_type not in IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type",
        )

    content = await image.read(MAX_IMAGE_SIZE + 1)

    if len(content) > MAX_IMAGE_SIZE:
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

    old_image_url = product.image_url

    try:
        image_url = await run_in_threadpool(
            upload_image,
            content,
            public_id=f"product_{product.id}",
            folder="nava/products",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload product image",
        ) from exc

    product.image_url = image_url
    record_audit_log(
        db,
        actor=current_user,
        action="product.image_changed",
        resource_type="product",
        resource_id=product.id,
        store_id=product.store_id,
        before_state={"has_image": bool(old_image_url)},
        after_state={"has_image": True},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(product)

    if old_image_url and old_image_url.startswith("/uploads/products/"):
        await run_in_threadpool(_remove_product_image, old_image_url)

    return _product_response(
        product,
        "Product image uploaded successfully",
    )


@router.delete("/{product_id}/image")
def delete_product_image(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(
            Product.id == product_id,
            store_owner_filter(current_user, "product.update"),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    image_url = product.image_url

    try:
        _remove_product_image(image_url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to remove product image",
        ) from exc

    product.image_url = None
    record_audit_log(
        db,
        actor=current_user,
        action="product.image_changed",
        resource_type="product",
        resource_id=product.id,
        store_id=product.store_id,
        before_state={"has_image": bool(image_url)},
        after_state={"has_image": False},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(product)

    return _product_response(
        product,
        "Product image removed successfully",
    )


@router.get("/")
def get_products(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            store_owner_filter(current_user, "product.read"),
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    products = (
        db.query(Product)
        .filter(Product.store_id == store.id)
        .all()
    )

    return [
        _product_response(product)
        for product in products
    ]


@router.get("/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(
            Product.id == product_id,
            store_owner_filter(current_user, "product.read"),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return _product_response(product)


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    price: float | None = Field(None, ge=0, le=9999999999.99, allow_inf_nan=False)
    stock: int | None = Field(None, ge=0, le=2147483647)
    size: str | None = Field(None, max_length=100)
    color: str | None = Field(None, max_length=100)
    attributes: dict[str, Any] | None = None
    category_ids: list[str] | None = Field(None, max_length=30)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Product name must not be blank")
        return value


@router.put("/{product_id}")
def update_product(
    product_id: int,
    data: ProductUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(
            Product.id == product_id,
            store_owner_filter(current_user, "product.update"),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    safely_discard_semantic_document(
        db,
        SOURCE_PRODUCT,
        product.id,
        product.store_id,
    )

    before_state = {
        "name": product.name,
        "price": str(product.price),
        "stock": product.stock,
        "reserved_stock": product.reserved_stock,
        "is_active": product.is_active,
    }

    update_data = data.model_dump(exclude_unset=True)

    if "category_ids" in update_data:
        if update_data["category_ids"] is None:
            update_data.pop("category_ids")
        else:
            update_data["category_ids"] = _validated_category_ids(product.store, update_data["category_ids"])

    if "attributes" in update_data and update_data["attributes"] is not None:
        update_data["size"] = update_data["attributes"].get(
            "size",
            update_data.get("size", product.size),
        )
        update_data["color"] = update_data["attributes"].get(
            "color",
            update_data.get("color", product.color),
        )

    for field, value in update_data.items():
        setattr(product, field, value)

    record_audit_log(
        db,
        actor=current_user,
        action="product.updated",
        resource_type="product",
        resource_id=product.id,
        store_id=product.store_id,
        before_state=before_state,
        after_state={
            "name": product.name,
            "price": str(product.price),
            "stock": product.stock,
            "reserved_stock": product.reserved_stock,
            "is_active": product.is_active,
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(product)
    safely_sync_semantic_document(db, product)

    return _product_response(
        product,
        "Product updated successfully",
    )


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(
            Product.id == product_id,
            store_owner_filter(current_user, "product.delete"),
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    image_url = product.image_url
    before_state = {
        "name": product.name,
        "price": str(product.price),
        "stock": product.stock,
        "reserved_stock": product.reserved_stock,
        "is_active": product.is_active,
    }

    safely_discard_semantic_document(
        db,
        SOURCE_PRODUCT,
        product.id,
        product.store_id,
    )

    try:
        _remove_product_image(image_url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to remove product image",
        ) from exc

    db.delete(product)
    record_audit_log(
        db,
        actor=current_user,
        action="product.deleted",
        resource_type="product",
        resource_id=product_id,
        store_id=product.store_id,
        before_state=before_state,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return {
        "message": "Product deleted successfully",
        "product_id": product_id,
    }
