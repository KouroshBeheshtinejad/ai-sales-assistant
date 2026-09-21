from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.routes.auth import get_optional_user
from app.services.payment_service import PaymentProviderNotConfigured, PaymentService


router = APIRouter(prefix="/payments", tags=["Payments"])


class VerifyPaymentRequest(BaseModel):
    authority: str = Field(..., min_length=1, max_length=255)


def payment_response(payment):
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "provider": payment.provider,
        "amount": str(payment.amount),
        "status": payment.status,
        "authority": payment.authority,
        "transaction_id": payment.transaction_id,
        "payment_url": (payment.payment_metadata or {}).get("payment_url"),
        "paid_at": payment.paid_at,
    }


@router.post("/orders/{order_id}", status_code=status.HTTP_201_CREATED)
def create_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        payment = PaymentService.create_payment(db, order_id, idempotency_key, current_user.id if current_user else None, None if current_user else guest_token)
    except PaymentProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Order not found" else 400, detail=str(exc)) from exc
    return payment_response(payment)


@router.post("/{payment_id}/verify")
def verify_payment(
    payment_id: int,
    payload: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
):
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        payment = PaymentService.verify_payment(db, payment_id, payload.authority, current_user.id if current_user else None, None if current_user else guest_token)
    except PaymentProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Payment not found" else 400, detail=str(exc)) from exc
    return payment_response(payment)