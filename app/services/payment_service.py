from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Order, Payment, Product
from app.services.notification_service import notify_payment_success


class PaymentProvider(Protocol):
    name: str

    def create_payment(self, *, amount: Decimal, order_id: int, callback_url: str | None = None) -> dict: ...
    def verify_payment(self, *, amount: Decimal, authority: str) -> dict: ...
    def get_status(self, *, authority: str) -> str: ...
    def refund(self, *, transaction_id: str, amount: Decimal) -> dict: ...


class PaymentProviderNotConfigured(RuntimeError):
    pass


class MockPaymentProvider:
    name = "mock"

    def create_payment(self, *, amount: Decimal, order_id: int, callback_url: str | None = None) -> dict:
        return {"authority": f"mock-{secrets.token_urlsafe(18)}", "payment_url": None}

    def verify_payment(self, *, amount: Decimal, authority: str) -> dict:
        if not authority.startswith("mock-"):
            raise ValueError("Invalid payment authority")
        return {"transaction_id": f"mock-tx-{secrets.token_urlsafe(12)}"}

    def get_status(self, *, authority: str) -> str:
        return "pending" if authority.startswith("mock-") else "failed"

    def refund(self, *, transaction_id: str, amount: Decimal) -> dict:
        if not transaction_id.startswith("mock-tx-"):
            raise ValueError("Invalid transaction")
        return {"status": "refunded"}


class UnconfiguredPaymentProvider:
    name = "unconfigured"

    def _raise(self):
        raise PaymentProviderNotConfigured("Payment provider is not configured")

    def create_payment(self, **kwargs):
        self._raise()

    def verify_payment(self, **kwargs):
        self._raise()

    def get_status(self, **kwargs):
        self._raise()

    def refund(self, **kwargs):
        self._raise()


def get_payment_provider() -> PaymentProvider:
    provider = os.getenv("PAYMENT_PROVIDER", "disabled").strip().casefold()
    if provider == "mock":
        if os.getenv("APP_ENV", "development").strip().casefold() in {"production", "prod"}:
            raise PaymentProviderNotConfigured("Mock payment provider is disabled in production")
        return MockPaymentProvider()
    return UnconfiguredPaymentProvider()


class PaymentService:
    @staticmethod
    def create_payment(
        db: Session,
        order_id: int,
        idempotency_key: str,
        user_id: int | None = None,
        guest_token: str | None = None,
        callback_url: str | None = None,
    ) -> Payment:
        order = db.scalar(select(Order).where(Order.id == order_id))
        if order is None or (user_id is not None and order.user_id != user_id) or (user_id is None and order.guest_token != guest_token):
            raise ValueError("Order not found")
        if order.status != "pending":
            raise ValueError("Only pending orders can be paid")

        existing = db.scalar(select(Payment).where(Payment.order_id == order_id, Payment.idempotency_key == idempotency_key))
        if existing is not None:
            return existing
        if any(payment.status == "paid" for payment in order.payments):
            raise ValueError("Order is already paid")

        provider = get_payment_provider()
        details = provider.create_payment(amount=Decimal(str(order.total_amount)), order_id=order.id, callback_url=callback_url)
        payment = Payment(
            order_id=order.id,
            provider=provider.name,
            amount=order.total_amount,
            status="pending",
            authority=details.get("authority"),
            idempotency_key=idempotency_key,
            payment_metadata={"payment_url": details.get("payment_url")},
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def verify_payment(db: Session, payment_id: int, authority: str, user_id: int | None = None, guest_token: str | None = None) -> Payment:
        payment = db.scalar(
            select(Payment)
            .options(joinedload(Payment.order))
            .where(Payment.id == payment_id)
            .with_for_update()
        )
        if payment is None or (user_id is not None and payment.order.user_id != user_id) or (user_id is None and payment.order.guest_token != guest_token):
            raise ValueError("Payment not found")
        if payment.authority != authority:
            raise ValueError("Invalid payment authority")
        if payment.status == "paid":
            return payment

        provider = get_payment_provider()
        result = provider.verify_payment(amount=payment.amount, authority=authority)
        payment.status = "paid"
        payment.order.status = "confirmed"
        payment.transaction_id = result["transaction_id"]
        payment.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
        for item in payment.order.items:
            if item.product_id is not None:
                product = db.get(Product, item.product_id)
                if product is not None:
                    product.reserved_stock = max(0, product.reserved_stock - item.quantity)
        db.commit()
        db.refresh(payment)
        notify_payment_success(payment.order, payment.transaction_id)
        return payment