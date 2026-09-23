from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import SECRET_KEY
from app.db.models import User, VerificationCode
from app.services.notification_service import get_email_provider, get_sms_provider


OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _hash_code(user_id: int, channel: str, code: str) -> str:
    payload = f"{user_id}:{channel}:{code}".encode()
    return hmac.new(SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()


def issue_code(db: Session, user: User, channel: str) -> str:
    target = user.email if channel == "email" else user.phone
    if not target:
        raise ValueError(f"User has no {channel} target")
    db.query(VerificationCode).filter(
        VerificationCode.user_id == user.id,
        VerificationCode.channel == channel,
        VerificationCode.used_at.is_(None),
    ).update({VerificationCode.used_at: datetime.now(timezone.utc).replace(tzinfo=None)})
    code = f"{secrets.randbelow(100_000_000):08d}"
    record = VerificationCode(
        user_id=user.id,
        channel=channel,
        target=target,
        code_hash=_hash_code(user.id, channel, code),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(record)
    db.commit()
    provider = os.getenv("OTP_PROVIDER", "disabled").casefold()
    if provider == "email":
        get_email_provider().send(
            email=user.email,
            subject="NAVA verification code",
            message=f"Your NAVA verification code is {code}.",
        )
    elif provider == "sms" and user.phone:
        get_sms_provider().send(
            phone=user.phone,
            message=f"NAVA verification code: {code}",
        )
    return code


def verify_code(db: Session, user: User, channel: str, code: str) -> bool:
    record = db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.user_id == user.id,
            VerificationCode.channel == channel,
            VerificationCode.used_at.is_(None),
        )
        .order_by(VerificationCode.created_at.desc())
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if record is None or record.expires_at <= now or record.attempts >= OTP_MAX_ATTEMPTS:
        return False
    record.attempts += 1
    valid = hmac.compare_digest(record.code_hash, _hash_code(user.id, channel, code))
    if valid:
        record.used_at = now
    db.commit()
    return valid