import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import allowed_hosts
from app.core.csrf import ensure_csrf_token, set_csrf_cookie
from app.db.database import engine
from app.db import models
from app.routes.auth import router as auth_router
from app.routes.store_management import router as store_management_router
from app.routes.stores import router as stores_router
from app.routes.products import router as products_router
from app.routes.dashboard import router as dashboard_router
from app.routes.faqs import router as faqs_router
from app.routes.knowledge_base import router as knowledge_base_router
from app.routes.chat import router as chat_router
from app.routes.cart import router as cart_router
from app.routes.order import router as order_router
from app.routes.seller_orders import router as seller_orders_router
from app.routes.conversations import router as conversations_router

app = FastAPI(
    title="AI Sales Assistant",
    version="0.1.0",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def csrf_cookie_middleware(request: Request, call_next):
    ensure_csrf_token(request)
    response = await call_next(request)
    set_csrf_cookie(request, response)
    return response

app.include_router(auth_router)
app.include_router(store_management_router)
app.include_router(stores_router)
app.include_router(products_router)
app.include_router(faqs_router)
app.include_router(knowledge_base_router)
app.include_router(chat_router)
app.include_router(dashboard_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(seller_orders_router)
app.include_router(conversations_router)

@app.get("/", include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
    )


@app.get("/landing", response_class=HTMLResponse, include_in_schema=False)
async def landing(request: Request):
    return templates.TemplateResponse(request=request, name="landing.html")


@app.get("/health/db")
async def database_health():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar(),
        }


@app.get("/health/live", include_in_schema=False)
async def liveness_check():
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
async def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Readiness probe database check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not ready",
        )
    return {"status": "ready"}
