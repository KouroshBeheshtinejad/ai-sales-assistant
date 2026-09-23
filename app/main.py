import logging
import re
import uuid
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import allowed_hosts, validate_production_configuration
from app.core.csrf import ensure_csrf_token, set_csrf_cookie
from app.db.database import SessionLocal, engine
from app.db.models import Product, Store
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
from app.routes.business_types import router as business_types_router
from app.routes.payments import router as payments_router
from app.routes.auth import get_current_user

@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_production_configuration()
    yield


app = FastAPI(
    title="AI Sales Assistant",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")
frontend_dist = Path("frontend/dist")
uploads_dir = Path("uploads")


def react_html_with_metadata(request: Request, title: str, description: str, path: str) -> HTMLResponse:
    html_path = frontend_dist / "index.html"
    if not html_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    canonical = str(request.base_url).rstrip("/") + path
    document = html_path.read_text(encoding="utf-8")
    metadata = (
        f'<title>{escape(title)}</title>'
        f'<meta name="description" content="{escape(description)}">'
        f'<link rel="canonical" href="{escape(canonical)}">'
        f'<meta property="og:title" content="{escape(title)}">'
        f'<meta property="og:description" content="{escape(description)}">'
        f'<meta property="og:url" content="{escape(canonical)}">'
    )
    document = re.sub(r"<title>.*?</title>", "", document, count=1, flags=re.DOTALL)
    document = re.sub(r'<meta name="description"[^>]*>', "", document, count=1)
    document = re.sub(r'<meta property="og:(?:title|description|url)"[^>]*>', "", document)
    document = re.sub(r'<link rel="canonical"[^>]*>', "", document)
    document = document.replace("<head>", f"<head>{metadata}", 1)
    return HTMLResponse(document)


@app.middleware("http")
async def csrf_cookie_middleware(request: Request, call_next):
    ensure_csrf_token(request)
    response = await call_next(request)
    set_csrf_cookie(request, response)
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed request_id=%s path=%s", request_id, request.url.path)
        raise
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault(
    "Content-Security-Policy",
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' https://res.cloudinary.com data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
    )
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
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
app.include_router(business_types_router)
app.include_router(payments_router)

# Versioned API surface. The unprefixed routes above remain compatibility
# aliases for server-rendered forms and existing integrations.
for api_router in (
    auth_router,
    store_management_router,
    stores_router,
    products_router,
    faqs_router,
    knowledge_base_router,
    chat_router,
    cart_router,
    order_router,
    seller_orders_router,
    conversations_router,
    business_types_router,
    payments_router,
):
    app.include_router(api_router, prefix="/api")

if frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="frontend_assets")
    app.mount("/app", StaticFiles(directory=frontend_dist, html=True), name="react_frontend")

uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "products").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/", include_in_schema=False)
async def root(request: Request):
    if (frontend_dist / "index.html").is_file():
        return react_html_with_metadata(
            request,
            "NAVA | AI commerce",
            "Conversational commerce for modern stores.",
            "/",
        )
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
    )


@app.get("/landing", response_class=HTMLResponse, include_in_schema=False)
async def landing(request: Request):
    if (frontend_dist / "index.html").is_file():
        return react_html_with_metadata(
            request,
            "NAVA | AI commerce",
            "Conversational commerce for modern stores.",
            "/landing",
        )
    return templates.TemplateResponse(request=request, name="landing.html")


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    path = frontend_dist / "robots.txt"
    if path.is_file():
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    path = frontend_dist / "sitemap.xml"
    if path.is_file():
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/store/{store_id}", include_in_schema=False)
async def react_store_route(store_id: int, request: Request):
    with SessionLocal() as db:
        store = db.query(Store).filter(Store.id == store_id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return react_html_with_metadata(
        request,
        f"{store.name} | NAVA",
        store.description or f"Explore {store.name} on NAVA.",
        f"/store/{store_id}",
    )


@app.get("/store/{store_id}/product/{product_id}", include_in_schema=False)
async def react_product_route(store_id: int, product_id: int, request: Request):
    with SessionLocal() as db:
        product = (
            db.query(Product)
            .join(Store)
            .filter(
                Product.id == product_id,
                Product.store_id == store_id,
                Product.is_active.is_(True),
            )
            .first()
        )
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        store_name = product.store.name
    return react_html_with_metadata(
        request,
        f"{product.name} | {store_name} | NAVA",
        product.description or f"{product.name} from {store_name}.",
        f"/store/{store_id}/product/{product_id}",
    )


@app.get("/seller", include_in_schema=False)
async def react_seller_route():
    if (frontend_dist / "index.html").is_file():
        return FileResponse(frontend_dist / "index.html")
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/login", include_in_schema=False)
@app.get("/register", include_in_schema=False)
@app.get("/track", include_in_schema=False)
@app.get("/seller/products", include_in_schema=False)
@app.get("/seller/knowledge", include_in_schema=False)
@app.get("/seller/orders", include_in_schema=False)
@app.get("/seller/conversations", include_in_schema=False)
async def react_frontend_route():
    if (frontend_dist / "index.html").is_file():
        return FileResponse(frontend_dist / "index.html")
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/seller/order/{order_id}", include_in_schema=False)
@app.get("/seller/conversation/{conversation_id}", include_in_schema=False)
async def react_seller_detail_route():
    if (frontend_dist / "index.html").is_file():
        return FileResponse(frontend_dist / "index.html")
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/health/db")
async def database_health(_current_user=Depends(get_current_user)):
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar(),
        }


@app.get("/health/live", include_in_schema=False)
async def liveness_check():
    return {"status": "ok"}


@app.get("/health", include_in_schema=False)
async def health_check():
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
