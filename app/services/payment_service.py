from __future__ import annotations

import os
import secrets
import json
import logging
from urllib import request as urllib_request
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.db.models import Order, Payment, Product
from app.services.notification_service import notify_payment_success
from app.services.order_service import OrderService


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


class ZarinpalPaymentProvider:
    name = "zarinpal"

    def __init__(self) -> None:
        try:
            self.merchant_id = os.environ["PAYMENT_MERCHANT_ID"]
            self.callback_url = os.environ["PAYMENT_CALLBACK_URL"]
        except KeyError as exc:
            raise PaymentProviderNotConfigured("Zarinpal payment configuration is incomplete") from exc
        self.base_url = os.getenv(
            "PAYMENT_API_URL",
            "https://payment.zarinpal.com/pg/v4/payment",
        ).rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib_request.Request(
            f"{self.base_url}/{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(request, timeout=15) as response:
            return json.loads(response.read())

    def create_payment(self, *, amount: Decimal, order_id: int, callback_url: str | None = None) -> dict:
        result = self._post(
            "request.json",
            {
                "merchant_id": self.merchant_id,
                "amount": int(amount),
                "callback_url": callback_url or self.callback_url,
                "description": f"NAVA order {order_id}",
            },
        )
        data = result.get("data") or {}
        if result.get("code") != 100 or not data.get("authority"):
            raise PaymentProviderNotConfigured("Payment gateway rejected the payment request")
        authority = data["authority"]
        return {
            "authority": authority,
            "payment_url": f"https://www.zarinpal.com/pg/StartPay/{authority}",
        }

    def verify_payment(self, *, amount: Decimal, authority: str) -> dict:
        result = self._post(
            "verify.json",
            {
                "merchant_id": self.merchant_id,
                "amount": int(amount),
                "authority": authority,
            },
        )
        data = result.get("data") or {}
        if result.get("code") not in {100, 101} or not data.get("ref_id"):
            raise ValueError("Payment verification failed")
        return {"transaction_id": str(data["ref_id"])}

    def get_status(self, *, authority: str) -> str:
        return "pending"

    def refund(self, *, transaction_id: str, amount: Decimal) -> dict:
        raise PaymentProviderNotConfigured("Zarinpal refund requires merchant-specific settlement configuration")

def get_payment_provider() -> PaymentProvider:
    provider = os.getenv("PAYMENT_PROVIDER", "disabled").strip().casefold()
    if provider == "mock":
        if os.getenv("APP_ENV", "development").strip().casefold() in {"production", "prod"}:
            raise PaymentProviderNotConfigured("Mock payment provider is disabled in production")
        return MockPaymentProvider()
    if provider == "zarinpal":
        return ZarinpalPaymentProvider()
    return UnconfiguredPaymentProvider()


class PaymentService:
    logger = logging.getLogger(__name__)
    @staticmethod
    def create_payment(
        db: Session,
        order_id: int,
        idempotency_key: str,
        user_id: int | None = None,
        guest_token: str | None = None,
        callback_url: str | None = None,
    ) -> Payment:
        order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
        if order is None or (user_id is not None and order.user_id != user_id) or (user_id is None and order.guest_token != guest_token):
            raise ValueError("Order not found")
        if order.status != "pending":
            raise ValueError("Only pending orders can be paid")

        existing = db.scalar(select(Payment).where(Payment.order_id == order_id, Payment.idempotency_key == idempotency_key))
        if existing is not None:
            return existing
        if any(payment.status == "paid" for payment in order.payments):
            raise ValueError("Order is already paid")
        pending_payment = db.scalar(
            select(Payment)
            .where(Payment.order_id == order_id, Payment.status == "pending")
            .order_by(Payment.id)
        )
        if pending_payment is not None:
            return pending_payment

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
        PaymentService.logger.info("payment_created payment_id=%s order_id=%s provider=%s", payment.id, order.id, provider.name)
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
        if payment.status != "pending":
            raise ValueError("Payment is no longer pending")

        order = db.scalar(select(Order).where(Order.id == payment.order_id).with_for_update())
        if order is None:
            raise ValueError("Order not found")
        if order.status != "pending" or order.paid_at is not None:
            raise ValueError("Order is no longer awaiting payment")

        provider = get_payment_provider()
        try:
            result = provider.verify_payment(amount=payment.amount, authority=authority)
        except ValueError:
            payment.status = "failed"
            db.commit()
            raise
        payment.status = "paid"
        payment.transaction_id = result["transaction_id"]
        payment.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
        OrderService.finalize_paid_order(db, order, payment.paid_at)
        for item in order.items:
            if item.product_id is not None:
                inventory_result = db.execute(
                    update(Product)
                    .where(
                        Product.id == item.product_id,
                        Product.stock >= item.quantity,
                        Product.reserved_stock >= item.quantity,
                    )
                    .values(
                        stock=Product.stock - item.quantity,
                        reserved_stock=Product.reserved_stock - item.quantity,
                    )
                )
                if getattr(inventory_result, "rowcount", 0) != 1:
                    db.rollback()
                    raise ValueError("Reserved stock is no longer available")
        db.commit()
        db.refresh(payment)
        PaymentService.logger.info("payment_verified payment_id=%s order_id=%s", payment.id, order.id)
        notify_payment_success(order, payment.transaction_id)
        return payment

    @staticmethod
    def record_gateway_outcome(db: Session, authority: str, status: str) -> None:
        normalized = status.casefold()
        payment_state = {
            "cancel": "cancelled",
            "cancelled": "cancelled",
            "canceled": "cancelled",
            "expired": "expired",
            "failed": "failed",
            "nok": "failed",
        }.get(normalized)
        if payment_state is None:
            return
        payment = db.scalar(select(Payment).where(Payment.authority == authority).with_for_update())
        if payment is None or payment.status == "paid":
            return
        payment.status = payment_state
        db.commit()