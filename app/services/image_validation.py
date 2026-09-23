from io import BytesIO

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_WIDTH = 4096
MAX_IMAGE_HEIGHT = 4096
ALLOWED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF"})


def validate_image_content(content: bytes) -> None:
    if not content:
        raise ValueError("Image is empty")
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError("Unsupported image format")
            if image.width > MAX_IMAGE_WIDTH or image.height > MAX_IMAGE_HEIGHT:
                raise ValueError("Image dimensions are too large")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Invalid image content") from exc
