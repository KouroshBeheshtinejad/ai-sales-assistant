from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text

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

app = FastAPI(
    title="AI Sales Assistant",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(store_management_router)
app.include_router(stores_router)
app.include_router(products_router)
app.include_router(faqs_router)
app.include_router(knowledge_base_router)
app.include_router(chat_router)
app.include_router(dashboard_router)

@app.get("/", include_in_schema=False)
async def root(request: Request):
    target = "/dashboard" if request.cookies.get("access_token") else "/auth/login"
    return RedirectResponse(url=target)


@app.get("/health/db")
async def database_health():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar(),
        }