import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken


class PaymentCredentialError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = os.getenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", "").strip()
    if not key:
        raise PaymentCredentialError("Payment credential encryption is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise PaymentCredentialError("Payment credential encryption is not configured") from exc


def encrypt_payment_credential(value: str) -> str:
    try:
        return _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    except (UnicodeEncodeError, PaymentCredentialError) as exc:
        if isinstance(exc, PaymentCredentialError):
            raise
        raise PaymentCredentialError("Payment credential could not be stored") from exc


def decrypt_payment_credential(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError, PaymentCredentialError) as exc:
        raise PaymentCredentialError("Stored payment credential is unavailable") from exc


def fingerprint_payment_credential(value: str) -> str:
    key = os.getenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", "").strip()
    if not key:
        raise PaymentCredentialError("Payment credential encryption is not configured")
    try:
        _fernet()
        return hmac.new(key.encode("ascii"), value.encode("utf-8"), hashlib.sha256).hexdigest()
    except (UnicodeEncodeError, PaymentCredentialError) as exc:
        if isinstance(exc, PaymentCredentialError):
            raise
        raise PaymentCredentialError("Payment credential could not be fingerprinted") from exc