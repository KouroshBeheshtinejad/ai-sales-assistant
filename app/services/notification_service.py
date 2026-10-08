"""Post-order notification boundary.

Email and SMS providers are configurable through environment variables.
No order transaction depends on notification delivery succeeding.
"""
from __future__ import annotations

import json
import html
import logging
import os
import smtplib
from email.message import EmailMessage
from urllib import request as urllib_request
from typing import Protocol

from app.db.models import Order

logger = logging.getLogger(__name__)


class SMSProvider(Protocol):
    def send(self, *, phone: str, message: str) -> None: ...


class EmailProvider(Protocol):
    def send(self, *, email: str, subject: str, message: str, html_message: str | None = None) -> None: ...


class DisabledSMSProvider:
    def send(self, *, phone: str, message: str) -> None:
        logger.info("SMS provider disabled; notification skipped for order")


class DisabledEmailProvider:
    def send(self, *, email: str, subject: str, message: str, html_message: str | None = None) -> None:
        logger.info("Email provider disabled; notification skipped")


class SMTPEmailProvider:
    def send(self, *, email: str, subject: str, message: str, html_message: str | None = None) -> None:
        mail = EmailMessage()
        mail["From"] = os.environ["SMTP_FROM"]
        mail["To"] = email
        mail["Subject"] = subject
        mail.set_content(message)
        if html_message:
            mail.add_alternative(html_message, subtype="html")

        host = os.environ["SMTP_HOST"]
        port = int(os.getenv("SMTP_PORT", "587"))

        with smtplib.SMTP(host, port, timeout=10) as client:
            client.starttls()
            client.login(
                os.environ["SMTP_USERNAME"],
                os.environ["SMTP_PASSWORD"],
            )
            client.send_message(mail)


class EmailBumpEmailProvider:
    API_URL = "https://emailbump.com/api/v1/emails"

    def send(self, *, email: str, subject: str, message: str, html_message: str | None = None) -> None:
        api_key = os.environ["EMAILBUMP_API_KEY"]
        sender = os.environ["EMAILBUMP_FROM"]

        payload = json.dumps(
            {
                "from": sender,
                "to": email,
                "subject": subject,
                "html": html_message or f"<p>{html.escape(message).replace(chr(10), '<br>')}</p>",
                "text": message,
            }
        ).encode("utf-8")

        req = urllib_request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib_request.urlopen(req, timeout=10) as response:
            response.read()


class WebhookSMSProvider:
    def send(self, *, phone: str, message: str) -> None:
        payload = json.dumps(
            {"to": phone, "message": message}
        ).encode()

        req = urllib_request.Request(
            os.environ["SMS_WEBHOOK_URL"],
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib_request.urlopen(req, timeout=10):
            return


def get_sms_provider() -> SMSProvider:
    provider = os.getenv("SMS_PROVIDER", "disabled").casefold()

    if provider == "disabled":
        return DisabledSMSProvider()

    if provider == "webhook":
        return WebhookSMSProvider()

    logger.warning("Unsupported SMS_PROVIDER; notification skipped")
    return DisabledSMSProvider()


def get_email_provider() -> EmailProvider:
    provider = os.getenv("EMAIL_PROVIDER", "disabled").casefold()

    if provider == "disabled":
        return DisabledEmailProvider()

    if provider == "smtp":
        return SMTPEmailProvider()

    if provider == "emailbump":
        return EmailBumpEmailProvider()

    logger.warning("Unsupported EMAIL_PROVIDER; notification skipped")
    return DisabledEmailProvider()


def notify_order_created(order: Order) -> None:
    message = f"NAVA order #{order.id} created. Total: {order.total_amount}"

    try:
        get_sms_provider().send(
            phone=order.customer_phone,
            message=message,
        )
    except Exception:
        logger.exception(
            "Order notification failed for order_id=%s",
            order.id,
        )


def notify_payment_success(order: Order, transaction_id: str) -> None:
    message = (
        f"NAVA payment confirmed for order "
        f"{order.tracking_number}. Transaction: {transaction_id}"
    )

    try:
        get_sms_provider().send(
            phone=order.customer_phone,
            message=message,
        )

        if order.customer_email:
            get_email_provider().send(
                email=order.customer_email,
                subject="NAVA payment confirmed",
                message=message,
            )

        if order.store.owner.email:
            get_email_provider().send(
                email=order.store.owner.email,
                subject="NAVA order payment received",
                message=message,
            )

    except Exception:
        logger.exception(
            "Payment notification failed for order_id=%s",
            order.id,
        )