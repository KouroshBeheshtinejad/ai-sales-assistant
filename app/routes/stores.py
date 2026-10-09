import os
import hmac
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.business_types import get_business_type_label, normalize_business_type
from app.core.currencies import SUPPORTED_STORE_CURRENCIES
from app.core.csrf import require_csrf_header
from app.db.database import get_db
from app.db.models import Order, Product, Store, StoreMembership, StorePaymentAccount, User
from app.routes.auth import get_current_user, require_roles, store_owner_filter, store_owner_only_filter
from app.services.cloudinary_service import delete_image, upload_image
from app.services.image_validation import validate_image_content
from app.services.audit_service import record_audit_log
from app.services.payment_service import payment_provider_registry
from app.security.payment_credentials import (
    PaymentCredentialError,
    decrypt_payment_credential,
    encrypt_payment_credential,
    fingerprint_payment_credential,
)
from app.security.policies import store_access


router = APIRouter(
    prefix="/stores",
    tags=["Stores"],
)


def _store_location(store: Store) -> dict[str, float] | None:
    if store.latitude is None or store.longitude is None:
        return None
    return {"lat": float(store.latitude), "lng": float(store.longitude)}


class StoreLocationInput(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

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
    categories: list[dict[str, str]] = Field(default_factory=list, max_length=30)
    primary_color: str = Field("#0d8a85", pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str = Field("#f2f7f6", pattern=r"^#[0-9a-fA-F]{6}$")
    contact_phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=2000)
    location: StoreLocationInput | None = None
    store_hours: str | None = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Store name must not be blank")
        return value

    @field_validator("categories")
    @classmethod
    def categories_must_have_unique_ids_and_names(cls, value: list[dict[str, str]]) -> list[dict[str, str]]:
        cleaned = []
        ids = set()
        names = set()
        for category in value:
            category_id = category.get("id", "").strip()
            name = category.get("name", "").strip()
            if not category_id or not name or len(name) > 60:
                raise ValueError("Categories need an id and a name of at most 60 characters")
            if category_id in ids or name.casefold() in names:
                raise ValueError("Category ids and names must be unique")
            ids.add(category_id)
            names.add(name.casefold())
            cleaned.append({"id": category_id, "name": name})
        return cleaned

    @field_validator("contact_phone", "address", "store_hours")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


@router.post("/")
def create_store(
    data: StoreCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, "store_owner", "god")
    normalized_business_type = normalize_business_type(data.business_type)
    store = Store(
        name=data.name,
        description=data.description,
        business_type=normalized_business_type,
        categories=data.categories,
        primary_color=data.primary_color.lower(),
        secondary_color=data.secondary_color.lower(),
        contact_phone=data.contact_phone,
        address=data.address,
        latitude=data.location.lat if data.location else None,
        longitude=data.location.lng if data.location else None,
        store_hours=data.store_hours,
        owner_id=current_user.id,
    )

    db.add(store)
    db.flush()
    record_audit_log(
        db,
        actor=current_user,
        action="store.created",
        resource_type="store",
        resource_id=store.id,
        store_id=store.id,
        after_state={
            "name": store.name,
            "business_type": store.business_type,
            "categories": store.categories or [],
            "primary_color": store.primary_color,
            "secondary_color": store.secondary_color,
        },
        ip_address=request.client.host if request.client else None,
    )
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
        "categories": store.categories or [],
        "primary_color": store.primary_color,
        "secondary_color": store.secondary_color,
        "contact_phone": store.contact_phone,
        "address": store.address,
        "location": _store_location(store),
        "store_hours": store.store_hours,
        "country_code": store.country_code,
        "currency": store.currency,
        "payment_provider": store.payment_provider,
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
            "categories": store.categories or [],
            "primary_color": store.primary_color,
            "secondary_color": store.secondary_color,
            "contact_phone": store.contact_phone,
            "address": store.address,
            "location": _store_location(store),
            "store_hours": store.store_hours,
            "country_code": store.country_code,
            "currency": store.currency,
            "payment_provider": store.payment_provider,
            "created_at": store.created_at,
            **(store_access(db, current_user, store.id) or {}),
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
        "categories": store.categories or [],
        "primary_color": store.primary_color,
        "secondary_color": store.secondary_color,
        "contact_phone": store.contact_phone,
        "address": store.address,
        "location": _store_location(store),
        "store_hours": store.store_hours,
        "country_code": store.country_code,
        "currency": store.currency,
        "payment_provider": store.payment_provider,
        "created_at": store.created_at,
        **(store_access(db, current_user, store.id) or {}),
    }


class StoreUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=10000)
    business_type: str | None = Field(None, max_length=100)
    categories: list[dict[str, str]] | None = Field(None, max_length=30)
    primary_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    contact_phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=2000)
    location: StoreLocationInput | None = None
    store_hours: str | None = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Store name must not be blank")
        return value

    @field_validator("categories")
    @classmethod
    def categories_must_have_unique_ids_and_names(cls, value: list[dict[str, str]] | None) -> list[dict[str, str]] | None:
        if value is None:
            return None
        return StoreCreateRequest.categories_must_have_unique_ids_and_names(value)

    @field_validator("contact_phone", "address", "store_hours")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class StorePaymentSettingsRequest(BaseModel):
    country_code: str = Field(..., pattern=r"^[A-Za-z]{2}$")
    currency: str = Field(..., pattern=r"^[A-Za-z]{3}$")
    provider: Literal[
        "disabled",
        "zarinpal",
        "stripe_connect",
        "paypal_multiparty",
        "adyen_platforms",
        "mollie_connect",
        "mock",
    ]
    external_account_id: str | None = Field(None, max_length=255)
    credential_reference: str | None = Field(None, max_length=64, pattern=r"^[A-Z0-9_]+$")
    merchant_id: str | None = None

    @field_validator("country_code", "currency")
    @classmethod
    def uppercase_codes(cls, value: str) -> str:
        return value.upper()

    @field_validator("external_account_id")
    @classmethod
    def clean_account_reference(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None

    @field_validator("credential_reference")
    @classmethod
    def clean_credential_reference(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None

    @model_validator(mode="after")
    def require_provider_account(self):
        if self.provider != "zarinpal" and self.credential_reference:
            raise ValueError("Credential references are only used for ZarinPal")
        if self.provider == "zarinpal" and self.currency not in {"IRT", "IRR"}:
            raise ValueError("ZarinPal supports only IRT and IRR Store currencies")
        return self


def _payment_settings_response(store: Store, account: StorePaymentAccount | None) -> dict:
    provider = store.payment_provider
    account_status = account.status if account is not None else "not_configured"
    if provider == "zarinpal" and account is not None and not account.credential_fingerprint:
        account_status = "pending"
    return {
        "store_id": store.id,
        "country_code": store.country_code,
        "currency": store.currency,
        "provider": provider,
        "status": account_status,
        "adapter_available": payment_provider_registry.has_adapter(provider),
        "account_configured": bool(account and (account.external_account_id or account.credential_reference or account.credential_ciphertext)),
    }


def _ensure_unique_zarinpal_credential(db: Session, store_id: int, merchant_id: str) -> None:
    other_accounts = db.scalars(
        select(StorePaymentAccount).where(
            StorePaymentAccount.provider == "zarinpal",
            StorePaymentAccount.store_id != store_id,
        )
    ).all()
    for other_account in other_accounts:
        try:
            other_merchant_id = (
                decrypt_payment_credential(other_account.credential_ciphertext)
                if other_account.credential_ciphertext
                else os.getenv(f"PAYMENT_SECRET_{other_account.credential_reference}", "")
            )
        except PaymentCredentialError as exc:
            raise HTTPException(status_code=503, detail="An existing Store credential must be reconfigured") from exc
        if other_merchant_id and hmac.compare_digest(merchant_id, other_merchant_id):
            raise HTTPException(status_code=409, detail="This ZarinPal Merchant ID is already assigned to another Store")


@router.get("/{store_id}/payment-settings")
def get_store_payment_settings(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.scalar(select(Store).where(Store.id == store_id, store_owner_only_filter(current_user)))
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    account = db.scalar(
        select(StorePaymentAccount).where(
            StorePaymentAccount.store_id == store.id,
            StorePaymentAccount.provider == store.payment_provider,
        )
    )
    return _payment_settings_response(store, account)


@router.put("/{store_id}/payment-settings")
def update_store_payment_settings(
    store_id: int,
    data: StorePaymentSettingsRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.scalar(
        select(Store)
        .where(Store.id == store_id, store_owner_only_filter(current_user))
        .with_for_update()
    )
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    if data.currency not in SUPPORTED_STORE_CURRENCIES and data.currency != store.currency:
        raise HTTPException(status_code=422, detail="Unsupported Store currency")
    if data.provider == "mock" and os.getenv("APP_ENV", "development").strip().casefold() in {"production", "prod"}:
        raise HTTPException(status_code=400, detail="Mock payments are disabled in production")
    if store.currency != data.currency and db.query(Order.id).filter(Order.store_id == store.id).first():
        raise HTTPException(status_code=409, detail="Store currency cannot change after an order exists")
    if data.provider == "zarinpal" and not os.getenv("PAYMENT_CALLBACK_URL", "").strip():
        raise HTTPException(status_code=503, detail="PAYMENT_CALLBACK_URL is required for ZarinPal")
    account = None
    if data.provider != "disabled":
        account = db.scalar(
            select(StorePaymentAccount)
            .where(StorePaymentAccount.store_id == store.id, StorePaymentAccount.provider == data.provider)
            .with_for_update()
        )
        credential_reference = data.credential_reference or (account.credential_reference if account else None)
        external_account_id = data.external_account_id or (account.external_account_id if account else None)
        credential_ciphertext = account.credential_ciphertext if account else None
        credential_fingerprint = None
        if data.provider == "zarinpal":
            resolved_merchant_id = None
            if data.merchant_id and data.credential_reference:
                raise HTTPException(status_code=422, detail="Provide either a Merchant ID or a server credential reference")
            if data.merchant_id:
                merchant_id = data.merchant_id.strip()
                try:
                    if str(uuid.UUID(merchant_id)) != merchant_id.casefold():
                        raise ValueError("invalid format")
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail="Invalid ZarinPal Merchant ID format") from exc
                try:
                    credential_ciphertext = encrypt_payment_credential(merchant_id)
                except PaymentCredentialError as exc:
                    raise HTTPException(status_code=503, detail=str(exc)) from exc
                credential_reference = None
                resolved_merchant_id = merchant_id
            elif data.credential_reference:
                credential_reference = data.credential_reference
                credential_ciphertext = None
                resolved_merchant_id = os.getenv(f"PAYMENT_SECRET_{credential_reference}", "").strip()
                if not resolved_merchant_id:
                    raise HTTPException(status_code=503, detail="The referenced ZarinPal credential is not available")
            elif not credential_ciphertext and not credential_reference:
                raise HTTPException(status_code=422, detail="A ZarinPal Merchant ID is required")
            elif credential_ciphertext:
                try:
                    resolved_merchant_id = decrypt_payment_credential(credential_ciphertext)
                except PaymentCredentialError as exc:
                    raise HTTPException(status_code=503, detail=str(exc)) from exc
            elif credential_reference:
                resolved_merchant_id = os.getenv(f"PAYMENT_SECRET_{credential_reference}", "").strip()
                if not resolved_merchant_id:
                    raise HTTPException(status_code=503, detail="The referenced ZarinPal credential is not available")
            if resolved_merchant_id:
                _ensure_unique_zarinpal_credential(db, store.id, resolved_merchant_id)
                try:
                    credential_fingerprint = fingerprint_payment_credential(resolved_merchant_id)
                except PaymentCredentialError as exc:
                    raise HTTPException(status_code=503, detail=str(exc)) from exc
        elif not external_account_id:
            raise HTTPException(status_code=422, detail="An external provider account ID is required")
        adapter_available = payment_provider_registry.has_adapter(data.provider)
        if account is None:
            account = StorePaymentAccount(
                store_id=store.id,
                provider=data.provider,
                external_account_id=external_account_id,
                credential_reference=credential_reference,
                credential_ciphertext=credential_ciphertext,
                credential_fingerprint=credential_fingerprint,
                status="active" if adapter_available else "pending",
                country_code=data.country_code,
                currency=data.currency,
            )
            db.add(account)
        else:
            account.external_account_id = external_account_id
            account.credential_reference = credential_reference
            account.credential_ciphertext = credential_ciphertext
            account.credential_fingerprint = credential_fingerprint
            account.status = "active" if adapter_available else "pending"
            account.country_code = data.country_code
            account.currency = data.currency

    before_state = {
        "country_code": store.country_code,
        "currency": store.currency,
        "payment_provider": store.payment_provider,
    }
    store.country_code = data.country_code
    store.currency = data.currency
    store.payment_provider = data.provider
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This ZarinPal Merchant ID is already assigned to another Store") from exc
    record_audit_log(
        db,
        actor=current_user,
        action="store.payment_settings_changed",
        resource_type="store",
        resource_id=store.id,
        store_id=store.id,
        before_state=before_state,
        after_state={
            "country_code": store.country_code,
            "currency": store.currency,
            "payment_provider": store.payment_provider,
            "account_status": account.status if account else "not_configured",
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(store)
    return _payment_settings_response(store, account)


@router.put("/{store_id}")
def update_store(
    store_id: int,
    data: StoreUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            store_owner_filter(current_user, "store.update"),
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    before_state = {
        "name": store.name,
        "description": store.description,
        "business_type": store.business_type,
        "categories": store.categories or [],
        "primary_color": store.primary_color,
        "secondary_color": store.secondary_color,
        "contact_phone": store.contact_phone,
        "address": store.address,
        "location": _store_location(store),
        "store_hours": store.store_hours,
    }
    update_data = data.model_dump(exclude_unset=True)

    if "location" in update_data:
        location = update_data.pop("location")
        store.latitude = location["lat"] if location else None
        store.longitude = location["lng"] if location else None

    if update_data.get("categories") is None:
        update_data.pop("categories", None)
    for color_field in ("primary_color", "secondary_color"):
        if update_data.get(color_field) is None:
            update_data.pop(color_field, None)
        else:
            update_data[color_field] = update_data[color_field].lower()

    if "business_type" in update_data and update_data["business_type"] is not None:
        update_data["business_type"] = normalize_business_type(update_data["business_type"])

    for field, value in update_data.items():
        setattr(store, field, value)

    if "categories" in update_data:
        valid_category_ids = {category["id"] for category in store.categories or []}
        for product in db.query(Product).filter(Product.store_id == store.id).all():
            product.category_ids = [category_id for category_id in product.category_ids or [] if category_id in valid_category_ids]

    record_audit_log(
        db,
        actor=current_user,
        action="store.updated",
        resource_type="store",
        resource_id=store.id,
        store_id=store.id,
        before_state=before_state,
        after_state={
            "name": store.name,
            "description": store.description,
            "business_type": store.business_type,
            "categories": store.categories or [],
            "primary_color": store.primary_color,
            "secondary_color": store.secondary_color,
            "contact_phone": store.contact_phone,
            "address": store.address,
            "location": _store_location(store),
            "store_hours": store.store_hours,
        },
        ip_address=request.client.host if request.client else None,
    )
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
        "categories": store.categories or [],
        "primary_color": store.primary_color,
        "secondary_color": store.secondary_color,
        "contact_phone": store.contact_phone,
        "address": store.address,
        "location": _store_location(store),
        "store_hours": store.store_hours,
    }


@router.post("/{store_id}/logo")
async def upload_store_logo(
    store_id: int,
    request: Request,
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            store_owner_filter(current_user, "store.update"),
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
    record_audit_log(
        db,
        actor=current_user,
        action="store.logo_changed",
        resource_type="store",
        resource_id=store.id,
        store_id=store.id,
        before_state={"has_logo": bool(old_logo_url)},
        after_state={"has_logo": True},
        ip_address=request.client.host if request.client else None,
    )
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            store_owner_filter(current_user, "store.update"),
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
    record_audit_log(
        db,
        actor=current_user,
        action="store.logo_changed",
        resource_type="store",
        resource_id=store.id,
        store_id=store.id,
        before_state={"has_logo": bool(logo_url)},
        after_state={"has_logo": False},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return {
        "store_id": store.id,
        "logo_url": None,
        "message": "Store logo removed successfully",
    }


@router.delete("/{store_id}")
def delete_store(
    store_id: int,
    request: Request,
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

    record_audit_log(
        db,
        actor=current_user,
        action="store.deleted",
        resource_type="store",
        resource_id=store.id,
        store_id=store.id,
        before_state={"name": store.name, "business_type": store.business_type, "owner_id": store.owner_id},
        ip_address=request.client.host if request.client else None,
    )
    db.delete(store)
    db.commit()

    return {
        "message": "Store deleted successfully",
        "store_id": store_id,
    }


class StoreAdminDecision(BaseModel):
    status: Literal["approved", "rejected"]


class StoreMemberCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    role: Literal["store_admin", "store_manager", "store_viewer"]


class StoreMemberUpdate(BaseModel):
    role: Literal["store_admin", "store_manager", "store_viewer"] | None = None
    status: Literal["approved", "rejected", "suspended", "revoked"] | None = None


def _member_store_or_404(db: Session, user: User, store_id: int, permission: str) -> Store:
    store = db.scalar(
        select(Store).where(Store.id == store_id, store_owner_filter(user, permission))
    )
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


def _membership_response(membership: StoreMembership) -> dict:
    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "email": membership.user.email,
        "name": " ".join(part for part in (membership.user.first_name, membership.user.last_name) if part),
        "role": membership.role,
        "status": membership.status,
        "created_at": membership.created_at,
    }


@router.get("/{store_id}/members")
def list_store_members(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _member_store_or_404(db, current_user, store_id, "member.read")
    memberships = db.scalars(
        select(StoreMembership)
        .where(StoreMembership.store_id == store_id)
        .order_by(StoreMembership.created_at)
    ).all()
    return [_membership_response(item) for item in memberships]


@router.post("/{store_id}/members", status_code=status.HTTP_201_CREATED)
def add_store_member(
    store_id: int,
    payload: StoreMemberCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_header),
):
    _member_store_or_404(db, current_user, store_id, "member.invite")
    email = payload.email.strip().casefold()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account must register before being added")
    existing = db.scalar(
        select(StoreMembership).where(
            StoreMembership.store_id == store_id,
            StoreMembership.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership already exists")
    membership_status = "approved" if user.is_verified and user.approval_status == "active" else "pending"
    membership = StoreMembership(
        store_id=store_id,
        user_id=user.id,
        role=payload.role,
        status=membership_status,
    )
    db.add(membership)
    db.flush()
    user.token_version += 1
    record_audit_log(
        db,
        actor=current_user,
        action="membership.invited",
        resource_type="store_membership",
        resource_id=membership.id,
        store_id=store_id,
        after_state={"user_id": user.id, "role": membership.role, "status": membership.status},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(membership)
    return _membership_response(membership)


@router.patch("/{store_id}/members/{membership_id}")
def update_store_member(
    store_id: int,
    membership_id: int,
    payload: StoreMemberUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf_header),
):
    if payload.role is None and payload.status is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A role or status change is required")
    if payload.status in {"approved", "rejected"}:
        permission = "member.approve"
    elif payload.status in {"suspended", "revoked"}:
        permission = "member.remove"
    else:
        permission = "member.update"
    store = _member_store_or_404(db, current_user, store_id, permission)
    membership = db.get(StoreMembership, membership_id)
    if membership is None or membership.store_id != store.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    if membership.user_id == store.owner_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Store owner membership cannot be changed")
    if membership.status not in {"approved", "pending", "suspended", "revoked", "rejected"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership state cannot be changed")
    if payload.status == "approved" and membership.status not in {"pending", "suspended", "revoked"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership cannot be approved from this state")
    if payload.status == "rejected" and membership.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership is not pending")
    if payload.status == "approved" and not membership.user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email verification is required first")

    before_state = {"role": membership.role, "status": membership.status}
    if payload.role is not None:
        membership.role = payload.role
    if payload.status is not None:
        membership.status = payload.status
        if membership.user.role == "store_admin":
            membership.user.approval_status = "active" if payload.status == "approved" else membership.user.approval_status
    membership.user.token_version += 1
    action = "membership.role_changed" if payload.role is not None else f"membership.{payload.status}"
    record_audit_log(
        db,
        actor=current_user,
        action=action,
        resource_type="store_membership",
        resource_id=membership.id,
        store_id=store_id,
        before_state=before_state,
        after_state={"role": membership.role, "status": membership.status},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(membership)
    return _membership_response(membership)


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
    request: Request,
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
    previous_membership_status = membership.status
    previous_approval_status = membership.user.approval_status
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
    record_audit_log(
        db,
        actor=current_user,
        action=f"membership.{payload.status}",
        resource_type="store_membership",
        resource_id=membership.id,
        store_id=store_id,
        before_state={
            "status": previous_membership_status,
            "user_approval_status": previous_approval_status,
        },
        after_state={
            "status": membership.status,
            "user_approval_status": user.approval_status,
            "role": membership.role,
        },
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"membership_id": membership.id, "status": membership.status, "user_approval_status": user.approval_status}
