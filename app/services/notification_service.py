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


class DisabledSMSProvider:
    def send(self, *, phone: str, message: str) -> None:
        logger.info("SMS provider disabled; notification skipped for order")


def get_sms_provider() -> SMSProvider:
    # A concrete vendor is deliberately not assumed; credentials stay external.
    if os.getenv("SMS_PROVIDER", "disabled").casefold() == "disabled":
        return DisabledSMSProvider()
    logger.warning("Unsupported SMS_PROVIDER; notification skipped")
    return DisabledSMSProvider()


def notify_order_created(order: Order) -> None:
    message = f"NAVA order #{order.id} created. Total: {order.total_amount}"
    try:
        get_sms_provider().send(phone=order.customer_phone, message=message)
    except Exception:
        logger.exception("Order notification failed for order_id=%s", order.id)
