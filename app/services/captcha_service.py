"""Generates and verifies the small "type the number you see" human check used on
login, registration, and the seller account-completion form.

This is a lightweight, self-hosted CAPTCHA: no external service, no API key, and it
degrades gracefully offline. It is not meant to withstand a determined, well-funded
attacker (no CAPTCHA rendered this simply is) — it exists to stop casual scripted
abuse of these forms, which is the threat these endpoints actually face.

Challenges are stored server-side (DB-backed, so this also works correctly across
multiple worker processes), single-use, short-lived, and rate-limited by attempts,
mirroring the existing VerificationCode / PasswordResetToken pattern.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import SECRET_KEY
from app.db.models import CaptchaChallenge


CODE_LENGTH = 5
EXPIRY_MINUTES = 10
MAX_ATTEMPTS = 5
IMAGE_SIZE = (160, 60)
_FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Vazirmatn-Bold.ttf"


def _hash_code(token: str, code: str) -> str:
    payload = f"{token}:{code}".encode()
    return hmac.new(SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()


def _render_image(code: str) -> bytes:
    width, height = IMAGE_SIZE
    image = Image.new("RGB", (width, height), "#f1f6f5")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(_FONT_PATH), 34)

    rng = secrets.SystemRandom()

    # Noise lines behind the digits, then the digits themselves (each with a small
    # random offset/rotation so the code cannot be lifted with a plain string match
    # against a fixed template).
    for _ in range(6):
        x1, y1 = rng.randint(0, width), rng.randint(0, height)
        x2, y2 = rng.randint(0, width), rng.randint(0, height)
        draw.line((x1, y1, x2, y2), fill="#b9cfcb", width=1)

    slot_width = width / len(code)
    for index, digit in enumerate(code):
        glyph = Image.new("RGBA", (40, 50), (0, 0, 0, 0))
        glyph_draw = ImageDraw.Draw(glyph)
        glyph_draw.text((8, 4), digit, font=font, fill="#0b5f5a")
        angle = rng.randint(-22, 22)
        glyph = glyph.rotate(angle, expand=True, resample=Image.BICUBIC)
        x = int(index * slot_width + rng.randint(2, 10))
        y = rng.randint(2, max(2, height - glyph.height - 2))
        image.paste(glyph, (x, y), glyph)

    for _ in range(80):
        x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
        draw.point((x, y), fill="#8fa8a4")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_captcha(db: Session) -> tuple[str, bytes]:
    """Creates a new challenge and returns its token and PNG image bytes."""
    code = "".join(str(secrets.randbelow(10)) for _ in range(CODE_LENGTH))
    token = secrets.token_urlsafe(24)
    db.add(CaptchaChallenge(
        token=token,
        code_hash=_hash_code(token, code),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=EXPIRY_MINUTES),
    ))
    db.commit()
    return token, _render_image(code)


def verify_captcha(db: Session, token: str, answer: str) -> bool:
    """Checks the answer against a challenge. Always single-use: correct or not,
    a solved-or-attempted challenge cannot be replayed."""
    if not token or not answer:
        return False
    record = db.scalar(
        select(CaptchaChallenge).where(
            CaptchaChallenge.token == token,
            CaptchaChallenge.used_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if record is None or record.expires_at <= now or record.attempts >= MAX_ATTEMPTS:
        return False
    record.attempts += 1
    valid = hmac.compare_digest(record.code_hash, _hash_code(token, answer.strip()))
    record.used_at = now
    db.commit()
    return valid
