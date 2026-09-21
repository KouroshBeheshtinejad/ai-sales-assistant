import jwt
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import PasswordResetToken, User
from app.core.config import cookie_settings
from app.core.csrf import require_csrf_token
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.chat_rate_limit import enforce_auth_rate_limit
from app.services.verification_service import issue_code, verify_code


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

templates = Jinja2Templates(directory="app/templates")


security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def _set_access_token_cookie(response: Response, access_token: str) -> None:
    settings = cookie_settings()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.secure,
        samesite=settings.samesite,
        max_age=settings.max_age_seconds,
    )


class RegisterRequest(BaseModel):
    email: EmailStr
    first_name: str | None = Field(None, min_length=1, max_length=120)
    last_name: str | None = Field(None, min_length=1, max_length=120)
    phone: str | None = Field(None, min_length=5, max_length=50)
    password: str = Field(..., min_length=8)
    confirm_password: str | None = Field(None, min_length=8)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class VerifyAccountRequest(BaseModel):
    email: EmailStr
    email_code: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    phone_code: str | None = Field(None, min_length=8, max_length=8, pattern=r"^\d{8}$")


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=255)
    new_password: str = Field(..., min_length=8)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    if request.cookies.get("access_token"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="auth_login.html", context={"error": None})


@router.get("/register", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request):
    if request.cookies.get("access_token"):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": None})


@router.post("/login-form", response_class=HTMLResponse, include_in_schema=False)
def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf_token),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="auth_login.html",
            context={"error": "The email or password is incorrect."},
            status_code=401,
        )
    access_token = create_access_token(user.id, user.token_version)
    redirect = RedirectResponse(url="/dashboard", status_code=303)
    _set_access_token_cookie(redirect, access_token)
    return redirect


@router.post("/register-form", response_class=HTMLResponse, include_in_schema=False)
def register_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf_token),
):
    if len(password) < 8:
        return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": "Password must be at least 8 characters."}, status_code=422)
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": "An account with this email already exists."}, status_code=400)
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    access_token = create_access_token(user.id, user.token_version)
    redirect = RedirectResponse(url="/dashboard", status_code=303)
    _set_access_token_cookie(redirect, access_token)
    return redirect


@router.post("/logout", include_in_schema=False)
def logout(_: None = Depends(require_csrf_token)):
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.post("/register")
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_auth_rate_limit(request, "register")
    existing_user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        password_hash=hash_password(data.password),
        is_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    issue_code(db, user, "email")
    if user.phone:
        issue_code(db, user, "phone")

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "email": user.email,
        "verification_required": True,
        "channels": ["email", "phone"] if user.phone else ["email"],
    }


@router.post("/verify")
def verify_account(data: VerifyAccountRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification request")
    email_valid = verify_code(db, user, "email", data.email_code)
    phone_valid = True if not user.phone else bool(data.phone_code and verify_code(db, user, "phone", data.phone_code))
    if not email_valid or not phone_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code")
    user.is_verified = True
    db.commit()
    return {"message": "Account verified", "email": user.email}


def _reset_hash(token: str) -> str:
    return hashlib.sha256(f"{token}:{SECRET_KEY}".encode()).hexdigest()


@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, "password-reset")
    user = db.query(User).filter(User.email == data.email).first()
    if user is not None:
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: datetime.now(timezone.utc).replace(tzinfo=None)})
        raw_token = secrets.token_urlsafe(48)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=_reset_hash(raw_token),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15),
        ))
        db.commit()
        if os.getenv("PASSWORD_RESET_PROVIDER", "disabled").casefold() == "log" and os.getenv("APP_ENV", "development").casefold() not in {"production", "prod"}:
            logger.info("Password reset token issued for %s: %s", user.email, raw_token)
    return {"message": "If the account exists, reset instructions will be sent."}


@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == _reset_hash(data.token),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
    ).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    record.user.password_hash = hash_password(data.new_password)
    record.user.token_version += 1
    record.used_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"message": "Password reset successful"}


@router.post("/login")
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    enforce_auth_rate_limit(request, "login")
    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if not user or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account verification is required",
        )

    access_token = create_access_token(user.id, user.token_version)

    _set_access_token_cookie(response, access_token)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        user_id = int(user_id)

    except (jwt.PyJWTError, TypeError, ValueError, OverflowError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if payload.get("token_version", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, OverflowError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if payload.get("token_version", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "created_at": current_user.created_at,
    }

def get_current_user_from_cookie(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")

    # Fallback to Authorization header
    if not token:
        authorization = request.headers.get("Authorization")

        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        user_id = int(user_id)

    except (jwt.PyJWTError, TypeError, ValueError, OverflowError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
