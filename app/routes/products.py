from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product, Store, User
from app.routes.auth import get_current_user
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
    if not image_url or not image_url.startswith("/uploads/products/"):
        return
    filename = image_url.rsplit("/", 1)[-1]
    path = PRODUCT_UPLOAD_DIR / filename
    if path.is_file():
        path.unlink()


class ProductCreateRequest(BaseModel):
    store_id: int
    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=10000)
    price: float = Field(..., ge=0, le=9999999999.99, allow_inf_nan=False)
    stock: int = Field(0, ge=0, le=2147483647)
    size: str | None = Field(None, max_length=100)
    color: str | None = Field(None, max_length=100)
    attributes: dict[str, Any] | None = None

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
        "stock": product.stock,
        "reserved_stock": product.reserved_stock,
        "size": product.size,
        "color": product.color,
        "attributes": product.attributes or {},
        "is_active": product.is_active,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }
    if message is not None:
        response["message"] = message
    return response


@router.post("/")
def create_product(
    data: ProductCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == data.store_id,
            Store.owner_id == current_user.id,
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    product = Product(
        name=data.name,
        description=data.description,
        price=data.price,
        stock=data.stock,
        size=(data.attributes or {}).get("size", data.size),
        color=(data.attributes or {}).get("color", data.color),
        attributes=data.attributes or {},
        store_id=store.id,
    )

    db.add(product)
    db.commit()
    db.refresh(product)
    safely_sync_semantic_document(db, product)

    return _product_response(product, "Product created successfully")


@router.post("/{product_id}/image")
async def upload_product_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(Product.id == product_id, Store.owner_id == current_user.id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    extension = IMAGE_TYPES.get(image.content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type")

    content = await image.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image is too large")

    PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (PRODUCT_UPLOAD_DIR / filename).write_bytes(content)
    _remove_product_image(product.image_url)
    product.image_url = f"/uploads/products/{filename}"
    db.commit()
    db.refresh(product)
    return _product_response(product, "Product image uploaded successfully")


@router.delete("/{product_id}/image")
def delete_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(Product.id == product_id, Store.owner_id == current_user.id)
        .first()
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    _remove_product_image(product.image_url)
    product.image_url = None
    db.commit()
    db.refresh(product)
    return _product_response(product, "Product image removed successfully")

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
            Store.owner_id == current_user.id,
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
            Store.owner_id == current_user.id,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(
            Product.id == product_id,
            Store.owner_id == current_user.id,
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    safely_discard_semantic_document(db, SOURCE_PRODUCT, product.id, product.store_id)
    update_data = data.model_dump(exclude_unset=True)

    if "attributes" in update_data and update_data["attributes"] is not None:
        update_data["size"] = update_data["attributes"].get(
            "size", update_data.get("size", product.size)
        )
        update_data["color"] = update_data["attributes"].get(
            "color", update_data.get("color", product.color)
        )

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    safely_sync_semantic_document(db, product)

    return _product_response(product, "Product updated successfully")

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .join(Store)
        .filter(
            Product.id == product_id,
            Store.owner_id == current_user.id,
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    safely_discard_semantic_document(db, SOURCE_PRODUCT, product.id, product.store_id)
    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted successfully",
        "product_id": product_id,
    }
