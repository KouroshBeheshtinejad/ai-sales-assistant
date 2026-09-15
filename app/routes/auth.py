import jwt

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.core.config import cookie_settings
from app.core.csrf import require_csrf_token
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

templates = Jinja2Templates(directory="app/templates")


security = HTTPBearer()


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
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


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
    access_token = create_access_token(user.id)
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
    access_token = create_access_token(user.id)
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
    db: Session = Depends(get_db),
):
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
        password_hash=hash_password(data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "email": user.email,
    }


@router.post("/login")
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
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

    access_token = create_access_token(user.id)

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

    return user


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
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
