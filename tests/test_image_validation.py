from io import BytesIO

import pytest
from PIL import Image

from app.services.image_validation import validate_image_content


def test_image_validation_rejects_spoofed_content():
    with pytest.raises(ValueError, match="Invalid image content"):
        validate_image_content(b"not-an-image")


def test_image_validation_accepts_real_png():
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buffer, format="PNG")

    validate_image_content(buffer.getvalue())


def test_image_validation_rejects_oversized_dimensions():
    buffer = BytesIO()
    Image.new("RGB", (4097, 1), "red").save(buffer, format="PNG")

    with pytest.raises(ValueError, match="dimensions"):
        validate_image_content(buffer.getvalue())