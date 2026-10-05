from __future__ import annotations

import os
import secrets
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Protocol

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import Order, Payment, PaymentTransaction, Product, Store, StorePaymentAccount
from app.security.payment_credentials import (
    PaymentCredentialError,
    decrypt_payment_credential,
)
from app.services.notification_service import notify_payment_success
from app.services.order_service import OrderService


class PaymentProvider(Protocol):
    name: str

    def create_payment(self, *, amount: Decimal, currency: str, order_id: int, callback_url: str | None = None) -> dict: ...
    def verify_payment(self, *, amount: Decimal, currency: str, authority: str) -> dict: ...
    def get_status(self, *, authority: str, currency: str) -> str: ...
    def refund(self, *, transaction_id: str, amount: Decimal, currency: str, authority: str | None = None) -> dict: ...


class PaymentProviderNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class PaymentAccountContext:
    provider: str
    store_id: int | None
    account_id: int | None
    external_account_id: str | None
    credential_reference: str | None
    country_code: str
    currency: str
    credential_ciphertext: str | None = None

    @classmethod
    def from_account(cls, account: StorePaymentAccount) -> "PaymentAccountContext":
        return cls(
            provider=account.provider,
            store_id=account.store_id,
            account_id=account.id,
            external_account_id=account.external_account_id,
            credential_reference=account.credential_reference,
            country_code=account.country_code,
            currency=account.currency,
            credential_ciphertext=account.credential_ciphertext,
        )

    def snapshot(self) -> dict:
        return {
            "store_id": self.store_id,
            "external_account_id": self.external_account_id,
            "credential_reference": self.credential_reference,
            "credential_ciphertext": self.credential_ciphertext,
            "country_code": self.country_code,
            "currency": self.currency,
        }


def toman_to_rial(amount: Decimal, currency: str = "IRT") -> int:
    if currency == "IRT":
        rial_amount = Decimal(str(amount)) * Decimal("10")
    elif currency == "IRR":
        rial_amount = Decimal(str(amount))
    else:
        raise ValueError("ZarinPal only supports IRT or IRR store currencies")
    if rial_amount != rial_amount.to_integral_value():
        raise ValueError("Payment amount must be representable as a whole rial")
    return int(rial_amount)


class MockPaymentProvider:
    name = "mock"

    def create_payment(self, *, amount: Decimal, currency: str, order_id: int, callback_url: str | None = None) -> dict:
        return {"authority": f"mock-{secrets.token_urlsafe(18)}", "payment_url": None}

    def verify_payment(self, *, amount: Decimal, currency: str, authority: str) -> dict:
        if not authority.startswith("mock-"):
            raise ValueError("Invalid payment authority")
        return {"transaction_id": f"mock-tx-{secrets.token_urlsafe(12)}"}

    def get_status(self, *, authority: str, currency: str) -> str:
        return "pending" if authority.startswith("mock-") else "failed"

    def refund(self, *, transaction_id: str, amount: Decimal, currency: str, authority: str | None = None) -> dict:
        if not transaction_id.startswith("mock-tx-"):
            raise ValueError("Invalid transaction")
        return {"status": "refunded"}


class ZarinpalPaymentProvider:
    name = "zarinpal"

    def __init__(self, account: PaymentAccountContext | None = None) -> None:
        self.merchant_id: str | None
        try:
            if account and account.credential_ciphertext:
                self.merchant_id = decrypt_payment_credential(account.credential_ciphertext)
            elif account and account.credential_reference:
                if not account.credential_reference.replace("_", "").isalnum():
                    raise PaymentProviderNotConfigured("Invalid ZarinPal credential reference")
                self.merchant_id = os.getenv(f"PAYMENT_SECRET_{account.credential_reference}")
            else:
                self.merchant_id = None
        except PaymentCredentialError as exc:
            raise PaymentProviderNotConfigured("ZarinPal Store credential is unavailable") from exc
        self.callback_url = os.getenv("PAYMENT_CALLBACK_URL", "").strip()
        if not self.merchant_id or not self.callback_url:
            raise PaymentProviderNotConfigured("ZarinPal Store account or callback URL is not configured")
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
        try:
            with urllib_request.urlopen(request, timeout=15) as response:
                return json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise PaymentProviderNotConfigured("ZarinPal request failed") from exc

    def create_payment(self, *, amount: Decimal, currency: str, order_id: int, callback_url: str | None = None) -> dict:
        rial_amount = toman_to_rial(amount, currency)
        result = self._post(
            "request.json",
            {
                "merchant_id": self.merchant_id,
                "amount": rial_amount,
                "currency": "IRR",
                "callback_url": callback_url or self.callback_url,
                "description": f"NAVA order {order_id}",
            },
        )
        data = result.get("data") or {}
        if data.get("code") != 100 or not data.get("authority"):
            raise PaymentProviderNotConfigured("Payment gateway rejected the payment request")
        authority = data["authority"]
        return {
            "authority": authority,
            "payment_url": f"https://payment.zarinpal.com/pg/StartPay/{authority}",
        }

    def verify_payment(self, *, amount: Decimal, currency: str, authority: str) -> dict:
        result = self._post(
            "verify.json",
            {
                "merchant_id": self.merchant_id,
                "amount": toman_to_rial(amount, currency),
                "authority": authority,
            },
        )
        data = result.get("data") or {}
        if data.get("code") not in {100, 101} or not data.get("ref_id"):
            raise ValueError("Payment verification failed")
        return {"transaction_id": str(data["ref_id"])}

    def get_status(self, *, authority: str, currency: str) -> str:
        result = self._post(
            "inquiry.json",
            {"merchant_id": self.merchant_id, "authority": authority},
        )
        status = str((result.get("data") or {}).get("status", "")).upper()
        return {
            "VERIFIED": "paid",
            "PAID": "paid",
            "IN_BANK": "pending",
            "FAILED": "failed",
            "REVERSED": "cancelled",
        }.get(status, "unknown")

    def refund(
        self,
        *,
        transaction_id: str,
        amount: Decimal,
        currency: str,
        authority: str | None = None,
    ) -> dict:
        if not authority:
            raise PaymentProviderNotConfigured("ZarinPal payment authority is unavailable")
        result = self._post(
            "reverse.json",
            {"merchant_id": self.merchant_id, "authority": authority},
        )
        data = result.get("data") or {}
        if data.get("code") != 100:
            raise PaymentProviderNotConfigured("ZarinPal could not reverse this payment")
        return {"status": "refunded", "id": authority}


class PaymentProviderRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[PaymentAccountContext | None], PaymentProvider]] = {}

    def register(self, name: str, factory: Callable[[PaymentAccountContext | None], PaymentProvider]) -> None:
        self._factories[name] = factory

    def unregister(self, name: str) -> None:
        self._factories.pop(name, None)

    def has_adapter(self, name: str) -> bool:
        return name in self._factories

    def create(self, name: str, account: PaymentAccountContext | None = None) -> PaymentProvider:
        factory = self._factories.get(name)
        if factory is None:
            raise PaymentProviderNotConfigured(f"Payment provider adapter '{name}' is not installed")
        if name == "mock" and os.getenv("APP_ENV", "development").strip().casefold() in {"production", "prod"}:
            raise PaymentProviderNotConfigured("Mock payment provider is disabled in production")
        return factory(account)


payment_provider_registry = PaymentProviderRegistry()
payment_provider_registry.register("mock", lambda _account: MockPaymentProvider())
payment_provider_registry.register("zarinpal", lambda account: ZarinpalPaymentProvider(account))

SUPPORTED_PAYMENT_PROVIDERS = (
    "disabled",
    "zarinpal",
    "stripe_connect",
    "paypal_multiparty",
    "adyen_platforms",
    "mollie_connect",
    "mock",
)


def get_payment_provider(
    provider: str | None = None,
    account: PaymentAccountContext | None = None,
) -> PaymentProvider:
    selected = provider or os.getenv("PAYMENT_PROVIDER", "disabled").strip().casefold()
    if selected == "disabled":
        raise PaymentProviderNotConfigured("Payment is disabled")
    return payment_provider_registry.create(selected, account)


class PaymentService:
    logger = logging.getLogger(__name__)

    @staticmethod
    def _payment_account(db: Session, store_id: int, provider_name: str) -> StorePaymentAccount:
        account = db.scalar(
            select(StorePaymentAccount).where(
                StorePaymentAccount.store_id == store_id,
                StorePaymentAccount.provider == provider_name,
            )
        )
        if account is None or account.status != "active":
            raise PaymentProviderNotConfigured("Store payment account is not active")
        if provider_name == "zarinpal" and not account.credential_fingerprint:
            raise PaymentProviderNotConfigured("Store ZarinPal credentials must be saved again")
        return account

    @staticmethod
    def _provider_for_payment(db: Session, payment: Payment, expected_store_id: int) -> PaymentProvider:
        account = db.get(StorePaymentAccount, payment.provider_account_id) if payment.provider_account_id is not None else None
        context = payment.provider_context or {}

        if payment.provider == "mock" and account is None:
            if context.get("store_id") not in (None, expected_store_id):
                raise PaymentProviderNotConfigured("Payment Store account is unavailable")
            account_context = PaymentAccountContext(
                provider=payment.provider,
                store_id=context.get("store_id") or expected_store_id,
                account_id=None,
                external_account_id=context.get("external_account_id"),
                credential_reference=context.get("credential_reference"),
                country_code=context.get("country_code", ""),
                currency=context.get("currency", payment.currency),
                credential_ciphertext=context.get("credential_ciphertext"),
            )
            return get_payment_provider(payment.provider, account_context)

        if (
            account is None
            or account.store_id != expected_store_id
            or account.provider != payment.provider
            or (payment.provider == "zarinpal" and not account.credential_fingerprint)
        ):
            raise PaymentProviderNotConfigured("Payment Store account is unavailable")
        if context:
            if context.get("store_id") != expected_store_id:
                raise PaymentProviderNotConfigured("Payment Store account is unavailable")
            account_context = PaymentAccountContext(
                provider=payment.provider,
                store_id=context.get("store_id"),
                account_id=payment.provider_account_id,
                external_account_id=context.get("external_account_id"),
                credential_reference=context.get("credential_reference"),
                country_code=context.get("country_code", ""),
                currency=context.get("currency", payment.currency),
                credential_ciphertext=context.get("credential_ciphertext"),
            )
            return get_payment_provider(payment.provider, account_context)
        return get_payment_provider(payment.provider, PaymentAccountContext.from_account(account))

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

        store = db.get(Store, order.store_id)
        if store is None:
            raise PaymentProviderNotConfigured("Payment is not configured for this Store")

        selected_provider = store.payment_provider if store.payment_provider != "disabled" else os.getenv("PAYMENT_PROVIDER", "disabled").strip().casefold()
        if selected_provider == "disabled":
            raise PaymentProviderNotConfigured("Payment is not configured for this Store")

        account = None
        if selected_provider == "mock":
            account = db.scalar(
                select(StorePaymentAccount).where(
                    StorePaymentAccount.store_id == store.id,
                    StorePaymentAccount.provider == "mock",
                )
            )
        else:
            account = PaymentService._payment_account(db, store.id, selected_provider)
            if account.currency != order.currency or account.currency != store.currency:
                raise PaymentProviderNotConfigured("Store payment account currency does not match the order")

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

        if account is not None:
            account_context = PaymentAccountContext.from_account(account)
        else:
            account_context = PaymentAccountContext(
                provider=selected_provider,
                store_id=store.id,
                account_id=None,
                external_account_id=None,
                credential_reference=None,
                country_code=store.country_code,
                currency=order.currency,
                credential_ciphertext=None,
            )
        provider = get_payment_provider(selected_provider, account_context)
        details = provider.create_payment(
            amount=Decimal(str(order.total_amount)),
            currency=order.currency,
            order_id=order.id,
            callback_url=callback_url,
        )
        payment = Payment(
            order_id=order.id,
            provider=provider.name,
            provider_account_id=account.id if account else None,
            provider_context=account_context.snapshot(),
            amount=order.total_amount,
            currency=order.currency,
            status="pending",
            authority=details.get("authority"),
            idempotency_key=idempotency_key,
            payment_metadata={"payment_url": details.get("payment_url")},
        )
        payment.transactions.append(PaymentTransaction(
            transaction_type="payment",
            status="pending",
            amount=order.total_amount,
            currency=order.currency,
            provider_reference=details.get("authority"),
            idempotency_key=idempotency_key,
        ))
        db.add(payment)
        db.commit()
        db.refresh(payment)
        PaymentService.logger.info("payment_created payment_id=%s order_id=%s provider=%s", payment.id, order.id, provider.name)
        return payment

    @staticmethod
    def verify_payment(db: Session, payment_id: int, authority: str, user_id: int | None = None, guest_token: str | None = None) -> Payment:
        payment = db.scalar(
            select(Payment)
            .where(Payment.id == payment_id)
            .with_for_update()
        )
        if payment is None:
            raise ValueError("Payment not found")
        if payment.status == "paid":
            order = db.get(Order, payment.order_id)
            if order is None or (user_id is not None and order.user_id != user_id) or (user_id is None and order.guest_token != guest_token):
                raise ValueError("Payment not found")
            if payment.authority != authority:
                raise ValueError("Invalid payment authority")
            return payment
        if payment.status != "pending":
            raise ValueError("Payment is no longer pending")

        order = db.scalar(select(Order).where(Order.id == payment.order_id).with_for_update())
        if order is None or (user_id is not None and order.user_id != user_id) or (user_id is None and order.guest_token != guest_token):
            raise ValueError("Payment not found")
        if payment.authority != authority:
            raise ValueError("Invalid payment authority")
        if order.status != "pending" or order.paid_at is not None:
            raise ValueError("Order is no longer awaiting payment")

        provider = PaymentService._provider_for_payment(db, payment, order.store_id)
        try:
            result = provider.verify_payment(amount=payment.amount, currency=payment.currency, authority=authority)
        except ValueError:
            payment.status = "failed"
            payment.transactions.append(PaymentTransaction(
                transaction_type="verification",
                status="failed",
                amount=payment.amount,
                currency=payment.currency,
                provider_reference=authority,
                idempotency_key=f"verify-failed:{payment.id}",
            ))
            db.commit()
            raise
        payment.status = "paid"
        payment.transaction_id = result["transaction_id"]
        payment.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
        payment.transactions.append(PaymentTransaction(
            transaction_type="verification",
            status="paid",
            amount=payment.amount,
            currency=payment.currency,
            provider_reference=payment.transaction_id,
            idempotency_key=f"verify:{payment.id}",
        ))
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
    def reconcile_payment(
        db: Session,
        payment_id: int,
        user_id: int | None = None,
        guest_token: str | None = None,
    ) -> Payment:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if payment is None:
            raise ValueError("Payment not found")
        order = db.scalar(select(Order).where(Order.id == payment.order_id).with_for_update())
        if order is None or (user_id is not None and order.user_id != user_id) or (user_id is None and order.guest_token != guest_token):
            raise ValueError("Payment not found")
        if payment.status != "pending":
            return payment

        provider = PaymentService._provider_for_payment(db, payment, order.store_id)
        outcome = provider.get_status(authority=payment.authority or "", currency=payment.currency).casefold()
        if outcome in {"paid", "succeeded", "success", "completed"}:
            return PaymentService.verify_payment(
                db,
                payment.id,
                payment.authority or "",
                user_id,
                guest_token,
            )
        terminal_status = {
            "failed": "failed",
            "cancelled": "cancelled",
            "canceled": "cancelled",
            "expired": "expired",
        }.get(outcome)
        if terminal_status:
            payment.status = terminal_status
            payment.transactions.append(PaymentTransaction(
                transaction_type="reconciliation",
                status=terminal_status,
                amount=payment.amount,
                currency=payment.currency,
                provider_reference=payment.authority,
                idempotency_key=f"reconcile:{payment.id}:{terminal_status}",
            ))
            db.commit()
            db.refresh(payment)
        return payment

    @staticmethod
    def refund_payment(
        db: Session,
        payment_id: int,
        amount: Decimal,
        idempotency_key: str,
        user_id: int,
    ) -> PaymentTransaction:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if payment is None:
            raise ValueError("Payment not found")
        order = db.scalar(select(Order).where(Order.id == payment.order_id).with_for_update())
        store = db.get(Store, order.store_id) if order is not None else None
        if order is None or store is None or store.owner_id != user_id:
            raise ValueError("Payment not found")

        existing = db.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.payment_id == payment.id,
                PaymentTransaction.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing
        if payment.status != "paid":
            raise ValueError("Only paid payments can be refunded")
        if amount <= 0:
            raise ValueError("Refund amount must be positive")

        refunded = db.scalar(
            select(func.coalesce(func.sum(PaymentTransaction.amount), 0)).where(
                PaymentTransaction.payment_id == payment.id,
                PaymentTransaction.transaction_type == "refund",
                PaymentTransaction.status.in_(("pending", "refunded", "succeeded")),
            )
        )
        if amount > Decimal(str(payment.amount)) - Decimal(str(refunded or 0)):
            raise ValueError("Refund amount exceeds the remaining captured amount")

        remaining = Decimal(str(payment.amount)) - Decimal(str(refunded or 0))
        if payment.provider == "zarinpal":
            if amount != remaining:
                raise ValueError("ZarinPal only supports a full reverse")
            paid_at = payment.paid_at.replace(tzinfo=timezone.utc) if payment.paid_at and payment.paid_at.tzinfo is None else payment.paid_at
            if paid_at is None or datetime.now(timezone.utc) - paid_at > timedelta(minutes=30):
                raise ValueError("ZarinPal reverse is only available within 30 minutes")

        provider = PaymentService._provider_for_payment(db, payment, order.store_id)
        result = provider.refund(
            transaction_id=payment.transaction_id or "",
            amount=amount,
            currency=payment.currency,
            authority=payment.authority,
        )
        provider_status = str(result.get("status", "pending")).casefold()
        transaction = PaymentTransaction(
            transaction_type="refund",
            status="refunded" if provider_status in {"refunded", "succeeded", "success"} else provider_status,
            amount=amount,
            currency=payment.currency,
            provider_reference=result.get("transaction_id") or result.get("id"),
            idempotency_key=idempotency_key,
            transaction_metadata={key: value for key, value in result.items() if key not in {"transaction_id", "id"}},
        )
        payment.transactions.append(transaction)
        if transaction.status == "refunded" and amount == Decimal(str(payment.amount)) - Decimal(str(refunded or 0)):
            payment.status = "refunded"
        db.commit()
        db.refresh(transaction)
        return transaction
