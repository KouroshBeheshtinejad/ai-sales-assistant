from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Payment, User
from app.routes.auth import get_current_user, get_optional_user
from app.services.payment_service import PaymentProviderNotConfigured, PaymentService


router = APIRouter(prefix="/payments", tags=["Payments"])


class VerifyPaymentRequest(BaseModel):
    authority: str = Field(..., min_length=1, max_length=255)


class RefundPaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)


def payment_response(payment):
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "provider": payment.provider,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "authority": payment.authority,
        "transaction_id": payment.transaction_id,
        "payment_url": (payment.payment_metadata or {}).get("payment_url"),
        "paid_at": payment.paid_at,
    }


def transaction_response(transaction):
    return {
        "id": transaction.id,
        "payment_id": transaction.payment_id,
        "type": transaction.transaction_type,
        "status": transaction.status,
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "provider_reference": transaction.provider_reference,
        "created_at": transaction.created_at,
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


@router.post("/{payment_id}/reconcile")
def reconcile_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
):
    if current_user is None and not guest_token:
        raise HTTPException(status_code=401, detail="Guest token is required")
    try:
        payment = PaymentService.reconcile_payment(
            db,
            payment_id,
            current_user.id if current_user else None,
            None if current_user else guest_token,
        )
    except PaymentProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Payment not found" else 400, detail=str(exc)) from exc
    return payment_response(payment)


@router.post("/{payment_id}/refunds", status_code=status.HTTP_201_CREATED)
def refund_payment(
    payment_id: int,
    payload: RefundPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    try:
        transaction = PaymentService.refund_payment(
            db,
            payment_id,
            payload.amount,
            idempotency_key,
            current_user.id,
        )
    except PaymentProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Payment not found" else 400, detail=str(exc)) from exc
    return transaction_response(transaction)


@router.get("/callback", include_in_schema=False)
def payment_callback(request: Request, db: Session = Depends(get_db)):
    authority = request.query_params.get("Authority") or request.query_params.get("authority")
    raw_status = request.query_params.get("Status") or ""
    payment_status = raw_status.casefold()
    if not authority:
        return RedirectResponse("/payment-result?payment=failed", status_code=303)
    payment = db.scalar(
        select(Payment)
        .where(Payment.authority == authority)
    )
    if payment is None:
        return RedirectResponse("/payment-result?payment=failed", status_code=303)

    order = payment.order
    if payment_status != "ok":
        try:
            payment = PaymentService.reconcile_payment(
                db,
                payment.id,
                order.user_id,
                order.guest_token,
            )
        except (PaymentProviderNotConfigured, ValueError):
            pass
        if payment.status == "paid":
            return RedirectResponse(
                f"/payment-result?payment=success&store_id={order.store_id}&order_id={order.id}",
                status_code=303,
            )
        return RedirectResponse(
            f"/payment-result?payment=failed&store_id={order.store_id}&payment_id={payment.id}",
            status_code=303,
        )

    if payment_status == "ok":
        try:
            PaymentService.verify_payment(
                db,
                payment.id,
                authority,
                order.user_id,
                order.guest_token,
            )
        except (PaymentProviderNotConfigured, ValueError):
            return RedirectResponse("/payment-result?payment=failed", status_code=303)
        return RedirectResponse(
            f"/payment-result?payment=success&store_id={order.store_id}&order_id={order.id}",
            status_code=303,
        )
    return RedirectResponse("/payment-result?payment=failed", status_code=303)