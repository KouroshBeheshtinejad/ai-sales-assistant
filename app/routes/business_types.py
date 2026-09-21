from fastapi import APIRouter

from app.core.business_types import get_business_types


router = APIRouter(prefix="/business-types", tags=["Business Types"])


@router.get("")
def list_business_types():
    return get_business_types()