from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import engine
from app.db import models
from app.routes.auth import router as auth_router
from app.routes.store_management import router as store_management_router
from app.routes.stores import router as stores_router
from app.routes.products import router as products_router
from app.routes.dashboard import router as dashboard_router

app = FastAPI(
    title="AI Sales Assistant",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(store_management_router)
app.include_router(stores_router)
app.include_router(products_router)
app.include_router(dashboard_router)

@app.get("/")
async def root():
    return {
        "message": "AI Sales Assistant API is running",
        "version": "0.1.0",
    }


@app.get("/health/db")
async def database_health():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar(),
        }