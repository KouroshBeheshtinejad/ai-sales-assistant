from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.business_types import BUSINESS_TYPES, get_business_fields_for_store, get_business_type_label, normalize_business_type
from app.core.csrf import require_csrf_token
from app.db.database import get_db
from app.db.models import User, Store, Product, FAQ, KnowledgeBaseEntry
from app.routes.auth import get_current_user_from_cookie
from app.services.semantic_index import (
    SOURCE_FAQ,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_PRODUCT,
    safely_discard_semantic_document,
    safely_sync_semantic_document,
)


router = APIRouter(
    tags=["Store Management"],
)


templates = Jinja2Templates(
    directory="app/templates"
)


def _collect_custom_product_attributes(form_data):
    custom_attributes = {}
    for key, value in form_data.multi_items():
        if key.startswith("field_") and value not in ("", None):
            custom_attributes[key.removeprefix("field_")] = value
    return custom_attributes


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

    faqs = (
        db.query(FAQ)
        .filter(FAQ.store_id == store.id)
        .order_by(FAQ.updated_at.desc())
        .limit(3)
        .all()
    )

    knowledge_entries = (
        db.query(KnowledgeBaseEntry)
        .filter(KnowledgeBaseEntry.store_id == store.id)
        .order_by(KnowledgeBaseEntry.updated_at.desc())
        .limit(3)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="store_manage.html",
        context={
            "user": current_user,
            "store": store,
            "products": products,
            "faqs": faqs,
            "knowledge_entries": knowledge_entries,
            "business_type_label": get_business_type_label(store.business_type),
        },
    )


@router.get(
    "/stores/{store_id}/faq-manager",
    response_class=HTMLResponse,
)
def manage_faqs(
    store_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    faqs = db.query(FAQ).filter(FAQ.store_id == store.id).order_by(FAQ.updated_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="store_faqs.html",
        context={
            "user": current_user,
            "store": store,
            "faqs": faqs,
            "business_type_label": get_business_type_label(store.business_type),
        },
    )


@router.get(
    "/stores/{store_id}/faq-manager/new",
    response_class=HTMLResponse,
)
def new_faq_form(
    store_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return templates.TemplateResponse(
        request=request,
        name="faq_form.html",
        context={
            "user": current_user,
            "store": store,
            "faq": None,
            "mode": "create",
            "business_type_label": get_business_type_label(store.business_type),
        },
    )


@router.post(
    "/stores/{store_id}/faq-manager/new",
)
def create_faq_from_form(
    store_id: int,
    request: Request,
    question: str = Form(...),
    answer: str = Form(...),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    faq = FAQ(question=question.strip(), answer=answer.strip(), is_active=is_active, store_id=store.id)
    db.add(faq)
    db.commit()
    safely_sync_semantic_document(db, faq)
    return RedirectResponse(url=f"/stores/{store.id}/faq-manager", status_code=303)


@router.get(
    "/stores/{store_id}/faq-manager/{faq_id}/edit",
    response_class=HTMLResponse,
)
def edit_faq_form(
    store_id: int,
    faq_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    faq = db.query(FAQ).filter(FAQ.id == faq_id, FAQ.store_id == store.id).first()
    if faq is None:
        raise HTTPException(status_code=404, detail="FAQ not found")

    return templates.TemplateResponse(
        request=request,
        name="faq_form.html",
        context={
            "user": current_user,
            "store": store,
            "faq": faq,
            "mode": "edit",
            "business_type_label": get_business_type_label(store.business_type),
        },
    )


@router.post(
    "/stores/{store_id}/faq-manager/{faq_id}/edit",
)
def update_faq_from_form(
    store_id: int,
    faq_id: int,
    request: Request,
    question: str = Form(...),
    answer: str = Form(...),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    faq = db.query(FAQ).filter(FAQ.id == faq_id, FAQ.store_id == store.id).first()
    if faq is None:
        raise HTTPException(status_code=404, detail="FAQ not found")

    safely_discard_semantic_document(db, SOURCE_FAQ, faq.id, faq.store_id)
    faq.question = question.strip()
    faq.answer = answer.strip()
    faq.is_active = is_active
    db.commit()
    safely_sync_semantic_document(db, faq)
    return RedirectResponse(url=f"/stores/{store.id}/faq-manager", status_code=303)


@router.post(
    "/stores/{store_id}/faq-manager/{faq_id}/delete",
)
def delete_faq_from_form(
    store_id: int,
    faq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    faq = db.query(FAQ).filter(FAQ.id == faq_id, FAQ.store_id == store.id).first()
    if faq is None:
        raise HTTPException(status_code=404, detail="FAQ not found")

    safely_discard_semantic_document(db, SOURCE_FAQ, faq.id, faq.store_id)
    db.delete(faq)
    db.commit()
    return RedirectResponse(url=f"/stores/{store.id}/faq-manager", status_code=303)


@router.get(
    "/stores/{store_id}/knowledge-manager",
    response_class=HTMLResponse,
)
def manage_knowledge(
    store_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    entries = db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.store_id == store.id).order_by(KnowledgeBaseEntry.updated_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="store_knowledge.html",
        context={
            "user": current_user,
            "store": store,
            "entries": entries,
            "business_type_label": get_business_type_label(store.business_type),
        },
    )


@router.get(
    "/stores/{store_id}/knowledge-manager/new",
    response_class=HTMLResponse,
)
def new_knowledge_form(
    store_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    return templates.TemplateResponse(
        request=request,
        name="knowledge_form.html",
        context={
            "user": current_user,
            "store": store,
            "entry": None,
            "mode": "create",
            "business_type_label": get_business_type_label(store.business_type),
        },
    )


@router.post(
    "/stores/{store_id}/knowledge-manager/new",
)
def create_knowledge_from_form(
    store_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    entry = KnowledgeBaseEntry(title=title.strip(), content=content.strip(), is_active=is_active, store_id=store.id)
    db.add(entry)
    db.commit()
    safely_sync_semantic_document(db, entry)
    return RedirectResponse(url=f"/stores/{store.id}/knowledge-manager", status_code=303)


@router.get(
    "/stores/{store_id}/knowledge-manager/{knowledge_id}/edit",
    response_class=HTMLResponse,
)
def edit_knowledge_form(
    store_id: int,
    knowledge_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    entry = db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.id == knowledge_id, KnowledgeBaseEntry.store_id == store.id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    return templates.TemplateResponse(
        request=request,
        name="knowledge_form.html",
        context={
            "user": current_user,
            "store": store,
            "entry": entry,
            "mode": "edit",
            "business_type_label": get_business_type_label(store.business_type),
        },
    )


@router.post(
    "/stores/{store_id}/knowledge-manager/{knowledge_id}/edit",
)
def update_knowledge_from_form(
    store_id: int,
    knowledge_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    entry = db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.id == knowledge_id, KnowledgeBaseEntry.store_id == store.id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    safely_discard_semantic_document(
        db, SOURCE_KNOWLEDGE_BASE, entry.id, entry.store_id
    )
    entry.title = title.strip()
    entry.content = content.strip()
    entry.is_active = is_active
    db.commit()
    safely_sync_semantic_document(db, entry)
    return RedirectResponse(url=f"/stores/{store.id}/knowledge-manager", status_code=303)


@router.post(
    "/stores/{store_id}/knowledge-manager/{knowledge_id}/delete",
)
def delete_knowledge_from_form(
    store_id: int,
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
):
    store = db.query(Store).filter(Store.id == store_id, Store.owner_id == current_user.id).first()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    entry = db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.id == knowledge_id, KnowledgeBaseEntry.store_id == store.id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    safely_discard_semantic_document(
        db, SOURCE_KNOWLEDGE_BASE, entry.id, entry.store_id
    )
    db.delete(entry)
    db.commit()
    return RedirectResponse(url=f"/stores/{store.id}/knowledge-manager", status_code=303)

@router.get(
    "/stores/{store_id}/products/new",
    response_class=HTMLResponse,
)
def new_product_form(
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

    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={
            "user": current_user,
            "store": store,
            "business_fields": get_business_fields_for_store(store.business_type),
            "business_type_label": get_business_type_label(store.business_type),
        },
    )

@router.get(
    "/stores/{store_id}/products/{product_id}/edit",
    response_class=HTMLResponse,
)
def edit_product_form(
    store_id: int,
    product_id: int,
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

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.store_id == store.id,
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return templates.TemplateResponse(
        request=request,
        name="product_edit.html",
        context={
            "user": current_user,
            "store": store,
            "product": product,
            "business_fields": get_business_fields_for_store(store.business_type),
            "business_type_label": get_business_type_label(store.business_type),
        },
    )

@router.post(
    "/stores/{store_id}/products/{product_id}/edit",
)
async def update_product_from_form(
    store_id: int,
    product_id: int,
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
    price: float = Form(...),
    stock: int = Form(0),
    size: str | None = Form(None),
    color: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
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

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.store_id == store.id,
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    safely_discard_semantic_document(db, SOURCE_PRODUCT, product.id, product.store_id)
    product.name = name
    product.description = description
    product.price = price
    product.stock = stock
    product.size = size
    product.color = color

    form_data = await request.form()
    custom_attributes = _collect_custom_product_attributes(form_data)
    product.attributes = custom_attributes
    product.size = custom_attributes.get("size", size)
    product.color = custom_attributes.get("color", color)

    db.commit()
    safely_sync_semantic_document(db, product)

    return RedirectResponse(
        url=f"/stores/{store.id}/manage",
        status_code=303,
    )

@router.post(
    "/stores/{store_id}/products",
)
async def create_product_from_form(
    store_id: int,
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
    price: float = Form(...),
    stock: int = Form(0),
    size: str | None = Form(None),
    color: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
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

    form_data = await request.form()
    custom_attributes = _collect_custom_product_attributes(form_data)

    product = Product(
        name=name,
        description=description,
        price=price,
        stock=stock,
        size=custom_attributes.get("size", size),
        color=custom_attributes.get("color", color),
        attributes=custom_attributes,
        store_id=store.id,
    )

    db.add(product)
    db.commit()
    safely_sync_semantic_document(db, product)

    return RedirectResponse(
        url=f"/stores/{store.id}/manage",
        status_code=303,
    )

@router.get(
    "/stores/{store_id}/edit",
    response_class=HTMLResponse,
)
def edit_store_form(
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

    return templates.TemplateResponse(
        request=request,
        name="store_edit.html",
        context={
            "user": current_user,
            "store": store,
            "business_types": BUSINESS_TYPES,
        },
    )

@router.post(
    "/stores/{store_id}/edit",
)
def update_store_from_form(
    store_id: int,
    name: str = Form(...),
    description: str | None = Form(None),
    business_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
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

    store.name = name
    store.description = description
    store.business_type = normalize_business_type(business_type)

    db.commit()

    return RedirectResponse(
        url=f"/stores/{store.id}/manage",
        status_code=303,
    )

@router.post(
    "/stores/{store_id}/products/{product_id}/delete",
)
def delete_product_from_store(
    store_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
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

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.store_id == store.id,
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    safely_discard_semantic_document(db, SOURCE_PRODUCT, product.id, product.store_id)
    db.delete(product)
    db.commit()

    return RedirectResponse(
        url=f"/stores/{store.id}/manage",
        status_code=303,
    )

@router.get(
    "/stores/new",
    response_class=HTMLResponse,
)
def create_store_form(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie),
):
    return templates.TemplateResponse(
        request=request,
        name="store_create.html",
        context={
            "user": current_user,
            "business_types": BUSINESS_TYPES,
        },
    )


@router.post(
    "/stores/new",
)
def create_store_from_form(
    name: str = Form(...),
    description: str | None = Form(None),
    business_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
    _: None = Depends(require_csrf_token),
):
    store = Store(
        name=name,
        description=description,
        owner_id=current_user.id,
        business_type=normalize_business_type(business_type),
    )

    db.add(store)
    db.commit()

    return RedirectResponse(
        url="/dashboard",
        status_code=303,
    )
