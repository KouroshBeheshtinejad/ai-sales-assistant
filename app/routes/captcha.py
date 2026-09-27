"""Issues human-verification challenges for login, registration, and the seller
account form. See app/services/captcha_service.py for how challenges are generated,
stored, and verified.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.captcha_service import generate_captcha


router = APIRouter(prefix="/captcha", tags=["Captcha"])


@router.get("")
def new_captcha(db: Session = Depends(get_db)):
    token, image_bytes = generate_captcha(db)
    return {
        "captcha_token": token,
        # A data URI keeps this to one round trip and avoids a second, guessable
        # "fetch the image" endpoint that would need its own auth story.
        "image": "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
    }
