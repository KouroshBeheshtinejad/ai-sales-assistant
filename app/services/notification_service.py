"""Post-order notification boundary.

The provider is intentionally disabled until a buyer selects an SMS vendor.
No order transaction depends on this service succeeding.
"""
from __future__ import annotations

import logging
import os
from typing import Protocol

from app.db.models import Order

logger = logging.getLogger(__name__)


class SMSProvider(Protocol):
    def send(self, *, phone: str, message: str) -> None: ...


class EmailProvider(Protocol):
    def send(self, *, email: str, subject: str, message: str) -> None: ...


class DisabledSMSProvider:
    def send(self, *, phone: str, message: str) -> None:
        logger.info("SMS provider disabled; notification skipped for order")


class DisabledEmailProvider:
    def send(self, *, email: str, subject: str, message: str) -> None:
        logger.info("Email provider disabled; notification skipped")


def get_sms_provider() -> SMSProvider:
    # A concrete vendor is deliberately not assumed; credentials stay external.
    if os.getenv("SMS_PROVIDER", "disabled").casefold() == "disabled":
        return DisabledSMSProvider()
    logger.warning("Unsupported SMS_PROVIDER; notification skipped")
    return DisabledSMSProvider()


def get_email_provider() -> EmailProvider:
    if os.getenv("EMAIL_PROVIDER", "disabled").casefold() == "disabled":
        return DisabledEmailProvider()
    logger.warning("Unsupported EMAIL_PROVIDER; notification skipped")
    return DisabledEmailProvider()


def notify_order_created(order: Order) -> None:
    message = f"NAVA order #{order.id} created. Total: {order.total_amount}"
    try:
        get_sms_provider().send(phone=order.customer_phone, message=message)
    except Exception:
        logger.exception("Order notification failed for order_id=%s", order.id)


def notify_payment_success(order: Order, transaction_id: str) -> None:
    message = f"NAVA payment confirmed for order {order.tracking_number}. Transaction: {transaction_id}"
    try:
        get_sms_provider().send(phone=order.customer_phone, message=message)
        if order.customer_email:
            get_email_provider().send(email=order.customer_email, subject="NAVA payment confirmed", message=message)
        if order.store.owner.email:
            get_email_provider().send(email=order.store.owner.email, subject="NAVA order payment received", message=message)
    except Exception:
        logger.exception("Payment notification failed for order_id=%s", order.id)
