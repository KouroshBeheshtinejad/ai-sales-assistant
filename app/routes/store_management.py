from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, Store, Product
from app.routes.auth import get_current_user_from_cookie


router = APIRouter(
    tags=["Store Management"],
)


templates = Jinja2Templates(
    directory="app/templates"
)


@router.get(
    "/stores/{store_id}/manage",
    response_class=HTMLResponse,
)
def manage_store(
    store_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            Store.owner_id == current_user.id,
        )
        .first()
    )

    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store not found",
        )

    products = (
        db.query(Product)
        .filter(Product.store_id == store.id)
        .order_by(Product.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="store_manage.html",
        context={
            "user": current_user,
            "store": store,
            "products": products,
        },
    )