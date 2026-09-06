from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, Store, Product
from app.routes.auth import get_current_user_from_cookie


router = APIRouter(
    tags=["Dashboard"],
)


templates = Jinja2Templates(
    directory="app/templates"
)


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    # Total number of stores owned by the current user
    stores_count = (
        db.query(Store)
        .filter(Store.owner_id == current_user.id)
        .count()
    )

    # Total number of products across all user's stores
    total_products_count = (
        db.query(Product)
        .join(Store)
        .filter(Store.owner_id == current_user.id)
        .count()
    )

    # Total stock across all user's stores
    total_stock_count = (
        db.query(func.coalesce(func.sum(Product.stock), 0))
        .join(Store)
        .filter(Store.owner_id == current_user.id)
        .scalar()
    )

    # Get all stores owned by the current user
    stores = (
        db.query(Store)
        .filter(Store.owner_id == current_user.id)
        .all()
    )

    store_data = []

    for store in stores:

        # Number of products in this store
        store_products_count = (
            db.query(Product)
            .filter(Product.store_id == store.id)
            .count()
        )

        # Total stock in this store
        store_total_stock = (
            db.query(func.coalesce(func.sum(Product.stock), 0))
            .filter(Product.store_id == store.id)
            .scalar()
        )

        store_data.append(
            {
                "id": store.id,
                "name": store.name,
                "description": store.description,
                "products_count": store_products_count,
                "total_stock": store_total_stock,
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": current_user,
            "stores_count": stores_count,
            "products_count": total_products_count,
            "total_stock": total_stock_count,
            "stores": store_data,
        },
    )