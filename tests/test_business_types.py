from app.core.business_types import (
    get_business_fields_for_store,
    get_business_type,
    get_business_type_label,
    get_business_types,
    normalize_business_type,
)


def test_business_types_are_dynamic_and_normalized():
    types = get_business_types()
    assert types
    assert get_business_type(" fast_food ")["slug"] == "fast_food"
    assert get_business_type(None)["slug"] == "clothing"
    assert get_business_type("does-not-exist")["slug"] == "clothing"
    assert get_business_type_label("electronics")
    assert get_business_fields_for_store("restaurant")
    assert normalize_business_type("Fast Food") == "fast_food"
    assert normalize_business_type("unknown") == "clothing"
    assert normalize_business_type(None) == "clothing"