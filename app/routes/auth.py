import jwt
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import PasswordResetToken, Store, StoreMembership, User
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
from app.services.captcha_service import verify_captcha
from app.services.notification_service import get_email_provider
from app.services.verification_service import issue_code, verify_code
from app.security.policies import store_scope_filter


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

templates = Jinja2Templates(directory="app/templates")


security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-only")


def _normalized_email(email: str) -> str:
    return email.strip().casefold()


def _sync_god_role(user: User) -> None:
    god_email = _normalized_email(os.getenv("GOD_USER_EMAIL", ""))
    if god_email and user.is_verified and user.email.casefold() == god_email:
        user.role = "god"
        user.approval_status = "active"
    elif user.role == "god":
        user.role = "store_owner"


def store_owner_filter(user: User, permission: str = "store.read"):
    return store_scope_filter(user, permission)


def store_owner_only_filter(user: User):
    from sqlalchemy import true

    if user.role == "god":
        return true()
    return Store.owner_id == user.id


def require_roles(user: User, *roles: str) -> None:
    if user.approval_status != "active" or user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role access denied")


def _set_access_token_cookie(response: Response, access_token: str) -> None:
    settings = cookie_settings()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.secure,
        samesite=cast(Literal["lax", "strict", "none"], settings.samesite),
        max_age=settings.max_age_seconds,
    )


class RegisterRequest(BaseModel):
    email: EmailStr
    first_name: str | None = Field(None, min_length=1, max_length=120)
    last_name: str | None = Field(None, min_length=1, max_length=120)
    phone: str | None = Field(None, min_length=5, max_length=50)
    password: str = Field(..., min_length=8)
    confirm_password: str | None = Field(None, min_length=8)
    captcha_token: str = Field(..., min_length=1)
    captcha_answer: str = Field(..., min_length=1, max_length=16)
    role: Literal["customer", "store_owner", "store_admin", "support"] = "customer"
    store_id: int | None = Field(None, gt=0)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    @model_validator(mode="after")
    def validate_requested_role(self):
        if self.role == "store_admin" and self.store_id is None:
            raise ValueError("A store is required for a store admin request")
        if self.role != "store_admin" and self.store_id is not None:
            raise ValueError("A store can only be selected for a store admin request")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    captcha_token: str = Field(..., min_length=1)
    captcha_answer: str = Field(..., min_length=1, max_length=16)
    role: Literal["customer", "store_owner", "store_admin", "support", "god"] | None = None


class ProfileUpdateRequest(BaseModel):
    """The seller "complete your account" form. Every field here is required once the
    seller is filling this form in, even though most of them are optional at plain
    registration time (see RegisterRequest) — this is a deliberate, later step.
    """

    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)
    national_id: str = Field(..., pattern=r"^\d{10}$")
    business_address: str = Field(..., min_length=1, max_length=1000)
    business_phone: str = Field(..., min_length=5, max_length=50)
    password: str | None = Field(None, min_length=8)
    confirm_password: str | None = Field(None, min_length=8)
    captcha_token: str = Field(..., min_length=1)
    captcha_answer: str = Field(..., min_length=1, max_length=16)

    @model_validator(mode="after")
    def passwords_match(self):
        if (self.password or self.confirm_password) and self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


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
        return RedirectResponse(url="/workspace", status_code=303)
    return templates.TemplateResponse(request=request, name="auth_login.html", context={"error": None})


@router.get("/register", response_class=HTMLResponse, include_in_schema=False)
def register_page(request: Request):
    if request.cookies.get("access_token"):
        return RedirectResponse(url="/workspace", status_code=303)
    return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": None})


@router.post("/login-form", response_class=HTMLResponse, include_in_schema=False)
def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str | None = Form(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf_token),
):
    enforce_auth_rate_limit(request, "login-form")
    normalized_email = _normalized_email(email)
    user = db.query(User).filter(User.email == normalized_email).first()
    password_valid = verify_password(
        password,
        user.password_hash if user is not None else _DUMMY_PASSWORD_HASH,
    )
    if user is None or not password_valid:
        return templates.TemplateResponse(
            request=request,
            name="auth_login.html",
            context={"error": "The email or password is incorrect."},
            status_code=401,
        )
    _sync_god_role(user)
    if role and role != user.role:
        return templates.TemplateResponse(
            request=request,
            name="auth_login.html",
            context={"error": "Selected role does not match this account."},
            status_code=409,
        )
    if not user.is_verified or user.approval_status != "active":
        return templates.TemplateResponse(
            request=request,
            name="auth_login.html",
            context={"error": "Account verification or approval is required."},
            status_code=403,
        )
    db.commit()
    access_token = create_access_token(user.id, user.token_version)
    redirect = RedirectResponse(url="/workspace", status_code=303)
    _set_access_token_cookie(redirect, access_token)
    return redirect


@router.post("/register-form", response_class=HTMLResponse, include_in_schema=False)
def register_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("customer"),
    store_id: int | None = Form(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf_token),
):
    enforce_auth_rate_limit(request, "register-form")
    email = _normalized_email(email)
    if len(password) < 8:
        return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": "Password must be at least 8 characters."}, status_code=422)
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": "An account with this email already exists."}, status_code=400)
    if role not in {"customer", "store_owner", "store_admin", "support"}:
        return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": "Invalid account role."}, status_code=422)
    if role == "store_admin" and (store_id is None or db.get(Store, store_id) is None):
        return templates.TemplateResponse(request=request, name="auth_register.html", context={"error": "A valid store is required."}, status_code=422)
    user = User(
        email=email,
        password_hash=hash_password(password),
        is_verified=False,
        role=role,
        approval_status="active" if role == "customer" else "pending",
    )
    db.add(user)
    db.flush()
    if role == "store_admin":
        db.add(StoreMembership(store_id=store_id, user_id=user.id, status="pending"))
    db.commit()
    db.refresh(user)
    issue_code(db, user, "email")
    redirect = RedirectResponse(url="/auth/login", status_code=303)
    return redirect


@router.post("/logout", include_in_schema=False)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf_token),
):
    """Revoke the current session before clearing its browser cookie."""
    try:
        user = get_current_user_from_cookie(request=request, db=db)
    except HTTPException:
        user = None
    if user is not None:
        user.token_version += 1
        db.commit()
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
    if not verify_captcha(db, data.captcha_token, data.captcha_answer):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired captcha")
    normalized_email = _normalized_email(str(data.email))
    existing_user = (
        db.query(User)
        .filter(User.email == normalized_email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    if data.role == "store_admin" and db.get(Store, data.store_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    user = User(
        email=normalized_email,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        password_hash=hash_password(data.password),
        is_verified=False,
        role=data.role,
        approval_status="active" if data.role == "customer" else "pending",
    )

    db.add(user)
    db.flush()

    if data.role == "store_admin":
        db.add(StoreMembership(store_id=data.store_id, user_id=user.id, status="pending"))
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
        "role": user.role,
        "approval_status": user.approval_status,
        "approval_required": user.approval_status == "pending",
        "channels": ["email", "phone"] if user.phone else ["email"],
    }


@router.post("/verify")
def verify_account(request: Request, data: VerifyAccountRequest, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, "verify")
    user = db.query(User).filter(User.email == _normalized_email(str(data.email))).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification request")
    email_valid = verify_code(db, user, "email", data.email_code)
    phone_valid = True if not user.phone else bool(data.phone_code and verify_code(db, user, "phone", data.phone_code))
    if not email_valid or not phone_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code")
    user.is_verified = True
    _sync_god_role(user)
    db.commit()
    return {
        "message": "Account verified",
        "email": user.email,
        "role": user.role,
        "approval_status": user.approval_status,
    }


def _reset_hash(token: str) -> str:
    return hmac.new(
        SECRET_KEY.encode(),
        token.encode(),
        hashlib.sha256,
    ).hexdigest()


@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, "password-reset")
    user = db.query(User).filter(User.email == _normalized_email(str(data.email))).first()
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
        if os.getenv("EMAIL_PROVIDER", "disabled").casefold() == "smtp":
            public_url = os.getenv("APP_PUBLIC_URL", "http://localhost:8000").rstrip("/")
            get_email_provider().send(
                email=user.email,
                subject="NAVA password reset",
                message=f"Reset your password at {public_url}/reset-password?token={raw_token}",
            )
    return {"message": "If the account exists, reset instructions will be sent."}


@router.post("/password-reset/confirm")
def confirm_password_reset(request: Request, data: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, "password-reset-confirm")
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
    if not verify_captcha(db, data.captcha_token, data.captcha_answer):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired captcha")
    user = (
        db.query(User)
        .filter(User.email == _normalized_email(str(data.email)))
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

    _sync_god_role(user)
    if data.role is not None and data.role != user.role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected role does not match this account")

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account verification is required",
        )

    if user.approval_status == "pending":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account approval is pending")
    if user.approval_status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account access was rejected")
    db.commit()

    access_token = create_access_token(user.id, user.token_version)

    _set_access_token_cookie(response, access_token)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
    }


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, OverflowError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if payload.get("token_version", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    previous_role = user.role
    _sync_god_role(user)
    if user.role != previous_role:
        db.commit()
    if user.approval_status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not approved")
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials if credentials else request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return _user_from_token(token, db)


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials if credentials else request.cookies.get("access_token")
    if not token:
        return None

    return _user_from_token(token, db)


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "role": current_user.role,
        "approval_status": current_user.approval_status,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "national_id": current_user.national_id,
        "business_address": current_user.business_address,
        "business_phone": current_user.business_phone,
        "profile_complete": bool(
            current_user.first_name
            and current_user.last_name
            and current_user.phone
            and current_user.national_id
            and current_user.business_address
            and current_user.business_phone
        ),
        "store_memberships": [
            {"store_id": item.store_id, "status": item.status, "role": item.role}
            for item in db.query(StoreMembership).filter(StoreMembership.user_id == current_user.id).all()
        ],
        "created_at": current_user.created_at,
    }


@router.patch("/me")
def update_me(
    data: ProfileUpdateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enforce_auth_rate_limit(request, "profile-update")
    if not verify_captcha(db, data.captcha_token, data.captcha_answer):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired captcha")

    normalized_email = _normalized_email(str(data.email))
    if normalized_email != current_user.email:
        email_taken = (
            db.query(User)
            .filter(User.email == normalized_email, User.id != current_user.id)
            .first()
        )
        if email_taken:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if data.phone != current_user.phone:
        phone_taken = (
            db.query(User)
            .filter(User.phone == data.phone, User.id != current_user.id)
            .first()
        )
        if phone_taken:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone already registered")

    national_id_taken = (
        db.query(User)
        .filter(User.national_id == data.national_id, User.id != current_user.id)
        .first()
    )
    if national_id_taken:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="National ID already registered")

    email_changed = normalized_email != current_user.email
    current_user.first_name = data.first_name
    current_user.last_name = data.last_name
    current_user.email = normalized_email
    current_user.phone = data.phone
    current_user.national_id = data.national_id
    current_user.business_address = data.business_address
    current_user.business_phone = data.business_phone

    password_changed = False
    if data.password:
        current_user.password_hash = hash_password(data.password)
        current_user.token_version += 1
        password_changed = True

    if email_changed:
        # A changed email is unverified until proven again, exactly like a brand new
        # registration — the account keeps working, but re-verification is required.
        current_user.is_verified = False

    db.commit()
    db.refresh(current_user)

    if email_changed:
        issue_code(db, current_user, "email")

    new_access_token = None
    if password_changed:
        # The password change just bumped token_version, which would otherwise log
        # the very session that made this request out immediately. Reissue a token
        # for the same (now newer) token_version and refresh the cookie in place.
        new_access_token = create_access_token(current_user.id, current_user.token_version)
        _set_access_token_cookie(response, new_access_token)

    return {
        "message": "Profile updated",
        "email": current_user.email,
        "verification_required": email_changed,
        "access_token": new_access_token,
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

    return _user_from_token(token, db)
